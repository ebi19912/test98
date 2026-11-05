import datetime
from typing import Dict, Any, List
import aiosqlite
from app.database import get_db

BOX_INTERVALS = {
    1: 1,    # روز ۱
    2: 3,    # روز ۳
    3: 7,    # روز ۷
    4: 14,   # روز ۱۴
    5: 30    # روز ۳۰ (تسلط کامل)
}

async def update_question_leitner_status(db: aiosqlite.Connection, user_id: int, question_id: int, is_correct: bool):
    """
    به‌روزرسانی موقعیت سوال در جعبه لایتنر کاربر:
    - در صورت پاسخ درست: انتقال به جعبه بعدی
    - در صورت پاسخ اشتباه: بازگشت به جعبه اول
    """
    cursor = await db.execute(
        "SELECT box_level, consecutive_correct FROM user_leitner WHERE user_id = ? AND question_id = ?",
        (user_id, question_id)
    )
    row = await cursor.fetchone()
    now = datetime.datetime.utcnow()

    if row:
        current_box = row[0]
        consecutive = row[1]

        if is_correct:
            new_box = min(current_box + 1, 5)
            new_consecutive = consecutive + 1
        else:
            new_box = 1
            new_consecutive = 0

        interval_days = BOX_INTERVALS[new_box]
        next_review = now + datetime.timedelta(days=interval_days)

        await db.execute("""
            UPDATE user_leitner
            SET box_level = ?, consecutive_correct = ?, next_review_at = ?, last_reviewed_at = ?
            WHERE user_id = ? AND question_id = ?
        """, (new_box, new_consecutive, next_review.isoformat(), now.isoformat(), user_id, question_id))
    else:
        # سوال برای اولین بار ثبت می‌شود
        new_box = 2 if is_correct else 1
        new_consecutive = 1 if is_correct else 0
        interval_days = BOX_INTERVALS[new_box]
        next_review = now + datetime.timedelta(days=interval_days)

        await db.execute("""
            INSERT INTO user_leitner (user_id, question_id, box_level, consecutive_correct, next_review_at, last_reviewed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, question_id, new_box, new_consecutive, next_review.isoformat(), now.isoformat()))

async def get_user_leitner_stats(db: aiosqlite.Connection, user_id: int) -> Dict[str, Any]:
    """دریافت آمار جعبه‌های لایتنر کاربر برای نمایش در داشبورد"""
    cursor = await db.execute("""
        SELECT box_level, COUNT(*) 
        FROM user_leitner 
        WHERE user_id = ? 
        GROUP BY box_level
    """, (user_id,))
    rows = await cursor.fetchall()
    counts = {i: 0 for i in range(1, 6)}
    total = 0
    for box, count in rows:
        counts[box] = count
        total += count

    # تعداد سوالاتی که امروز موعد مرورشان رسیده است
    now = datetime.datetime.utcnow().isoformat()
    cursor = await db.execute("""
        SELECT COUNT(*) FROM user_leitner
        WHERE user_id = ? AND next_review_at <= ?
    """, (user_id, now))
    due_today = (await cursor.fetchone())[0]

    return {
        "boxes": counts,
        "total_in_leitner": total,
        "due_today": due_today,
        "mastered": counts[5]
    }
