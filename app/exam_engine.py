import json
import math
import datetime
from typing import Optional, Dict, Any, List, Tuple
import aiosqlite

from app.database import get_db
from app.leitner import update_question_leitner_status

async def create_exam(
    category: str,
    total_questions: int = 15,
    user_id: Optional[int] = None,
    guest_token: Optional[str] = None,
    exam_type: str = "custom",
    has_negative_marking: bool = True,
    duration_minutes: int = 20,
    filter_mode: str = "smart"
) -> Dict[str, Any]:
    """
    ساخت آزمون هوشمند با ترکیب وزنی:
    - ۶۰٪ سوالات جدید
    - ۳۰٪ خطاهای گذشته داوطلب
    - ۱۰٪ مرور دوره‌ای جعبه لایتنر
    """
    async with get_db() as db:
        now = datetime.datetime.utcnow()
        expires_at = now + datetime.timedelta(minutes=duration_minutes)

        cat_condition = "AND category = ?" if category and category != "all" else ""
        cat_params = (category,) if category and category != "all" else ()

        selected_q_ids: List[int] = []

        if filter_mode == "mistakes_only":
            # فقط خطاهای قبلی
            cursor = await db.execute(f"""
                SELECT q.id FROM questions q
                JOIN user_answers ua ON q.id = ua.question_id
                WHERE q.status = 'published' {cat_condition}
                  AND ua.is_correct = 0
                  AND (ua.user_id = ? OR ua.guest_token = ?)
                GROUP BY q.id
                ORDER BY RANDOM() LIMIT ?
            """, (*cat_params, user_id, guest_token, total_questions))
            rows = await cursor.fetchall()
            selected_q_ids = [r[0] for r in rows]

        elif filter_mode == "bookmarked_only" and user_id:
            # فقط سوالات نشان‌شده
            cursor = await db.execute(f"""
                SELECT q.id FROM questions q
                JOIN user_bookmarks ub ON q.id = ub.question_id
                WHERE q.status = 'published' {cat_condition}
                  AND ub.user_id = ?
                ORDER BY RANDOM() LIMIT ?
            """, (*cat_params, user_id, total_questions))
            rows = await cursor.fetchall()
            selected_q_ids = [r[0] for r in rows]

        else:
            # حالت پیش‌فرض هوشمند (Smart Blending)
            unseen_target = max(1, round(0.60 * total_questions))
            errors_target = max(1, round(0.30 * total_questions))
            leitner_target = total_questions - (unseen_target + errors_target)

            # ۱. استخر سوالات جدید (دیده‌نشده)
            cursor = await db.execute(f"""
                SELECT id FROM questions
                WHERE status = 'published' {cat_condition}
                  AND id NOT IN (
                      SELECT question_id FROM user_answers
                      WHERE (user_id = ? AND ? IS NOT NULL) OR (guest_token = ? AND ? IS NOT NULL)
                  )
                ORDER BY RANDOM() LIMIT ?
            """, (*cat_params, user_id, user_id, guest_token, guest_token, unseen_target))
            unseen_ids = [r[0] for r in await cursor.fetchall()]
            selected_q_ids.extend(unseen_ids)

            # ۲. استخر خطاهای قبلی کاربر
            if user_id or guest_token:
                cursor = await db.execute(f"""
                    SELECT q.id FROM questions q
                    JOIN user_answers ua ON q.id = ua.question_id
                    WHERE q.status = 'published' {cat_condition}
                      AND ua.is_correct = 0
                      AND ((ua.user_id = ? AND ? IS NOT NULL) OR (ua.guest_token = ? AND ? IS NOT NULL))
                      AND q.id NOT IN ({','.join(['?']*len(selected_q_ids)) if selected_q_ids else '0'})
                    GROUP BY q.id
                    ORDER BY RANDOM() LIMIT ?
                """, (*cat_params, user_id, user_id, guest_token, guest_token, *selected_q_ids, errors_target))
                error_ids = [r[0] for r in await cursor.fetchall()]
                selected_q_ids.extend(error_ids)

            # ۳. استخر لایتنر (موعد مرور رسیده)
            if user_id:
                cursor = await db.execute(f"""
                    SELECT q.id FROM questions q
                    JOIN user_leitner ul ON q.id = ul.question_id
                    WHERE q.status = 'published' {cat_condition}
                      AND ul.user_id = ?
                      AND ul.next_review_at <= ?
                      AND q.id NOT IN ({','.join(['?']*len(selected_q_ids)) if selected_q_ids else '0'})
                    ORDER BY RANDOM() LIMIT ?
                """, (*cat_params, user_id, now.isoformat(), *selected_q_ids, leitner_target))
                leitner_ids = [r[0] for r in await cursor.fetchall()]
                selected_q_ids.extend(leitner_ids)

        # در صورت کمبود سوال در هر استخر، با سوالات عمومی تکمیل شود
        needed = total_questions - len(selected_q_ids)
        if needed > 0:
            cursor = await db.execute(f"""
                SELECT id FROM questions
                WHERE status = 'published' {cat_condition}
                  AND id NOT IN ({','.join(['?']*len(selected_q_ids)) if selected_q_ids else '0'})
                ORDER BY RANDOM() LIMIT ?
            """, (*cat_params, *selected_q_ids, needed))
            fill_ids = [r[0] for r in await cursor.fetchall()]
            selected_q_ids.extend(fill_ids)

        if not selected_q_ids:
            # اگر هیچ سوالی یافت نشد، همه سوالات منتشرشده را می‌گیریم
            cursor = await db.execute("SELECT id FROM questions WHERE status = 'published' ORDER BY RANDOM() LIMIT ?", (total_questions,))
            selected_q_ids = [r[0] for r in await cursor.fetchall()]

        actual_total = len(selected_q_ids)

        # ایجاد رکورد آزمون در exam_attempts
        cursor = await db.execute("""
            INSERT INTO exam_attempts (
                user_id, guest_token, exam_type, category, total_questions,
                has_negative_marking, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            guest_token,
            exam_type,
            category or "all",
            actual_total,
            1 if has_negative_marking else 0,
            expires_at.isoformat()
        ))
        attempt_id = cursor.lastrowid

        # ثبت سوالات تخصیص‌یافته در exam_questions
        for order, q_id in enumerate(selected_q_ids, 1):
            await db.execute("""
                INSERT INTO exam_questions (attempt_id, question_id, question_order)
                VALUES (?, ?, ?)
            """, (attempt_id, q_id, order))

        await db.commit()

        return {
            "attempt_id": attempt_id,
            "total_questions": actual_total,
            "expires_at": expires_at.isoformat(),
            "duration_minutes": duration_minutes,
            "category": category
        }

async def get_exam_questions_for_taking(attempt_id: int) -> List[Dict[str, Any]]:
    """
    استخراج سوالات برای صفحه برگزاری آزمون
    نکته امنیتی حیاتی: کلید پاسخ صحیح (correct_index) و توضیح در خروجی ارسال نمی‌شوند!
    """
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT 
                eq.question_order,
                q.id as question_id,
                q.category,
                q.question_text,
                q.options_json,
                ua.selected_option
            FROM exam_questions eq
            JOIN questions q ON eq.question_id = q.id
            LEFT JOIN user_answers ua ON ua.attempt_id = eq.attempt_id AND ua.question_id = q.id
            WHERE eq.attempt_id = ?
            ORDER BY eq.question_order ASC
        """, (attempt_id,))
        rows = await cursor.fetchall()

        questions = []
        for r in rows:
            questions.append({
                "order": r["question_order"],
                "question_id": r["question_id"],
                "category": r["category"],
                "question_text": r["question_text"],
                "options": json.loads(r["options_json"]),
                "selected_option": r["selected_option"]
            })
        return questions

async def record_user_answer(
    attempt_id: int,
    question_id: int,
    selected_option: Optional[int],
    user_id: Optional[int] = None,
    guest_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    ثبت آنی پاسخ کاربر به یک سوال در جدول user_answers بدون رفرش صفحه (HTMX)
    """
    async with get_db() as db:
        # دریافت پاسخ صحیح جهت مقایسه در سمت سرور
        cursor = await db.execute("SELECT correct_index FROM questions WHERE id = ?", (question_id,))
        q_row = await cursor.fetchone()
        if not q_row:
            return {"status": "error", "message": "سوال یافت نشد"}

        correct_idx = q_row[0]
        is_correct = 1 if (selected_option is not None and selected_option == correct_idx) else 0

        # ذخیره یا به‌روزرسانی پاسخ
        await db.execute("""
            INSERT INTO user_answers (attempt_id, user_id, guest_token, question_id, selected_option, is_correct)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(attempt_id, question_id) DO UPDATE SET
                selected_option = excluded.selected_option,
                is_correct = excluded.is_correct,
                answered_at = CURRENT_TIMESTAMP
        """, (attempt_id, user_id, guest_token, question_id, selected_option, is_correct))

        await db.commit()
        return {"status": "success", "is_correct": is_correct}

async def finish_and_grade_exam(attempt_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    تصحیح نهایی آزمون، محاسبه نمره خام، تراز استاندارد، رتبه و به‌روزرسانی لایتنر
    """
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM exam_attempts WHERE id = ?", (attempt_id,))
        attempt = await cursor.fetchone()
        if not attempt:
            raise ValueError("آزمون یافت نشد")

        total_q = attempt["total_questions"]
        has_negative = bool(attempt["has_negative_marking"])
        category = attempt["category"]
        effective_user_id = user_id or attempt["user_id"]

        # استخراج آمار پاسخ‌ها
        cursor = await db.execute("""
            SELECT 
                COUNT(CASE WHEN is_correct = 1 THEN 1 END) as correct_count,
                COUNT(CASE WHEN is_correct = 0 AND selected_option IS NOT NULL THEN 1 END) as wrong_count,
                COUNT(CASE WHEN selected_option IS NULL THEN 1 END) as null_count
            FROM user_answers
            WHERE attempt_id = ?
        """, (attempt_id,))
        res = await cursor.fetchone()
        c_count = res["correct_count"] or 0
        w_count = res["wrong_count"] or 0
        answered_total = c_count + w_count
        unanswered_count = total_q - answered_total

        # فرمول نمره خام استخدامی کشور: (3 * درست - غلط) / (3 * کل) * 100
        if has_negative:
            raw_score = ((3 * c_count - w_count) / (3 * total_q)) * 100.0 if total_q > 0 else 0.0
        else:
            raw_score = (c_count / total_q) * 100.0 if total_q > 0 else 0.0

        raw_score = round(raw_score, 2)

        # به‌روزرسانی وضعیت تلاش در دیتابیس
        now = datetime.datetime.utcnow().isoformat()
        await db.execute("""
            UPDATE exam_attempts
            SET correct_count = ?,
                wrong_count = ?,
                unanswered_count = ?,
                raw_score = ?,
                is_finished = 1,
                finished_at = ?
            WHERE id = ?
        """, (c_count, w_count, unanswered_count, raw_score, now, attempt_id))

        # محاسبه میانگین و انحراف معیار جهت تراز T-Score
        cursor = await db.execute("""
            SELECT AVG(raw_score) as mean_val, COUNT(*) as count_val
            FROM exam_attempts
            WHERE category = ? AND is_finished = 1
        """, (category,))
        stats_row = await cursor.fetchone()
        mean_val = stats_row["mean_val"] or raw_score
        count_val = stats_row["count_val"] or 1

        # انحراف معیار
        cursor = await db.execute("""
            SELECT AVG((raw_score - ?)*(raw_score - ?)) as var_val
            FROM exam_attempts
            WHERE category = ? AND is_finished = 1
        """, (mean_val, mean_val, category))
        var_val = (await cursor.fetchone())["var_val"] or 0.0
        std_dev = math.sqrt(var_val) if var_val > 0 else 15.0

        # فرمول استاندارد تراز سراسری: T = 500 + 100 * ((Raw - Mean) / StdDev)
        if std_dev > 0:
            t_score = round(500.0 + 100.0 * ((raw_score - mean_val) / std_dev), 1)
        else:
            t_score = 500.0

        # محاسبه رتبه با Window Function
        cursor = await db.execute("""
            WITH ranked AS (
                SELECT id, RANK() OVER (ORDER BY raw_score DESC) as calculated_rank
                FROM exam_attempts
                WHERE category = ? AND is_finished = 1
            )
            SELECT calculated_rank FROM ranked WHERE id = ?
        """, (category, attempt_id))
        rank_row = await cursor.fetchone()
        calculated_rank = rank_row["calculated_rank"] if rank_row else 1

        # به‌روزرسانی تراز و رتبه
        await db.execute("""
            UPDATE exam_attempts
            SET t_score = ?, rank = ?
            WHERE id = ?
        """, (t_score, calculated_rank, attempt_id))

        # به‌روزرسانی جعبه لایتنر برای کاربر عضو
        if effective_user_id:
            cursor = await db.execute("""
                SELECT question_id, is_correct
                FROM user_answers
                WHERE attempt_id = ? AND selected_option IS NOT NULL
            """, (attempt_id,))
            answers = await cursor.fetchall()
            for q_id, is_corr in answers:
                await update_question_leitner_status(db, effective_user_id, q_id, bool(is_corr))

        await db.commit()

        return {
            "attempt_id": attempt_id,
            "raw_score": raw_score,
            "t_score": t_score,
            "rank": calculated_rank,
            "total_participants": count_val,
            "correct_count": c_count,
            "wrong_count": w_count,
            "unanswered_count": unanswered_count
        }

async def get_exam_report_details(attempt_id: int) -> Dict[str, Any]:
    """
    دریافت گزارش تفصیلی و کارنامه کامل آزمون برای نمایش به کاربر
    """
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT 
                ea.*,
                cat.name_fa as category_name
            FROM exam_attempts ea
            LEFT JOIN categories cat ON ea.category = cat.code
            WHERE ea.id = ?
        """, (attempt_id,))
        attempt = await cursor.fetchone()
        if not attempt:
            return {}

        attempt_data = dict(attempt)

        # استخراج تک‌تک سوالات به همراه گزینه‌ها، انتخاب کاربر، پاسخ صحیح و توضیح
        cursor = await db.execute("""
            SELECT 
                eq.question_order,
                q.id as question_id,
                q.category,
                q.question_text,
                q.options_json,
                q.correct_index,
                q.explanation,
                q.difficulty_level,
                ua.selected_option,
                ua.is_correct
            FROM exam_questions eq
            JOIN questions q ON eq.question_id = q.id
            LEFT JOIN user_answers ua ON ua.attempt_id = eq.attempt_id AND ua.question_id = q.id
            WHERE eq.attempt_id = ?
            ORDER BY eq.question_order ASC
        """, (attempt_id,))
        rows = await cursor.fetchall()

        questions_detail = []
        for r in rows:
            questions_detail.append({
                "order": r["question_order"],
                "question_id": r["question_id"],
                "category": r["category"],
                "question_text": r["question_text"],
                "options": json.loads(r["options_json"]),
                "correct_index": r["correct_index"],
                "explanation": r["explanation"],
                "difficulty_level": r["difficulty_level"],
                "selected_option": r["selected_option"],
                "is_correct": r["is_correct"]
            })

        attempt_data["questions"] = questions_detail
        return attempt_data
