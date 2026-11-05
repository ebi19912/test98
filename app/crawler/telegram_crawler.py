import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPoll, Message
from telethon.tl.functions.messages import SendVoteRequest
from telethon.errors import FloodWaitError

from app.config import settings
from app.database import get_db
from app.crawler.parser import (
    parse_text_question,
    parse_news_post,
    calculate_text_hash,
    clean_telegram_text
)
from app.crawler.deduplicator import is_question_duplicate

logger = logging.getLogger("crawler")
logger.setLevel(logging.INFO)

# ایجاد کلاینت تله‌تون در صورت تنظیم کلیدها
telegram_client: Optional[TelegramClient] = None

if settings.TELEGRAM_API_ID and settings.TELEGRAM_API_HASH:
    telegram_client = TelegramClient(
        settings.TELEGRAM_SESSION_NAME,
        settings.TELEGRAM_API_ID,
        settings.TELEGRAM_API_HASH
    )

async def extract_quiz_poll(client: TelegramClient, message: Message) -> Optional[Dict[str, Any]]:
    """
    استخراج تست از نوع Quiz تلگرام با تکنیک رأی خودکار برای بازگشایی پاسخ صحیح
    """
    try:
        if not message.media or not isinstance(message.media, MessageMediaPoll):
            return None

        poll = message.media.poll
        if not poll.quiz:
            return None  # نظرسنجی معمولی است نه آزمون تستی

        options = [ans.text.text for ans in poll.answers]
        if len(options) < 2:
            return None

        correct_idx = None
        explanation = None

        # رأی آزمایشی به گزینه اول برای دریافت پاسخ صحیح و راه حل از سرور تلگرام
        try:
            res = await client(SendVoteRequest(
                peer=message.peer_id,
                msg_id=message.id,
                options=[poll.answers[0].option]
            ))

            for update in getattr(res, "updates", []):
                if hasattr(update, "results") and update.results:
                    # استخراج پاسخ تشریحی (solution) در صورت وجود
                    if hasattr(update.results, "solution") and update.results.solution:
                        explanation = update.results.solution
                    # تشخیص اینکه کدام گزینه صحیح است
                    if hasattr(update.results, "results") and update.results.results:
                        for idx, ans_res in enumerate(update.results.results):
                            if getattr(ans_res, "correct", False):
                                correct_idx = idx
                                break
        except Exception as e:
            logger.warning(f"خطا در ارسال رأی آزمایشی Quiz (پیام {message.id}): {e}")

        question_text = poll.question.text.strip()
        text_hash = calculate_text_hash(question_text)

        return {
            "question_text": question_text,
            "options": options,
            "correct_index": correct_idx,
            "explanation": explanation,
            "status": "published" if correct_idx is not None else "needs_review",
            "text_hash": text_hash
        }
    except Exception as e:
        logger.error(f"خطای استخراج Quiz: {e}")
        return None

async def save_question_to_db(q_data: Dict[str, Any], channel: str, msg_id: int, category: str) -> bool:
    """ذخیره سوال استخراج‌شده در دیتابیس با بررسی عدم تکرار"""
    async with get_db() as db:
        # بررسی تکراری نبودن
        is_dup, reason = await is_question_duplicate(
            db, category, q_data["text_hash"], q_data["question_text"]
        )
        if is_dup:
            logger.info(f"سوال تکراری از کانال {channel} نادیده گرفته شد ({reason})")
            return False

        await db.execute("""
            INSERT INTO questions (
                category, question_text, options_json, correct_index,
                explanation, source_channel, source_msg_id, text_hash, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            category,
            q_data["question_text"],
            json.dumps(q_data["options"], ensure_ascii=False),
            q_data["correct_index"],
            q_data.get("explanation"),
            channel,
            msg_id,
            q_data["text_hash"],
            q_data["status"]
        ))

        # به‌روزرسانی آمار کانال
        await db.execute("""
            UPDATE crawler_channels
            SET last_msg_id = MAX(last_msg_id, ?),
                total_extracted = total_extracted + 1,
                last_crawled_at = CURRENT_TIMESTAMP
            WHERE channel_username = ?
        """, (msg_id, channel))

        await db.commit()
        return True

async def save_news_to_db(n_data: Dict[str, Any], channel: str, msg_id: int) -> bool:
    """ذخیره خبر استخراج‌شده در دیتابیس با اسلاگ یکتا"""
    async with get_db() as db:
        # بررسی وجود خبر با اسلاگ مشابه
        cursor = await db.execute("SELECT id FROM news WHERE slug = ? OR (source_channel = ? AND source_msg_id = ?)",
                                  (n_data["slug"], channel, msg_id))
        if await cursor.fetchone():
            return False

        await db.execute("""
            INSERT INTO news (
                title, slug, summary, content, category,
                source_channel, source_msg_id, cta_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            n_data["title"],
            n_data["slug"],
            n_data["summary"],
            n_data["content"],
            n_data["category"],
            channel,
            msg_id,
            n_data.get("cta_category", "employment")
        ))

        # به‌روزرسانی آمار کانال
        await db.execute("""
            UPDATE crawler_channels
            SET last_msg_id = MAX(last_msg_id, ?),
                total_extracted = total_extracted + 1,
                last_crawled_at = CURRENT_TIMESTAMP
            WHERE channel_username = ?
        """, (msg_id, channel))

        # ایندکس در FTS5
        await db.execute("""
            INSERT INTO news_fts (title, content) VALUES (?, ?)
        """, (n_data["title"], n_data["content"]))

        await db.commit()
        return True

async def process_channel_message(client: TelegramClient, message: Message, channel: str):
    """پردازش یک پیام مشخص از یک کانال بر اساس نگاشت دسته‌بندی"""
    ch_info = settings.TELEGRAM_CHANNELS.get(channel)
    if not ch_info:
        return

    content_type = ch_info["type"]
    category = ch_info["category"]

    # ۱. حالت نظرسنجی و کوییز تلگرام
    if message.media and isinstance(message.media, MessageMediaPoll):
        quiz_data = await extract_quiz_poll(client, message)
        if quiz_data:
            await save_question_to_db(quiz_data, channel, message.id, category)
            return

    # ۲. حالت پیام متنی
    raw_text = message.message or message.raw_text or ""
    if not raw_text:
        return

    if content_type == "question":
        q_data = parse_text_question(raw_text)
        if q_data:
            await save_question_to_db(q_data, channel, message.id, category)

    elif content_type == "news":
        n_data = parse_news_post(raw_text, default_category=category)
        if n_data:
            await save_news_to_db(n_data, channel, message.id)

    elif content_type == "mixed":
        # ابتدا تست می‌کنیم آیا سوال چهارگزینه‌ای است یا خیر
        q_data = parse_text_question(raw_text)
        if q_data:
            await save_question_to_db(q_data, channel, message.id, category)
        else:
            n_data = parse_news_post(raw_text, default_category=category)
            if n_data:
                await save_news_to_db(n_data, channel, message.id)

async def backfill_channel_history(channel_username: str, limit: int = 150) -> int:
    """
    استخراج پیام‌های قبلی و تاریخچه یک کانال تلگرام
    """
    if not telegram_client or not settings.TELEGRAM_ENABLED:
        logger.warning("تله‌تون فعال نیست یا اطلاعات احراز هویت تنظیم نشده است.")
        return 0

    count = 0
    try:
        logger.info(f"شروع استخراج تاریخچه کانال {channel_username} (حداکثر {limit} پیام)...")
        async for msg in telegram_client.iter_messages(channel_username, limit=limit):
            try:
                await process_channel_message(telegram_client, msg, channel_username)
                count += 1
                await asyncio.sleep(0.2) # جلوگیری از فلود تلگرام
            except Exception as e:
                logger.error(f"خطا در پردازش پیام {msg.id} از {channel_username}: {e}")

        async with get_db() as db:
            await db.execute("""
                INSERT INTO crawler_logs (channel_username, status, extracted_count, message)
                VALUES (?, 'success', ?, 'استخراج تاریخچه با موفقیت انجام شد')
            """, (channel_username, count))
            await db.commit()

        return count
    except FloodWaitError as e:
        logger.error(f"محدودیت زمانی تلگرام (FloodWait): {e.seconds} ثانیه صبر کنید.")
        return count
    except Exception as e:
        logger.error(f"خطا در استخراج تاریخچه {channel_username}: {e}")
        async with get_db() as db:
            await db.execute("""
                INSERT INTO crawler_logs (channel_username, status, extracted_count, message)
                VALUES (?, 'error', ?, ?)
            """, (channel_username, count, str(e)))
            await db.commit()
        return count
