from fastapi import APIRouter, Request, Response, HTTPException, Query
from fastapi.responses import HTMLResponse
from typing import Optional
import aiosqlite

from app.config import settings
from app.database import get_db
from app.auth_helper import get_current_user_and_guest
from app.templates_config import templates

router = APIRouter(prefix="/news", tags=["news"])

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def news_list_page(
    request: Request,
    response: Response,
    category: Optional[str] = None,
    q: Optional[str] = None,
    page: int = Query(1, ge=1)
):
    user, guest_token = await get_current_user_and_guest(request, response)
    page_size = 9
    offset = (page - 1) * page_size

    async with get_db() as db:
        conditions = ["is_published = 1"]
        params = []

        if category and category != "all":
            conditions.append("category = ?")
            params.append(category)

        if q:
            conditions.append("(title LIKE ? OR content LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])

        where_clause = " WHERE " + " AND ".join(conditions)

        # تعداد کل اخبار
        cursor = await db.execute(f"SELECT COUNT(*) FROM news {where_clause}", params)
        total_count = (await cursor.fetchone())[0]

        # دریافت اخبار صفحه جاری
        cursor = await db.execute(f"""
            SELECT n.id, n.title, n.slug, n.summary, n.category, n.created_at, n.views_count,
                   c.name_fa as category_name
            FROM news n
            LEFT JOIN categories c ON n.category = c.code
            {where_clause}
            ORDER BY n.id DESC
            LIMIT ? OFFSET ?
        """, (*params, page_size, offset))
        news_items = [dict(r) for r in await cursor.fetchall()]

        # دسته‌بندی‌های فعال خبری
        cursor = await db.execute("SELECT code, name_fa FROM categories WHERE is_news = 1")
        news_categories = [dict(r) for r in await cursor.fetchall()]

    total_pages = max(1, (total_count + page_size - 1) // page_size)

    return templates.TemplateResponse(
        request=request,
        name="news/list.html",
        context={
            "user": user,
            "news_items": news_items,
            "news_categories": news_categories,
            "selected_category": category or "all",
            "search_query": q or "",
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "settings": settings
        }
    )

@router.get("/{slug}", response_class=HTMLResponse)
async def news_detail_page(request: Request, response: Response, slug: str):
    user, guest_token = await get_current_user_and_guest(request, response)

    async with get_db() as db:
        # افزایش تعداد بازدید
        await db.execute("UPDATE news SET views_count = views_count + 1 WHERE slug = ?", (slug,))
        await db.commit()

        cursor = await db.execute("""
            SELECT n.*, c.name_fa as category_name, c.color as category_color
            FROM news n
            LEFT JOIN categories c ON n.category = c.code
            WHERE n.slug = ? AND n.is_published = 1
        """, (slug,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="خبر مورد نظر یافت نشد")

        article = dict(row)

        # اخبار مرتبط
        cursor = await db.execute("""
            SELECT id, title, slug, created_at, category
            FROM news
            WHERE category = ? AND slug != ? AND is_published = 1
            ORDER BY id DESC LIMIT 4
        """, (article["category"], slug))
        related_news = [dict(r) for r in await cursor.fetchall()]

        # اطلاعات دسته آزمون متناظر برای دکمه CTA انتهای خبر
        cta_code = article.get("cta_category") or "icdl"
        cursor = await db.execute("""
            SELECT code, name_fa, description, icon
            FROM categories
            WHERE code = ?
        """, (cta_code,))
        cta_cat = await cursor.fetchone()
        cta_category_data = dict(cta_cat) if cta_cat else None

    # تخمین زمان مطالعه (هر ۲۵۰ کلمه = ۱ دقیقه)
    word_count = len(article["content"].split())
    reading_time = max(1, word_count // 200)

    return templates.TemplateResponse(
        request=request,
        name="news/detail.html",
        context={
            "user": user,
            "article": article,
            "related_news": related_news,
            "cta_category": cta_category_data,
            "reading_time": reading_time,
            "settings": settings
        }
    )
