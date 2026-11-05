from rapidfuzz import fuzz
from typing import List, Tuple
import aiosqlite

async def is_question_duplicate(
    db: aiosqlite.Connection,
    category: str,
    text_hash: str,
    question_text: str,
    threshold: int = 85
) -> Tuple[bool, str]:
    """
    بررسی تکراری بودن سوال:
    ۱. بررسی هش دقیق (Hash Check)
    ۲. بررسی فازی شباهت کلمات (Fuzzy Token Match) با ۵۰۰ سوال اخیر همان درس
    خروجی: (آیا تکراری است؟ , دلیل)
    """
    # ۱. بررسی هش متنی دقیق
    cursor = await db.execute("SELECT id FROM questions WHERE text_hash = ?", (text_hash,))
    row = await cursor.fetchone()
    if row:
        return True, "exact_hash_match"

    # ۲. بررسی فازی با سوالات اخیر همان دسته‌بندی
    cursor = await db.execute(
        "SELECT question_text FROM questions WHERE category = ? ORDER BY id DESC LIMIT 500",
        (category,)
    )
    existing_questions = await cursor.fetchall()

    for (existing_q,) in existing_questions:
        ratio = fuzz.token_sort_ratio(question_text, existing_q)
        if ratio >= threshold:
            return True, f"fuzzy_match_{ratio}%"

    return False, "unique"
