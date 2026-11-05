from typing import Optional
import datetime
from fastapi import APIRouter, Request, Response, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from app.config import settings
from app.database import get_db
from app.auth_helper import get_current_user_and_guest
from app.templates_config import templates
from app.bale_bot import create_bale_login_session, handle_bale_webhook, check_session_status, normalize_digits

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, response: Response, redirect: Optional[str] = None):
    """صفحه اختصاصی ورود به سامانه با گزینه‌های ورود سریع دمو و پیام‌رسان بله"""
    user, guest_token = await get_current_user_and_guest(request, response)
    if user:
        if user.get("role") == "admin":
            return RedirectResponse(url="/admin", status_code=303)
        return RedirectResponse(url="/user/dashboard", status_code=303)

    session_data = await create_bale_login_session(guest_token=guest_token)

    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "user": user,
            "session": session_data,
            "redirect_url": redirect or "/user/dashboard",
            "settings": settings
        }
    )

@router.get("/modal", response_class=HTMLResponse)
async def get_login_modal(request: Request, response: Response):
    user, guest_token = await get_current_user_and_guest(request, response)
    session_data = await create_bale_login_session(guest_token=guest_token)

    return templates.TemplateResponse(
        request=request,
        name="auth/modal_content.html",
        context={
            "session": session_data,
            "settings": settings
        }
    )

@router.get("/check/{token}")
async def check_auth_endpoint(request: Request, response: Response, token: str):
    """
    بررسی مداوم تایید ورود کاربر در بله از طریق HTMX Polling (هر ۲ ثانیه)
    """
    res = await check_session_status(token)

    if res["status"] == "verified":
        user_id = res["user_id"]
        full_name = "داوطلب عزیز"
        async with get_db() as db:
            cursor = await db.execute("SELECT full_name FROM users WHERE id = ?", (user_id,))
            urow = await cursor.fetchone()
            if urow and urow[0]:
                full_name = urow[0]

        # تنظیم کوکی نشست امن
        response.set_cookie(key="user_id", value=str(user_id), max_age=60*24*3600, httponly=True)
        response.headers["HX-Redirect"] = "/user/dashboard"
        return HTMLResponse(f"""
            <div class="text-center py-4">
                <div class="inline-flex items-center justify-center w-12 h-12 bg-emerald-100 text-emerald-600 rounded-full mb-3 animate-bounce">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                </div>
                <h4 class="font-bold text-emerald-700 text-lg">سلام {full_name}! ورود موفقیت‌آمیز بود.</h4>
                <p class="text-xs text-slate-500 mt-1">اطلاعات شما با موفقیت از بله همگام شد. در حال انتقال به میز کار...</p>
            </div>
        """)
    elif res["status"] == "expired":
        return HTMLResponse("""
            <div class="text-center py-4 text-rose-600">
                <p class="text-sm">مهلت ورود منقضی شد. لطفاً صفحه را مجدداً باز کنید.</p>
            </div>
        """)

    # هنوز تایید نشده، ادامه انتظار
    return HTMLResponse(f"""
        <div class="flex items-center justify-center gap-2 text-slate-600 py-3" hx-get="/auth/check/{token}" hx-trigger="every 2s" hx-swap="outerHTML">
            <svg class="animate-spin h-5 w-5 text-emerald-600" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span class="text-xs font-medium">منتظر تایید شما در اپلیکیشن بله...</span>
        </div>
    """)

@router.post("/verify-otp")
async def verify_otp_endpoint(
    request: Request,
    response: Response,
    token: str = Form(""),
    otp_code: str = Form("")
):
    """تایید ورود با وارد کردن کد ۴ رقمی پیام‌رسان بله به صورت دستی"""
    token = token.strip()
    otp_code = normalize_digits(otp_code)

    if not otp_code:
        return HTMLResponse("""
            <div class="text-xs text-rose-600 bg-rose-50 p-2.5 rounded-xl mt-2 font-medium">
                ⚠️ لطفاً کد ۴ رقمی را وارد کنید.
            </div>
        """)

    _, guest_token = await get_current_user_and_guest(request, response)

    async with get_db() as db:
        now_iso = datetime.datetime.utcnow().isoformat()
        if token:
            cursor = await db.execute("""
                SELECT user_id, guest_token, token FROM auth_sessions
                WHERE ((token = ? AND otp_code = ?) OR otp_code = ?) AND expires_at > ?
                ORDER BY created_at DESC LIMIT 1
            """, (token, otp_code, otp_code, now_iso))
        else:
            cursor = await db.execute("""
                SELECT user_id, guest_token, token FROM auth_sessions
                WHERE otp_code = ? AND expires_at > ?
                ORDER BY created_at DESC LIMIT 1
            """, (otp_code, now_iso))
            
        row = await cursor.fetchone()

        if not row:
            return HTMLResponse("""
                <div class="text-xs text-rose-600 bg-rose-50 p-2.5 rounded-xl mt-2 font-medium">
                    ⚠️ کد اعتبارسنجی وارد شده صحیح نیست یا منقضی شده است.
                </div>
            """)

        user_id, session_guest_token, session_token = row[0], row[1], row[2]

        # در صورتی که کاربر قبلا لاگین نداشته با کد هم ایجاد می‌شود
        if not user_id:
            cursor = await db.execute("INSERT INTO users (full_name) VALUES ('کاربر تست ۹۸')")
            user_id = cursor.lastrowid

        await db.execute("UPDATE auth_sessions SET status = 'verified', user_id = ? WHERE token = ?", (user_id, session_token))

        # انتقال آزمون‌های مهمان
        target_guest = guest_token or session_guest_token
        if target_guest:
            await db.execute("UPDATE exam_attempts SET user_id = ? WHERE guest_token = ? AND (user_id IS NULL OR user_id = ?)", (user_id, target_guest, user_id))
            await db.execute("UPDATE user_answers SET user_id = ? WHERE guest_token = ? AND (user_id IS NULL OR user_id = ?)", (user_id, target_guest, user_id))

        await db.commit()

        # دریافت اطلاعات نام کاربر جهت پیام خوش‌آمدگویی
        cursor = await db.execute("SELECT full_name FROM users WHERE id = ?", (user_id,))
        u_row = await cursor.fetchone()
        u_name = u_row[0] if u_row and u_row[0] else 'داوطلب عزیز'

        res = HTMLResponse(f"""
            <div class="text-xs text-emerald-700 bg-emerald-50 p-3 rounded-xl mt-2 font-bold flex items-center justify-center gap-2 border border-emerald-200">
                <span class="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
                <span>خوش آمدید {u_name}! در حال انتقال به میز کار...</span>
            </div>
        """)
        res.set_cookie(key="user_id", value=str(user_id), max_age=60*24*3600, httponly=True)
        res.headers["HX-Redirect"] = "/user/dashboard"
        return res

@router.get("/demo-login")
@router.post("/demo-login")
async def demo_login_endpoint(
    response: Response,
    role: str = Query("user")
):
    """ورود سریع تستی برای تست پنل ادمین و پنل کاربری (پشتیبانی از GET و POST)"""
    async with get_db() as db:
        if role == "admin":
            cursor = await db.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
            row = await cursor.fetchone()
            if row:
                user_id = row[0]
            else:
                cursor = await db.execute("INSERT INTO users (full_name, phone, role, is_vip) VALUES ('مدیر ارشد سامانه', '09120000000', 'admin', 1)")
                await db.commit()
                user_id = cursor.lastrowid
            redirect_to = "/admin"
        else:
            # ایجاد یا دریافت کاربر داوطلب نمونه
            cursor = await db.execute("SELECT id FROM users WHERE role = 'user' LIMIT 1")
            row = await cursor.fetchone()
            if row:
                user_id = row[0]
            else:
                cursor = await db.execute("INSERT INTO users (full_name, phone, role, is_vip) VALUES ('داوطلب نمونه', '09121111111', 'user', 1)")
                await db.commit()
                user_id = cursor.lastrowid
            redirect_to = "/user/dashboard"

    redirect_resp = RedirectResponse(url=redirect_to, status_code=303)
    redirect_resp.set_cookie(key="user_id", value=str(user_id), max_age=60*24*3600, httponly=True)
    return redirect_resp

@router.post("/bale-webhook")
async def bale_webhook_endpoint(request: Request):
    """وب‌هوک دریافت رویدادها و آپدیت‌های ربات بله"""
    try:
        data = await request.json()
        await handle_bale_webhook(data)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)

@router.get("/logout")
async def logout_endpoint(response: Response):
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie(key="user_id")
    return resp
