import asyncio
import logging
from typing import Dict, Any, List
from app.config import settings
from app.database import get_db
from app.crawler.web_crawler import crawl_channel_web, crawl_all_channels_web, crawl_next_channel_round_robin
from app.crawler.telegram_crawler import backfill_channel_history, telegram_client

logger = logging.getLogger("crawler_manager")

async def get_crawler_status() -> List[Dict[str, Any]]:
    """دریافت وضعیت اتصال و آخرین آمار استخراج کانال‌ها"""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT 
                c.id, c.channel_username, c.content_type, c.category_code,
                c.name_fa, c.is_active, c.last_msg_id, c.total_extracted,
                c.last_crawled_at,
                cat.name_fa as category_name
            FROM crawler_channels c
            LEFT JOIN categories cat ON c.category_code = cat.code
            ORDER BY c.total_extracted DESC
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def sync_channel(channel_username: str, limit: int = 50) -> Dict[str, int]:
    """
    همگام‌سازی و استخراج کانال:
    اگر تله‌تون فعال باشد با تله‌تون، در غیر این صورت به صورت خودکار با وب‌اسکرپر عمومی تلگرام
    """
    if telegram_client and settings.TELEGRAM_ENABLED:
        count = await backfill_channel_history(channel_username, limit=limit)
        return {"questions": count, "news": 0}
    else:
        pages = max(1, limit // 20)
        return await crawl_channel_web(channel_username, max_pages=pages)

async def trigger_all_channels_sync(limit: int = 50):
    """اجرای همگام‌سازی و استخراج برای تمامی کانال‌های فعال در پس‌زمینه"""
    if telegram_client and settings.TELEGRAM_ENABLED:
        channels = await get_crawler_status()
        for ch in channels:
            if ch["is_active"]:
                try:
                    await backfill_channel_history(ch["channel_username"], limit=limit)
                except Exception as e:
                    logger.error(f"خطا در سینک کانال {ch['channel_username']}: {e}")
                await asyncio.sleep(2)
    else:
        await crawl_all_channels_web(max_pages=2)

async def periodic_crawler_worker(interval_seconds: int = 1800):
    """
    ورکر زمان‌بندی‌شده پس‌زمینه: هر ۳۰ دقیقه دقیقاً به یکی از کانال‌ها به صورت نوبتی (Round-Robin) سر می‌زند
    و تست‌ها و اخبار جدید را به همراه آرشیو پیام‌های قبلی‌تر استخراج می‌کند.
    """
    logger.info("سرویس استخراج نوبتی (Round-Robin) هر نیم ساعت کانال‌ها فعال شد.")
    while True:
        try:
            logger.info("شروع نوبت استخراج کانال بعدی...")
            res = await crawl_next_channel_round_robin()
            if res:
                logger.info(f"پایان نوبت خزش کانال @{res['channel']}: {res['total_new_questions']} سوال جدید، {res['total_new_news']} خبر جدید ({res['duplicates_skipped']} تکراری رد شد)")
        except Exception as e:
            logger.error(f"خطا در ورکر استخراج دوره‌ای: {e}")
        await asyncio.sleep(interval_seconds)

async def toggle_channel_status(channel_id: int, is_active: bool):
    """فعال یا غیرفعال کردن یک کانال"""
    async with get_db() as db:
        await db.execute(
            "UPDATE crawler_channels SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, channel_id)
        )
        await db.commit()
