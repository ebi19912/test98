from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import json

from app.config import settings
from app.database import get_db
from app.auth_helper import get_current_user_and_guest
from app.templates_config import templates
from app.leitner import get_user_leitner_stats

router = APIRouter(prefix="/user", tags=["user"])

@router.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request, response: Response):
    user, guest_token = await get_current_user_and_guest(request, response)
    if not user:
        return RedirectResponse(url="/?login=required", status_code=303)

    user_id = user["id"]

    async with get_db() as db:
        # ۱. خلاصه وضعیت آزمون‌ها
        cursor = await db.execute("""
            SELECT 
                COUNT(*) as total_attempts,
                AVG(raw_score) as avg_score,
                MAX(raw_score) as max_score,
                SUM(correct_count) as total_correct,
                SUM(wrong_count) as total_wrong,
                AVG(t_score) as avg_t_score
            FROM exam_attempts
            WHERE user_id = ? AND is_finished = 1
        """, (user_id,))
        stats_row = await cursor.fetchone()
        
        tot_c = stats_row["total_correct"] or 0
        tot_w = stats_row["total_wrong"] or 0
        tot_solved = tot_c + tot_w
        success_rate = round((tot_c / tot_solved * 100), 1) if tot_solved > 0 else 0

        stats = {
            "total_attempts": stats_row["total_attempts"] or 0,
            "avg_score": round(stats_row["avg_score"] or 0, 1),
            "max_score": round(stats_row["max_score"] or 0, 1),
            "total_correct": tot_c,
            "total_wrong": tot_w,
            "total_solved": tot_solved,
            "success_rate": success_rate,
            "avg_t_score": int(stats_row["avg_t_score"] or 500)
        }

        # تعداد سوالات نشان‌شده
        cursor = await db.execute("SELECT COUNT(*) FROM user_bookmarks WHERE user_id = ?", (user_id,))
        bookmarks_count = (await cursor.fetchone())[0]

        # ۲. نقاط قوت و ضعف تفکیکی بر اساس دروس (رنگی: سبز بالای ۶۰٪، زرد ۳۰ تا ۶۰٪، قرمز زیر ۳۰٪)
        cursor = await db.execute("""
            SELECT 
                c.code, c.name_fa, c.icon,
                AVG(ea.raw_score) as avg_score,
                COUNT(ea.id) as exam_count
            FROM categories c
            LEFT JOIN exam_attempts ea ON ea.category = c.code AND ea.user_id = ? AND ea.is_finished = 1
            WHERE c.is_exam = 1
            GROUP BY c.code
            ORDER BY exam_count DESC, avg_score ASC
        """, (user_id,))
        subjects = []
        weakest_subject = None

        for r in await cursor.fetchall():
            avg = round(r["avg_score"] or 0, 1)
            count = r["exam_count"] or 0
            if count == 0:
                color_class = "border-slate-200 text-slate-500 bg-slate-50"
                badge_text = "بدون آزمون"
                badge_color = "bg-slate-200 text-slate-700"
                bar_color = "bg-slate-300"
            elif avg >= 60:
                color_class = "border-emerald-200 text-emerald-800 bg-emerald-50/50"
                badge_text = "نقطه قوت (عالی)"
                badge_color = "bg-emerald-100 text-emerald-700"
                bar_color = "bg-emerald-500"
            elif avg >= 30:
                color_class = "border-amber-200 text-amber-800 bg-amber-50/50"
                badge_text = "متوسط (نیازمند تمرین)"
                badge_color = "bg-amber-100 text-amber-700"
                bar_color = "bg-amber-500"
            else:
                color_class = "border-rose-200 text-rose-800 bg-rose-50/50"
                badge_text = "نقطه ضعف (نیازمند توجه)"
                badge_color = "bg-rose-100 text-rose-700"
                bar_color = "bg-rose-500"

            sub_item = {
                "code": r["code"],
                "name": r["name_fa"],
                "icon": r["icon"],
                "avg_score": avg,
                "exam_count": count,
                "color_class": color_class,
                "badge_text": badge_text,
                "badge_color": badge_color,
                "bar_color": bar_color,
                "progress_width": min(100, max(5, int(avg))) if count > 0 else 0
            }
            subjects.append(sub_item)

            if count > 0 and (weakest_subject is None or avg < weakest_subject["avg_score"]):
                weakest_subject = sub_item

        # ۳. آخرین آزمون‌های کاربر
        cursor = await db.execute("""
            SELECT 
                ea.*,
                c.name_fa as category_name
            FROM exam_attempts ea
            LEFT JOIN categories c ON ea.category = c.code
            WHERE ea.user_id = ? AND ea.is_finished = 1
            ORDER BY ea.id DESC LIMIT 6
        """, (user_id,))
        recent_exams = [dict(r) for r in await cursor.fetchall()]

        # ۴. وضعیت جعبه لایتنر
        leitner_stats = await get_user_leitner_stats(db, user_id)

    return templates.TemplateResponse(
        request=request,
        name="user/dashboard.html",
        context={
            "user": user,
            "stats": stats,
            "subjects": subjects,
            "weakest_subject": weakest_subject,
            "bookmarks_count": bookmarks_count,
            "recent_exams": recent_exams,
            "leitner": leitner_stats,
            "settings": settings
        }
    )

@router.get("/leitner", response_class=HTMLResponse)
async def user_leitner_page(request: Request, response: Response):
    user, _ = await get_current_user_and_guest(request, response)
    if not user:
        return RedirectResponse(url="/?login=required", status_code=303)

    user_id = user["id"]

    async with get_db() as db:
        leitner_stats = await get_user_leitner_stats(db, user_id)

        # دریافت سوالات موجود در جعبه‌ها
        cursor = await db.execute("""
            SELECT 
                ul.box_level, ul.next_review_at, ul.consecutive_correct,
                q.id as question_id, q.question_text, q.category, q.options_json,
                q.explanation, c.name_fa as category_name
            FROM user_leitner ul
            JOIN questions q ON ul.question_id = q.id
            LEFT JOIN categories c ON q.category = c.code
            WHERE ul.user_id = ?
            ORDER BY ul.box_level ASC, ul.next_review_at ASC
        """, (user_id,))
        rows = await cursor.fetchall()

        leitner_questions = []
        for r in rows:
            leitner_questions.append({
                "box_level": r["box_level"],
                "next_review_at": r["next_review_at"],
                "consecutive_correct": r["consecutive_correct"],
                "question_id": r["question_id"],
                "question_text": r["question_text"],
                "category_name": r["category_name"],
                "explanation": r["explanation"]
            })

    return templates.TemplateResponse(
        request=request,
        name="user/leitner.html",
        context={
            "user": user,
            "leitner": leitner_stats,
            "questions": leitner_questions,
            "settings": settings
        }
    )

@router.get("/bookmarks", response_class=HTMLResponse)
async def user_bookmarks_page(request: Request, response: Response):
    user, _ = await get_current_user_and_guest(request, response)
    if not user:
        return RedirectResponse(url="/?login=required", status_code=303)

    user_id = user["id"]

    async with get_db() as db:
        cursor = await db.execute("""
            SELECT 
                ub.id as bookmark_id, ub.created_at,
                q.id as question_id, q.question_text, q.options_json, q.correct_index,
                q.explanation, c.name_fa as category_name
            FROM user_bookmarks ub
            JOIN questions q ON ub.question_id = q.id
            LEFT JOIN categories c ON q.category = c.code
            WHERE ub.user_id = ?
            ORDER BY ub.id DESC
        """, (user_id,))
        rows = await cursor.fetchall()

        bookmarks = []
        for r in rows:
            bookmarks.append({
                "bookmark_id": r["bookmark_id"],
                "question_id": r["question_id"],
                "question_text": r["question_text"],
                "options": json.loads(r["options_json"]),
                "correct_index": r["correct_index"],
                "explanation": r["explanation"],
                "category_name": r["category_name"]
            })

    return templates.TemplateResponse(
        request=request,
        name="user/bookmarks.html",
        context={
            "user": user,
            "bookmarks": bookmarks,
            "settings": settings
        }
    )

@router.get("/history", response_class=HTMLResponse)
async def user_history_page(
    request: Request,
    response: Response,
    category: str = "",
    page: int = 1
):
    user, _ = await get_current_user_and_guest(request, response)
    if not user:
        return RedirectResponse(url="/?login=required", status_code=303)

    user_id = user["id"]
    limit = 15
    page = max(1, page)
    offset = (page - 1) * limit

    async with get_db() as db:
        # ۱. لیست دسته‌بندی‌ها برای فیلتر
        cat_cursor = await db.execute("SELECT code, name_fa FROM categories WHERE is_exam = 1 ORDER BY code ASC")
        categories = [dict(r) for r in await cat_cursor.fetchall()]

        # ۲. محاسبه آمار کلی کاربر در آزمون‌ها
        stats_cursor = await db.execute("""
            SELECT 
                COUNT(*) as total_attempts,
                AVG(raw_score) as avg_score,
                MAX(raw_score) as max_score,
                SUM(correct_count) as total_correct,
                SUM(wrong_count) as total_wrong,
                SUM(unanswered_count) as total_unanswered
            FROM exam_attempts
            WHERE user_id = ? AND is_finished = 1
        """, (user_id,))
        stats_row = await stats_cursor.fetchone()
        stats = {
            "total_attempts": stats_row["total_attempts"] or 0,
            "avg_score": round(stats_row["avg_score"] or 0, 1),
            "max_score": round(stats_row["max_score"] or 0, 1),
            "total_correct": stats_row["total_correct"] or 0,
            "total_wrong": stats_row["total_wrong"] or 0,
            "total_unanswered": stats_row["total_unanswered"] or 0,
            "total_solved": (stats_row["total_correct"] or 0) + (stats_row["total_wrong"] or 0)
        }

        # ۳. کوئری آزمون‌ها با فیلتر دسته‌بندی
        where_clause = "WHERE ea.user_id = ? AND ea.is_finished = 1"
        params = [user_id]
        if category:
            where_clause += " AND ea.category = ?"
            params.append(category)

        # شمارش کل برای صفحه‌بندی
        count_cursor = await db.execute(f"SELECT COUNT(*) as total FROM exam_attempts ea {where_clause}", params)
        count_row = await count_cursor.fetchone()
        total_items = count_row["total"] or 0
        total_pages = max(1, (total_items + limit - 1) // limit)

        # دریافت لیست آزمون‌ها
        query_params = list(params) + [limit, offset]
        cursor = await db.execute(f"""
            SELECT 
                ea.*,
                c.name_fa as category_name
            FROM exam_attempts ea
            LEFT JOIN categories c ON ea.category = c.code
            {where_clause}
            ORDER BY ea.id DESC
            LIMIT ? OFFSET ?
        """, query_params)
        rows = await cursor.fetchall()
        attempts = [dict(r) for r in rows]

    return templates.TemplateResponse(
        request=request,
        name="user/history.html",
        context={
            "user": user,
            "stats": stats,
            "attempts": attempts,
            "categories": categories,
            "current_category": category,
            "page": page,
            "total_pages": total_pages,
            "total_items": total_items,
            "settings": settings
        }
    )

