import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.database import init_db
from app.seed_data import seed_initial_data
from app.crawler.telegram_crawler import telegram_client
from app.crawler.crawler_manager import periodic_crawler_worker

# وارد کردن روت‌های برنامه
from app.routers import home, exam, news, auth, user_panel, admin, seo

# تنظیم لاگرها
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("test98_main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    مدیریت چرخه حیات سرور FastAPI:
    ۱. راه‌اندازی دیتابیس SQLite در حالت بهینه WAL
    ۲. تزریق داده‌های نمونه اولیه در صورت خالی بودن دیتابیس
    ۳. اتصال کلاینت Userbot تلگرام در صورت فعال بودن
    """
    logger.info("در حال آماده‌سازی دیتابیس و سرویس‌های تست ۹۸...")
    await init_db()
    await seed_initial_data()

    # اتصال به تلگرام در صورت فعال بودن
    if telegram_client and settings.TELEGRAM_ENABLED:
        try:
            logger.info("در حال اتصال به Userbot تلگرام برای شنود زنده ۸ کانال...")
            await telegram_client.start()
            logger.info("اتصال Telethon برقرار شد.")
        except Exception as e:
            logger.error(f"خطا در اتصال به تلگرام: {e}")

    # راه‌اندازی ورکر پس‌زمینه استخراج دوره‌ای از کانال‌ها
    crawler_task = asyncio.create_task(periodic_crawler_worker(interval_seconds=1800))

    yield

    # لغو ورکر پس‌زمینه هنگام خاموش شدن
    crawler_task.cancel()

    # قطع ارتباط ایمن تلگرام در زمان خاموش شدن سرور
    if telegram_client and telegram_client.is_connected():
        logger.info("در حال قطع ارتباط ایمن تلگرام...")
        await telegram_client.disconnect()

app = FastAPI(
    title=settings.APP_NAME,
    description="پلتفرم آزمون‌ساز هوشمند و خبرخوان استخدامی کشور",
    version="1.0.0",
    lifespan=lifespan
)

# اتصال پوشه فایل‌های استاتیک
static_dir = Path(__file__).resolve().parent / "app" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ثبت روت‌ها
app.include_router(home.router)
app.include_router(exam.router)
app.include_router(news.router)
app.include_router(auth.router)
app.include_router(user_panel.router)
app.include_router(admin.router)
app.include_router(seo.router)

@app.get("/login", response_class=RedirectResponse)
async def login_shortcut():
    return RedirectResponse(url="/auth/login", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
