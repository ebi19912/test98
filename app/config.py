import os
from pathlib import Path
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی از .env در صورت وجود
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    APP_NAME: str = "تست ۹۸ | سامانه آزمون‌ساز و خبرخوان هوشمند استخدامی"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", 8000))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "test98-secret-key-default-change-me")
    SITE_URL: str = os.getenv("SITE_URL", "http://localhost:8000")

    # مسیر دیتابیس SQLite
    DB_PATH: str = str(BASE_DIR / os.getenv("DATABASE_PATH", "test98.db"))

    # تنظیمات تلگرام (Telethon Userbot)
    TELEGRAM_API_ID: int = int(os.getenv("TELEGRAM_API_ID", "0"))
    TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")
    TELEGRAM_SESSION_NAME: str = str(BASE_DIR / os.getenv("TELEGRAM_SESSION_NAME", "test98_userbot"))
    TELEGRAM_ENABLED: bool = os.getenv("TELEGRAM_ENABLED", "false").lower() in ("true", "1", "yes")

    # کانال‌های تحت پوشش با نگاشت ماژول و دسته
    TELEGRAM_CHANNELS = {
        "ICDL100": {
            "type": "question",
            "category": "icdl",
            "name": "مهارت‌های هفتگانه ICDL",
            "module": "questions"
        },
        "camputerraheeestekhdam": {
            "type": "question",
            "category": "computer",
            "name": "فناوری اطلاعات و کامپیوتر",
            "module": "questions"
        },
        "gavaninraheeestekhdam": {
            "type": "question",
            "category": "laws",
            "name": "قوانین و مقررات اداری",
            "module": "questions"
        },
        "maarefraheeeestekhdam": {
            "type": "question",
            "category": "maaref",
            "name": "معارف و اندیشه اسلامی",
            "module": "questions"
        },
        "maarefehrah": {
            "type": "question",
            "category": "maaref",
            "name": "معارف و اطلاعات عمومی",
            "module": "questions"
        },
        "Iranestekhdam_ir": {
            "type": "news",
            "category": "employment",
            "name": "اطلاعیه‌ها و دفترچه‌های استخدامی",
            "module": "news"
        },
        "raheeestekhdam2": {
            "type": "mixed",
            "category": "employment",
            "name": "اخبار و منابع استخدامی",
            "module": "mixed"
        },
        "nerkh_net": {
            "type": "news",
            "category": "economy",
            "name": "اخبار اقتصادی و نرخ‌ها",
            "module": "news"
        }
    }

    # تنظیمات پیام‌رسان بله
    BALE_BOT_TOKEN: str = os.getenv("BALE_BOT_TOKEN", "")
    BALE_BOT_USERNAME: str = os.getenv("BALE_BOT_USERNAME", "Test98Bot")
    BALE_API_URL: str = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}" if BALE_BOT_TOKEN else ""
    BALE_CHANNEL_ID: str = os.getenv("BALE_CHANNEL_ID", "@test98_ir")
    BALE_ENABLED: bool = os.getenv("BALE_ENABLED", "false").lower() in ("true", "1", "yes")

    # دسته‌بندی‌های رسمی سایت
    CATEGORIES = {
        "icdl": {"title": "مهارت‌های هفتگانه ICDL", "icon": "laptop", "color": "blue"},
        "computer": {"title": "فناوری اطلاعات و کامپیوتر", "icon": "server", "color": "indigo"},
        "laws": {"title": "قوانین و مقررات اداری", "icon": "scale", "color": "amber"},
        "maaref": {"title": "معارف و اندیشه اسلامی", "icon": "book-open", "color": "emerald"},
        "employment": {"title": "اخبار استخدامی و دفترچه‌ها", "icon": "briefcase", "color": "rose"},
        "economy": {"title": "اخبار اقتصادی و بازار کار", "icon": "chart-bar", "color": "cyan"}
    }

settings = Settings()
