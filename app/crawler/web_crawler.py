import re
import asyncio
import logging
from html import unescape
from typing import Dict, Any, List, Optional, Tuple
import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.database import get_db
from app.crawler.parser import (
    parse_text_question,
    parse_news_post,
    calculate_text_hash,
    clean_telegram_text,
    is_advertisement
)
from app.crawler.deduplicator import is_question_duplicate
from app.crawler.telegram_crawler import save_question_to_db, save_news_to_db

logger = logging.getLogger("web_crawler")
logger.setLevel(logging.INFO)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fa,en-US;q=0.7,en;q=0.3"
}

def clean_question_title(text: str) -> str:
    """حذف شماره سوالات در ابتدای متن مانند: ۶۱۷۸. یا تست ۱۲:"""
    if not text:
        return ""
    text = unescape(text).strip()
    text = re.sub(r"^(?:سوال|تست|مسئله)?\s*[\d۰-۹]+[\.\-\:\)]\s*", "", text)
    return text.strip()

async def crawl_channel_web(
    channel_username: str,
    max_pages: int = 4,
    start_before_id: Optional[int] = None,
    target_new_items: int = 25
) -> Dict[str, Any]:
    """
    استخراج تست‌ها و اخبار از پیش‌نمایش وب تلگرام (https://t.me/s/...)
    با قابلیت پیمایش عمیق به گذشته (Backward Pagination) در صورت وجود پیام‌های تکراری
    """
    ch_info = settings.TELEGRAM_CHANNELS.get(channel_username)
    if not ch_info:
        logger.warning(f"کانال {channel_username} در تنظیمات سامانه یافت نشد.")
        return {"questions": 0, "news": 0, "oldest_id": None}

    content_type = ch_info["type"]
    category = ch_info["category"]

    total_q = 0
    total_n = 0
    skipped_duplicates = 0
    before_id = start_before_id
    min_id_seen = None

    async with httpx.AsyncClient(headers=HEADERS, timeout=15.0, follow_redirects=True) as http_client:
        for page in range(max_pages):
            url = f"https://t.me/s/{channel_username}"
            if before_id:
                url += f"?before={before_id}"

            try:
                logger.info(f"در حال خزش صفحه {page+1} از کانال @{channel_username} ({url})...")
                res = await http_client.get(url)
                if res.status_code != 200:
                    logger.warning(f"دریافت کد {res.status_code} برای کانال {channel_username}")
                    break

                soup = BeautifulSoup(res.text, "html.parser")
                widgets = soup.find_all("div", class_="tgme_widget_message")
                if not widgets:
                    logger.info(f"پیامی در صفحه {page+1} از کانال {channel_username} یافت نشد.")
                    break

                current_page_msg_ids = []

                for w in widgets:
                    data_post = w.get("data-post", "")
                    if "/" not in data_post:
                        continue
                    try:
                        msg_id = int(data_post.split("/")[-1])
                        current_page_msg_ids.append(msg_id)
                        if min_id_seen is None or msg_id < min_id_seen:
                            min_id_seen = msg_id
                    except ValueError:
                        continue

                    # ۱. بررسی نظرسنجی و کوییز تستی (Poll / Quiz)
                    poll_q = w.find("div", class_="tgme_widget_message_poll_question")
                    if poll_q and content_type in ("question", "mixed"):
                        raw_q_text = poll_q.get_text(strip=True)
                        q_text = clean_question_title(raw_q_text)

                        options = []
                        max_percent = -1
                        likely_correct_idx = None

                        opt_divs = w.find_all("div", class_="tgme_widget_message_poll_option")
                        for idx, opt_div in enumerate(opt_divs):
                            opt_text_el = opt_div.find("div", class_="tgme_widget_message_poll_option_text")
                            opt_text = opt_text_el.get_text(strip=True) if opt_text_el else ""
                            options.append(opt_text)

                            percent_el = opt_div.find("div", class_="tgme_widget_message_poll_option_percent")
                            if percent_el:
                                p_text = percent_el.get_text(strip=True).replace("%", "")
                                try:
                                    p_val = int(p_text)
                                    if p_val > max_percent:
                                        max_percent = p_val
                                        likely_correct_idx = idx
                                except ValueError:
                                    pass

                        if len(options) >= 2 and len(q_text) >= 10:
                            correct_idx = likely_correct_idx if (max_percent >= 35) else None
                            status = "published" if correct_idx is not None else "needs_review"

                            q_data = {
                                "question_text": q_text,
                                "options": options,
                                "correct_index": correct_idx,
                                "explanation": f"بر اساس آمار مشارکت داوطلبان کانال @{channel_username} (گزینه با {max_percent}٪ آرا)",
                                "status": status,
                                "text_hash": calculate_text_hash(q_text)
                            }

                            saved = await save_question_to_db(q_data, channel_username, msg_id, category)
                            if saved:
                                total_q += 1
                            else:
                                skipped_duplicates += 1
                        continue

                    # ۲. بررسی پیام‌های متنی
                    text_div = w.find("div", class_="tgme_widget_message_text")
                    if text_div:
                        raw_text = text_div.get_text("\n", strip=True)
                        if is_advertisement(raw_text):
                            continue

                        if content_type in ("question", "mixed"):
                            parsed_q = parse_text_question(raw_text)
                            if parsed_q:
                                saved = await save_question_to_db(parsed_q, channel_username, msg_id, category)
                                if saved:
                                    total_q += 1
                                else:
                                    skipped_duplicates += 1
                                continue

                        if content_type in ("news", "mixed"):
                            parsed_n = parse_news_post(raw_text, default_category=category)
                            if parsed_n:
                                saved = await save_news_to_db(parsed_n, channel_username, msg_id)
                                if saved:
                                    total_n += 1
                                else:
                                    skipped_duplicates += 1

                # به پیام‌های قبلی‌تر برویم (?before=...)
                if current_page_msg_ids:
                    min_id = min(current_page_msg_ids)
                    if before_id and min_id >= before_id:
                        break # تاریخچه تمام شده
                    before_id = min_id
                else:
                    break

                # اگر به سقف سوالات جدید این نوبت رسیدیم، متوقف شو
                if (total_q + total_n) >= target_new_items:
                    break

                await asyncio.sleep(1.2)

            except Exception as e:
                logger.error(f"خطا در استخراج وب کانال {channel_username}: {e}")
                break

    # به‌روزرسانی قدیمی‌ترین شناسه پیام (oldest_msg_id) در جدول کانال‌ها
    async with get_db() as db:
        if min_id_seen:
            await db.execute("""
                UPDATE crawler_channels
                SET oldest_msg_id = CASE 
                    WHEN oldest_msg_id = 0 OR oldest_msg_id IS NULL THEN ?
                    ELSE MIN(oldest_msg_id, ?)
                END,
                last_crawled_at = CURRENT_TIMESTAMP
                WHERE channel_username = ?
            """, (min_id_seen, min_id_seen, channel_username))

        await db.execute("""
            INSERT INTO crawler_logs (channel_username, status, extracted_count, message)
            VALUES (?, 'success', ?, ?)
        """, (
            channel_username,
            total_q + total_n,
            f"استخراج انجام شد: {total_q} سوال جدید، {total_n} خبر جدید ({skipped_duplicates} تکراری رد شد)"
        ))
        await db.commit()

    logger.info(f"پایان خزش کانال @{channel_username}: {total_q} سوال جدید، {total_n} خبر، {skipped_duplicates} تکراری نادیده گرفته شد.")
    return {
        "channel": channel_username,
        "questions": total_q,
        "news": total_n,
        "duplicates_skipped": skipped_duplicates,
        "oldest_msg_id": min_id_seen
    }

async def crawl_next_channel_round_robin() -> Optional[Dict[str, Any]]:
    """
    انتخاب نوبتی (Round-Robin) یک کانال در هر نیم ساعت:
    کانالی که بیشترین زمان از آخرین استخراج آن گذشته انتخاب می‌شود.
    ابتدا پیام‌های جدید بالا و سپس پیام‌های قدیمی‌تر قبلی استخراج می‌شوند.
    """
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT channel_username, oldest_msg_id, last_msg_id
            FROM crawler_channels
            WHERE is_active = 1
            ORDER BY last_crawled_at ASC NULLS FIRST
            LIMIT 1
        """)
        row = await cursor.fetchone()
        if not row:
            logger.warning("هیچ کانال فعالی در پایگاه داده یافت نشد.")
            return None

        channel_username = row["channel_username"]
        oldest_msg_id = row["oldest_msg_id"] or 0

    logger.info(f"نوبت خزش دوره‌ای کانال @{channel_username} فرا رسید (oldest_id: {oldest_msg_id})...")

    # گام اول: استخراج پیام‌های جدید اخیر از بالای کانال (۱ صفحه)
    fresh_res = await crawl_channel_web(channel_username, max_pages=1)

    # گام دوم: اگر قدیمی‌ترین شناسه داریم، به پیام‌های قبلی‌تر رجوع کن و به عقب برو
    deep_res = {"questions": 0, "news": 0, "duplicates_skipped": 0}
    if oldest_msg_id > 0:
        deep_res = await crawl_channel_web(
            channel_username,
            max_pages=3,
            start_before_id=oldest_msg_id,
            target_new_items=20
        )

    return {
        "channel": channel_username,
        "total_new_questions": fresh_res.get("questions", 0) + deep_res.get("questions", 0),
        "total_new_news": fresh_res.get("news", 0) + deep_res.get("news", 0),
        "duplicates_skipped": fresh_res.get("duplicates_skipped", 0) + deep_res.get("duplicates_skipped", 0)
    }

async def crawl_all_channels_web(max_pages: int = 2) -> Dict[str, Any]:
    """خزش و استخراج همزمان تمام ۸ کانال تلگرام به صورت اتوماتیک"""
    results = {}
    total_questions = 0
    total_news = 0

    for ch_username in settings.TELEGRAM_CHANNELS.keys():
        try:
            res = await crawl_channel_web(ch_username, max_pages=max_pages)
            results[ch_username] = res
            total_questions += res["questions"]
            total_news += res["news"]
        except Exception as e:
            logger.error(f"خطا در پردازش کانال {ch_username}: {e}")
            results[ch_username] = {"questions": 0, "news": 0, "error": str(e)}

        await asyncio.sleep(1.0)

    return {
        "channels": results,
        "total_questions_extracted": total_questions,
        "total_news_extracted": total_news
    }
