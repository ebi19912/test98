from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
import aiosqlite

from app.config import settings
from app.database import get_db
from app.auth_helper import get_current_user_and_guest
from app.templates_config import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request, response: Response):
    user, guest_token = await get_current_user_and_guest(request, response)

    async with get_db() as db:
        # آمار کلیدی سیستم
        cursor = await db.execute("SELECT COUNT(*) FROM questions WHERE status = 'published'")
        total_questions = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM exam_attempts WHERE is_finished = 1")
        total_exams = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]

        # دسته‌بندی‌های آزمون به همراه تعداد سوالات فعال در هر دسته
        cursor = await db.execute("""
            SELECT c.code, c.name_fa, c.description, c.icon, c.color,
                   COUNT(q.id) as question_count
            FROM categories c
            LEFT JOIN questions q ON c.code = q.category AND q.status = 'published'
            WHERE c.is_exam = 1
            GROUP BY c.code
            ORDER BY question_count DESC
        """)
        exam_categories = [dict(r) for r in await cursor.fetchall()]

        # جدیدترین اخبار استخدامی
        cursor = await db.execute("""
            SELECT id, title, slug, summary, category, created_at
            FROM news
            WHERE is_published = 1
            ORDER BY id DESC LIMIT 4
        """)
        latest_news = [dict(r) for r in await cursor.fetchall()]

    resp = templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "user": user,
            "total_questions": total_questions,
            "total_exams": total_exams,
            "total_users": total_users,
            "categories": exam_categories,
            "latest_news": latest_news,
            "settings": settings
        }
    )
    resp.set_cookie("guest_token", guest_token, max_age=30*24*3600, httponly=True)
    return resp
