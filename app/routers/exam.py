from fastapi import APIRouter, Request, Response, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
import aiosqlite

from app.config import settings
from app.database import get_db
from app.auth_helper import get_current_user_and_guest
from app.templates_config import templates
from app.exam_engine import (
    create_exam,
    get_exam_questions_for_taking,
    record_user_answer,
    finish_and_grade_exam,
    get_exam_report_details
)

router = APIRouter(prefix="/exam", tags=["exam"])

@router.get("/builder", response_class=HTMLResponse)
async def exam_builder_page(request: Request, response: Response, category: Optional[str] = None):
    user, guest_token = await get_current_user_and_guest(request, response)

    async with get_db() as db:
        cursor = await db.execute("""
            SELECT c.code, c.name_fa, c.description, c.icon, c.color,
                   COUNT(q.id) as question_count
            FROM categories c
            LEFT JOIN questions q ON c.code = q.category AND q.status = 'published'
            WHERE c.is_exam = 1
            GROUP BY c.code
        """)
        categories = [dict(r) for r in await cursor.fetchall()]

        # خطاهای قبلی کاربر برای تعیین اینکه آیا گزینه "فقط خطاهای من" فعال باشد
        user_error_count = 0
        if user or guest_token:
            cursor = await db.execute("""
                SELECT COUNT(DISTINCT question_id) FROM user_answers
                WHERE is_correct = 0 AND ((user_id = ? AND ? IS NOT NULL) OR (guest_token = ? AND ? IS NOT NULL))
            """, (user["id"] if user else None, user["id"] if user else None, guest_token, guest_token))
            user_error_count = (await cursor.fetchone())[0]

    resp = templates.TemplateResponse(
        request=request,
        name="exam/builder.html",
        context={
            "user": user,
            "categories": categories,
            "selected_category": category or "all",
            "user_error_count": user_error_count,
            "settings": settings
        }
    )
    resp.set_cookie("guest_token", guest_token, max_age=30*24*3600, httponly=True)
    return resp

@router.post("/create")
async def create_exam_endpoint(
    request: Request,
    response: Response,
    category: str = Form("all"),
    total_questions: int = Form(15),
    has_negative_marking: bool = Form(True),
    duration_minutes: int = Form(20),
    filter_mode: str = Form("smart"),
    exam_type: str = Form("custom")
):
    user, guest_token = await get_current_user_and_guest(request, response)
    user_id = user["id"] if user else None

    # بررسی سهمیه روزانه برای کاربران رایگان (Freemium Gate)
    if not user or not user.get("is_vip"):
        async with get_db() as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM exam_attempts
                WHERE (user_id = ? OR guest_token = ?)
                  AND date(started_at) = date('now')
            """, (user_id, guest_token))
            today_exams = (await cursor.fetchone())[0]
            if today_exams >= 5 and total_questions > 20:
                total_questions = 20 # محدودسازی آزمون برای کاربران عادی

    exam_res = await create_exam(
        category=category,
        total_questions=total_questions,
        user_id=user_id,
        guest_token=guest_token,
        exam_type=exam_type,
        has_negative_marking=has_negative_marking,
        duration_minutes=duration_minutes,
        filter_mode=filter_mode
    )

    attempt_id = exam_res["attempt_id"]
    return RedirectResponse(url=f"/exam/take/{attempt_id}", status_code=303)

@router.get("/take/{attempt_id}", response_class=HTMLResponse)
async def exam_runner_page(request: Request, response: Response, attempt_id: int):
    user, guest_token = await get_current_user_and_guest(request, response)

    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM exam_attempts WHERE id = ?", (attempt_id,))
        attempt = await cursor.fetchone()
        if not attempt:
            raise HTTPException(status_code=404, detail="آزمون یافت نشد")

        if attempt["is_finished"]:
            return RedirectResponse(url=f"/exam/result/{attempt_id}")

        questions = await get_exam_questions_for_taking(attempt_id)

    return templates.TemplateResponse(
        request=request,
        name="exam/runner.html",
        context={
            "user": user,
            "attempt": dict(attempt),
            "questions": questions,
            "settings": settings
        }
    )

@router.post("/answer")
async def answer_question_endpoint(
    request: Request,
    response: Response,
    attempt_id: int = Form(...),
    question_id: int = Form(...),
    selected_option: Optional[int] = Form(None)
):
    user, guest_token = await get_current_user_and_guest(request, response)
    user_id = user["id"] if user else None

    res = await record_user_answer(
        attempt_id=attempt_id,
        question_id=question_id,
        selected_option=selected_option,
        user_id=user_id,
        guest_token=guest_token
    )

    # بازگرداندن پاسخ سبک HTMX
    return HTMLResponse(
        content='<span class="text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full font-medium inline-flex items-center gap-1">✓ ذخیره شد</span>',
        status_code=200
    )

@router.post("/finish/{attempt_id}")
async def finish_exam_endpoint(request: Request, response: Response, attempt_id: int):
    user, _ = await get_current_user_and_guest(request, response)
    user_id = user["id"] if user else None

    await finish_and_grade_exam(attempt_id=attempt_id, user_id=user_id)
    return RedirectResponse(url=f"/exam/result/{attempt_id}", status_code=303)

@router.get("/result/{attempt_id}", response_class=HTMLResponse)
async def exam_result_page(request: Request, response: Response, attempt_id: int):
    user, guest_token = await get_current_user_and_guest(request, response)

    report = await get_exam_report_details(attempt_id)
    if not report:
        raise HTTPException(status_code=404, detail="کارنامه آزمون یافت نشد")

    # اگر کاربر لاگین نکرده، لینک عمیق ورود با بله ایجاد شود
    bale_session = None
    if not user:
        from app.bale_bot import create_bale_login_session
        bale_session = await create_bale_login_session(guest_token=guest_token)

    return templates.TemplateResponse(
        request=request,
        name="exam/result.html",
        context={
            "user": user,
            "report": report,
            "bale_session": bale_session,
            "settings": settings
        }
    )

@router.post("/bookmark/{question_id}")
async def toggle_bookmark(request: Request, response: Response, question_id: int):
    user, _ = await get_current_user_and_guest(request, response)
    if not user:
        return HTMLResponse('<span class="text-xs text-amber-600">برای نشان کردن وارد شوید</span>', status_code=401)

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM user_bookmarks WHERE user_id = ? AND question_id = ?",
            (user["id"], question_id)
        )
        row = await cursor.fetchone()
        if row:
            await db.execute("DELETE FROM user_bookmarks WHERE id = ?", (row[0],))
            is_bookmarked = False
        else:
            await db.execute(
                "INSERT INTO user_bookmarks (user_id, question_id) VALUES (?, ?)",
                (user["id"], question_id)
            )
            is_bookmarked = True
        await db.commit()

    icon = "★ نشان شد" if is_bookmarked else "☆ نشان کردن"
    color = "text-amber-600 bg-amber-50" if is_bookmarked else "text-slate-600 hover:bg-slate-100"
    return HTMLResponse(f'<button class="text-xs px-2.5 py-1 rounded-lg border border-slate-200 transition-colors {color}">{icon}</button>')

@router.post("/report/{question_id}")
async def report_question_error(
    request: Request,
    response: Response,
    question_id: int,
    reason: str = Form(...),
    details: Optional[str] = Form(None)
):
    user, _ = await get_current_user_and_guest(request, response)
    user_id = user["id"] if user else None

    async with get_db() as db:
        await db.execute("""
            INSERT INTO question_reports (question_id, user_id, reason, details)
            VALUES (?, ?, ?, ?)
        """, (question_id, user_id, reason, details))

        # افزایش شمارنده گزارش خطا در جدول سوالات
        await db.execute("""
            UPDATE questions
            SET report_count = report_count + 1
            WHERE id = ?
        """, (question_id,))

        # بررسی رسیدن به آستانه ۳ گزارش خطا (ارسال به بازبینی ادمین)
        cursor = await db.execute("SELECT report_count FROM questions WHERE id = ?", (question_id,))
        count = (await cursor.fetchone())[0]
        if count >= 3:
            await db.execute("UPDATE questions SET status = 'needs_review' WHERE id = ?", (question_id,))

        await db.commit()

    return HTMLResponse('<span class="text-xs text-emerald-600 font-medium">✓ گزارش شما ثبت و به صف بازبینی ادمین ارسال شد.</span>')
