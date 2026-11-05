from fastapi import APIRouter, Request, Response, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
import json
import asyncio

from app.config import settings
from app.database import get_db
from app.auth_helper import get_current_user_and_guest
from app.templates_config import templates
from app.crawler.crawler_manager import get_crawler_status, sync_channel, trigger_all_channels_sync

router = APIRouter(prefix="/admin", tags=["admin"])

async def require_admin(request: Request, response: Response):
    user, _ = await get_current_user_and_guest(request, response)
    # جهت سهولت آزمایش اولیه اگر کاربر admin نبود، اجازه ورود با اخطار می‌دهد
    # یا می‌توان از demo login استفاده کرد
    return user

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, response: Response):
    user = await require_admin(request, response)

    async with get_db() as db:
        # آمار سوالات
        cursor = await db.execute("SELECT COUNT(*) FROM questions WHERE status = 'published'")
        published_q = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM questions WHERE status = 'needs_review'")
        pending_q = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM news")
        total_news = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM question_reports WHERE status = 'pending'")
        pending_reports = (await cursor.fetchone())[0]

        # آمار کانال‌های تلگرام
        channels = await get_crawler_status()

        # ۵ سوال آخر نیازمند بررسی
        cursor = await db.execute("""
            SELECT id, question_text, category, source_channel, created_at
            FROM questions
            WHERE status = 'needs_review'
            ORDER BY id DESC LIMIT 5
        """)
        pending_samples = [dict(r) for r in await cursor.fetchall()]

    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "user": user,
            "published_q": published_q,
            "pending_q": pending_q,
            "total_news": total_news,
            "pending_reports": pending_reports,
            "channels": channels,
            "pending_samples": pending_samples,
            "settings": settings
        }
    )

@router.get("/moderation", response_class=HTMLResponse)
async def admin_moderation_queue(request: Request, response: Response):
    """
    صف بازبینی و کنترل کیفیت سریع سوالات ناقص یا تلگرامی (Tinder-style Moderation)
    """
    user = await require_admin(request, response)

    async with get_db() as db:
        cursor = await db.execute("""
            SELECT 
                q.*,
                c.name_fa as category_name
            FROM questions q
            LEFT JOIN categories c ON q.category = c.code
            WHERE q.status = 'needs_review'
            ORDER BY q.report_count DESC, q.id ASC
            LIMIT 10
        """)
        rows = await cursor.fetchall()

        items = []
        for r in rows:
            items.append({
                "id": r["id"],
                "category": r["category"],
                "category_name": r["category_name"],
                "question_text": r["question_text"],
                "options": json.loads(r["options_json"]),
                "correct_index": r["correct_index"],
                "explanation": r["explanation"],
                "source_channel": r["source_channel"],
                "report_count": r["report_count"]
            })

    return templates.TemplateResponse(
        request=request,
        name="admin/moderation.html",
        context={
            "user": user,
            "questions": items,
            "total_pending": len(items),
            "settings": settings
        }
    )

@router.post("/moderation-action")
async def moderation_action(
    request: Request,
    response: Response,
    question_id: int = Form(...),
    action: str = Form(...), # publish, reject
    correct_index: Optional[int] = Form(None),
    question_text: Optional[str] = Form(None),
    explanation: Optional[str] = Form(None)
):
    """
    اکشن تایید و انتشار، رد یا تصحیح سوال با بازگشت آنی HTMX
    """
    async with get_db() as db:
        if action == "publish":
            if correct_index is None:
                return HTMLResponse('<span class="text-xs text-rose-600 font-bold">لطفاً گزینه صحیح را مشخص کنید</span>', status_code=400)

            await db.execute("""
                UPDATE questions
                SET status = 'published',
                    correct_index = ?,
                    question_text = COALESCE(?, question_text),
                    explanation = COALESCE(?, explanation)
                WHERE id = ?
            """, (correct_index, question_text, explanation, question_id))

            # ایندکس در FTS5 سوالات
            cursor = await db.execute("SELECT question_text, explanation FROM questions WHERE id = ?", (question_id,))
            q_row = await cursor.fetchone()
            if q_row:
                await db.execute("INSERT INTO questions_fts (question_text, explanation) VALUES (?, ?)", (q_row[0], q_row[1] or ""))

        elif action == "reject":
            await db.execute("UPDATE questions SET status = 'rejected' WHERE id = ?", (question_id,))

        await db.commit()

    return HTMLResponse(f"""
        <div class="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-center text-emerald-800 font-medium animate-fade-out">
            ✓ سوال شماره {question_id} با موفقیت { 'منتشر شد' if action == 'publish' else 'رد و بایگانی شد' }.
        </div>
    """)

@router.get("/crawlers", response_class=HTMLResponse)
async def admin_crawlers_page(request: Request, response: Response):
    user = await require_admin(request, response)
    channels = await get_crawler_status()

    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM crawler_logs ORDER BY id DESC LIMIT 20
        """)
        logs = [dict(r) for r in await cursor.fetchall()]

    return templates.TemplateResponse(
        request=request,
        name="admin/crawlers.html",
        context={
            "user": user,
            "channels": channels,
            "logs": logs,
            "settings": settings
        }
    )

@router.post("/crawlers/sync")
async def trigger_channel_sync(channel_username: str = Form(...), limit: int = Form(50)):
    """دستور دریافت دستی تاریخچه کانال تلگرام"""
    res = await sync_channel(channel_username, limit=limit)
    q_count = res.get("questions", 0)
    n_count = res.get("news", 0)
    return HTMLResponse(f"""
        <div class="text-xs text-emerald-700 bg-emerald-50 p-2 rounded-lg font-bold">
            ✓ سینک انجام شد ({q_count} سوال و {n_count} خبر جدید)
        </div>
    """)

@router.post("/crawlers/sync-all")
async def trigger_all_sync_endpoint():
    """استخراج همزمان تمام ۸ کانال تلگرام"""
    asyncio.create_task(trigger_all_channels_sync(limit=50))
    return HTMLResponse("""
        <div class="p-3 bg-emerald-50 text-emerald-800 rounded-xl text-xs font-bold border border-emerald-200">
            ✓ استخراج پس‌زمینه برای تمام ۸ کانال تلگرام آغاز شد. لطفاً چند ثانیه دیگر صفحه را تازه‌سازی کنید.
        </div>
    """)

@router.get("/reports", response_class=HTMLResponse)
async def admin_reports_page(request: Request, response: Response):
    user = await require_admin(request, response)

    async with get_db() as db:
        cursor = await db.execute("""
            SELECT 
                qr.*,
                q.question_text, q.options_json, q.correct_index,
                u.full_name as reporter_name
            FROM question_reports qr
            JOIN questions q ON qr.question_id = q.id
            LEFT JOIN users u ON qr.user_id = u.id
            ORDER BY qr.id DESC LIMIT 50
        """)
        rows = await cursor.fetchall()
        reports = []
        for r in rows:
            reports.append({
                "id": r["id"],
                "question_id": r["question_id"],
                "question_text": r["question_text"],
                "options": json.loads(r["options_json"]),
                "correct_index": r["correct_index"],
                "reason": r["reason"],
                "details": r["details"],
                "status": r["status"],
                "reporter_name": r["reporter_name"],
                "created_at": r["created_at"]
            })

    return templates.TemplateResponse(
        request=request,
        name="admin/reports.html",
        context={
            "user": user,
            "reports": reports,
            "settings": settings
        }
    )

@router.post("/reports/resolve")
async def resolve_report(report_id: int = Form(...), action: str = Form("resolve")):
    async with get_db() as db:
        new_status = "resolved" if action == "resolve" else "dismissed"
        await db.execute("UPDATE question_reports SET status = ? WHERE id = ?", (new_status, report_id))
        await db.commit()

    return HTMLResponse(f'<span class="text-xs text-slate-500 font-medium">گزارش {new_status} شد</span>')

# --- مدیریت جامع بانک سوالات ---
@router.get("/questions", response_class=HTMLResponse)
async def admin_questions_page(
    request: Request,
    response: Response,
    q: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    channel: Optional[str] = None,
    page: int = 1
):
    user = await require_admin(request, response)
    page_size = 20
    offset = (page - 1) * page_size

    async with get_db() as db:
        conditions = ["1=1"]
        params = []

        if q:
            conditions.append("(question_text LIKE ? OR explanation LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])

        if category and category != "all":
            conditions.append("category = ?")
            params.append(category)

        if status and status != "all":
            conditions.append("status = ?")
            params.append(status)

        if channel and channel != "all":
            conditions.append("source_channel = ?")
            params.append(channel)

        where_sql = " WHERE " + " AND ".join(conditions)

        # تعداد کل
        cursor = await db.execute(f"SELECT COUNT(*) FROM questions {where_sql}", params)
        total_count = (await cursor.fetchone())[0]

        cursor = await db.execute(f"""
            SELECT q.*, c.name_fa as category_name
            FROM questions q
            LEFT JOIN categories c ON q.category = c.code
            {where_sql}
            ORDER BY q.id DESC
            LIMIT ? OFFSET ?
        """, (*params, page_size, offset))
        rows = await cursor.fetchall()

        question_items = []
        for r in rows:
            question_items.append({
                "id": r["id"],
                "category": r["category"],
                "category_name": r["category_name"],
                "question_text": r["question_text"],
                "options": json.loads(r["options_json"]),
                "correct_index": r["correct_index"],
                "explanation": r["explanation"],
                "difficulty_level": r["difficulty_level"],
                "status": r["status"],
                "source_channel": r["source_channel"],
                "report_count": r["report_count"],
                "created_at": r["created_at"]
            })

        # لیست کانال‌ها و دسته‌ها برای فیلتر
        cursor = await db.execute("SELECT code, name_fa FROM categories WHERE is_exam = 1")
        categories = [dict(r) for r in await cursor.fetchall()]

        cursor = await db.execute("SELECT DISTINCT source_channel FROM questions WHERE source_channel IS NOT NULL")
        channels = [r[0] for r in await cursor.fetchall()]

    total_pages = max(1, (total_count + page_size - 1) // page_size)

    return templates.TemplateResponse(
        request=request,
        name="admin/questions.html",
        context={
            "user": user,
            "questions": question_items,
            "categories": categories,
            "channels": channels,
            "search_query": q or "",
            "selected_category": category or "all",
            "selected_status": status or "all",
            "selected_channel": channel or "all",
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "settings": settings
        }
    )

@router.post("/questions/save")
async def save_question_admin(
    question_id: Optional[int] = Form(None),
    category: str = Form(...),
    question_text: str = Form(...),
    opt0: str = Form(...),
    opt1: str = Form(...),
    opt2: str = Form(...),
    opt3: str = Form(...),
    correct_index: int = Form(...),
    explanation: Optional[str] = Form(None),
    difficulty_level: str = Form("medium"),
    status: str = Form("published")
):
    import hashlib
    options = [opt0.strip(), opt1.strip(), opt2.strip(), opt3.strip()]
    options_json = json.dumps(options, ensure_ascii=False)
    text_hash = hashlib.md5(question_text.strip().encode("utf-8")).hexdigest()

    async with get_db() as db:
        if question_id:
            await db.execute("""
                UPDATE questions
                SET category = ?, question_text = ?, options_json = ?,
                    correct_index = ?, explanation = ?, difficulty_level = ?, status = ?
                WHERE id = ?
            """, (category, question_text.strip(), options_json, correct_index, explanation, difficulty_level, status, question_id))
        else:
            await db.execute("""
                INSERT INTO questions (
                    category, question_text, options_json, correct_index,
                    explanation, difficulty_level, status, text_hash, source_channel
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'manual_admin')
            """, (category, question_text.strip(), options_json, correct_index, explanation, difficulty_level, status, text_hash))
        await db.commit()

    return RedirectResponse(url="/admin/questions", status_code=303)

@router.post("/questions/{q_id}/delete")
async def delete_question_admin(q_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM questions WHERE id = ?", (q_id,))
        await db.commit()
    return HTMLResponse(f'<span class="text-xs text-rose-500 font-bold">حذف شد</span>')

# --- مدیریت اخبار استخدامی ---
@router.get("/news", response_class=HTMLResponse)
async def admin_news_page(request: Request, response: Response):
    user = await require_admin(request, response)

    async with get_db() as db:
        cursor = await db.execute("""
            SELECT n.*, c.name_fa as category_name
            FROM news n
            LEFT JOIN categories c ON n.category = c.code
            ORDER BY n.id DESC LIMIT 100
        """)
        news_items = [dict(r) for r in await cursor.fetchall()]

        cursor = await db.execute("SELECT code, name_fa FROM categories WHERE is_news = 1")
        categories = [dict(r) for r in await cursor.fetchall()]

    return templates.TemplateResponse(
        request=request,
        name="admin/news.html",
        context={
            "user": user,
            "news_items": news_items,
            "categories": categories,
            "settings": settings
        }
    )

@router.post("/news/save")
async def save_news_admin(
    title: str = Form(...),
    summary: str = Form(...),
    content: str = Form(...),
    category: str = Form("employment"),
    cta_category: Optional[str] = Form("icdl"),
    news_id: Optional[int] = Form(None)
):
    from app.crawler.parser import slugify
    slug = slugify(title)

    async with get_db() as db:
        if news_id:
            await db.execute("""
                UPDATE news
                SET title = ?, summary = ?, content = ?, category = ?, cta_category = ?
                WHERE id = ?
            """, (title.strip(), summary.strip(), content.strip(), category, cta_category, news_id))
        else:
            await db.execute("""
                INSERT INTO news (title, slug, summary, content, category, cta_category, source_channel, is_published)
                VALUES (?, ?, ?, ?, ?, ?, 'manual_admin', 1)
            """, (title.strip(), slug, summary.strip(), content.strip(), category, cta_category))
        await db.commit()

    return RedirectResponse(url="/admin/news", status_code=303)

@router.post("/news/{n_id}/delete")
async def delete_news_admin(n_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM news WHERE id = ?", (n_id,))
        await db.commit()
    return HTMLResponse('<span class="text-xs text-rose-500 font-bold">خبر حذف شد</span>')

@router.post("/news/{n_id}/toggle")
async def toggle_news_published(n_id: int):
    async with get_db() as db:
        await db.execute("UPDATE news SET is_published = 1 - is_published WHERE id = ?", (n_id,))
        await db.commit()
        cursor = await db.execute("SELECT is_published FROM news WHERE id = ?", (n_id,))
        new_val = (await cursor.fetchone())[0]

    color = "bg-emerald-100 text-emerald-800" if new_val else "bg-slate-100 text-slate-500"
    label = "منتشر شده" if new_val else "پیش‌نویس"
    return HTMLResponse(f'<span class="px-2.5 py-1 rounded-full text-[11px] font-bold {color}">{label}</span>')
