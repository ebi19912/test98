import sqlite3
import aiosqlite
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any, List, Optional, Dict
from app.config import settings

# قفل همزمانی سراسری برای تراکنش‌های سنگین نوشتن در صورت نیاز
_db_write_lock = asyncio.Lock()

@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    تولید اتصال ناهمگام به دیتابیس SQLite با تنظیمات پیشرفته همزمانی و بهینه‌سازی عملکرد
    """
    db = await aiosqlite.connect(settings.DB_PATH)
    db.row_factory = aiosqlite.Row

    # بهینه‌سازی همزمانی و کارایی طبق مستندات معماری Test98
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA synchronous=NORMAL;")
    await db.execute("PRAGMA busy_timeout=10000;")
    await db.execute("PRAGMA foreign_keys=ON;")
    await db.execute("PRAGMA cache_size=-64000;")  # حدود ۶۴ مگابایت کش رم
    await db.execute("PRAGMA temp_store=MEMORY;")  # عملیات SORT و TEMP در رم

    try:
        yield db
    finally:
        await db.close()

async def init_db():
    """
    راه‌اندازی ساختار کامل پایگاه داده SQLite برای پلتفرم test98.ir
    """
    async with get_db() as db:
        # ۱. جدول دسته‌بندی‌ها
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                code TEXT PRIMARY KEY,
                name_fa TEXT NOT NULL,
                description TEXT,
                icon TEXT DEFAULT 'folder',
                color TEXT DEFAULT 'blue',
                is_exam INTEGER DEFAULT 1,
                is_news INTEGER DEFAULT 0
            );
        """)

        # ۲. جدول سوالات چهارگزینه‌ای
        await db.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                question_text TEXT NOT NULL,
                options_json TEXT NOT NULL, -- آرایه JSON از ۴ گزینه
                correct_index INTEGER,      -- 0 تا 3 (NULL یعنی نیازمند بررسی ادمین)
                explanation TEXT,           -- پاسخ تشریحی و نکات کلیدی
                source_channel TEXT,        -- کانال مبدا تلگرام
                source_msg_id INTEGER,      -- شناسه پیام اصلی تلگرام
                text_hash TEXT UNIQUE,      -- هش جهت جلوگیری از تکرار دقیق
                difficulty_level TEXT DEFAULT 'medium', -- easy, medium, hard
                status TEXT DEFAULT 'published',        -- published, needs_review, rejected
                report_count INTEGER DEFAULT 0,         -- گزارش خطای کاربران
                views_count INTEGER DEFAULT 0,
                correct_answers_count INTEGER DEFAULT 0,
                wrong_answers_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category) REFERENCES categories(code)
            );
        """)

        # ۳. جدول اخبار استخدامی و عمومی
        await db.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                summary TEXT,
                content TEXT NOT NULL,
                image_path TEXT,
                category TEXT NOT NULL,
                source_channel TEXT,
                source_msg_id INTEGER,
                views_count INTEGER DEFAULT 0,
                cta_category TEXT,          -- دسته آزمون مرتبط جهت نمایش بنر CTA
                is_published INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category) REFERENCES categories(code)
            );
        """)

        # ۴. جدول کاربران
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bale_chat_id INTEGER UNIQUE,
                bale_username TEXT,
                phone TEXT UNIQUE,
                full_name TEXT,
                target_exam TEXT,
                is_vip INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user', -- user, admin
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ۵. جدول نشست‌های احراز هویت و لینک جادویی بله
        await db.execute("""
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token TEXT PRIMARY KEY,
                guest_token TEXT,               -- توکن مهمان برای انتقال آزمون‌ها
                user_id INTEGER,                -- پس از تایید پر می‌شود
                otp_code TEXT,
                status TEXT DEFAULT 'pending',  -- pending, verified, expired
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # ۶. جدول آزمون‌های کاربران (سفارشی، استاندارد سراسری و تمرینی)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS exam_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guest_token TEXT,
                exam_type TEXT DEFAULT 'custom', -- custom, global, practice
                category TEXT NOT NULL,
                total_questions INTEGER NOT NULL,
                correct_count INTEGER DEFAULT 0,
                wrong_count INTEGER DEFAULT 0,
                unanswered_count INTEGER DEFAULT 0,
                raw_score REAL DEFAULT 0.0,
                t_score REAL,                    -- تراز محاسبه‌شده استاندارد
                rank INTEGER,                    -- رتبه کاربر در جامعه آماری
                has_negative_marking INTEGER DEFAULT 1,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_finished INTEGER DEFAULT 0,
                finished_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );
        """)

        # ۷. جدول واسط سوالات موجود در هر آزمون (Snapshot)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS exam_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                question_order INTEGER NOT NULL,
                FOREIGN KEY (attempt_id) REFERENCES exam_attempts(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions(id)
            );
        """)

        # ۸. جدول پاسخ‌های ریز کاربران به تک‌تک سوالات آزمون‌ها
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                user_id INTEGER,
                guest_token TEXT,
                question_id INTEGER NOT NULL,
                selected_option INTEGER,     -- 0 تا 3 یا NULL برای پاسخ نداده
                is_correct INTEGER,          -- 0 یا 1 یا NULL
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (attempt_id) REFERENCES exam_attempts(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions(id),
                UNIQUE(attempt_id, question_id)
            );
        """)

        # ۹. جدول جعبه لایتنر هوشمند (مرور زمان‌مند خطاهای داوطلب)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_leitner (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                box_level INTEGER DEFAULT 1,    -- سطح جعبه از ۱ تا ۵
                consecutive_correct INTEGER DEFAULT 0,
                next_review_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
                UNIQUE(user_id, question_id)
            );
        """)

        # ۱۰. جدول سوالات نشان‌شده (Bookmarks)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
                UNIQUE(user_id, question_id)
            );
        """)

        # ۱۱. جدول پارامترهای آماری آزمون‌های سراسری جهت محاسبه تراز
        await db.execute("""
            CREATE TABLE IF NOT EXISTS exam_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_identifier TEXT UNIQUE NOT NULL, -- مثل global_icdl_total
                total_participants INTEGER DEFAULT 0,
                mean_score REAL DEFAULT 0.0,
                std_dev REAL DEFAULT 0.0,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ۱۲. جدول وضعیت و پایش کانال‌های تلگرامی
        await db.execute("""
            CREATE TABLE IF NOT EXISTS crawler_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_username TEXT UNIQUE NOT NULL,
                content_type TEXT NOT NULL,     -- question, news, mixed
                category_code TEXT NOT NULL,
                name_fa TEXT,
                is_active INTEGER DEFAULT 1,
                last_msg_id INTEGER DEFAULT 0,
                oldest_msg_id INTEGER DEFAULT 0,
                total_extracted INTEGER DEFAULT 0,
                last_crawled_at TIMESTAMP,
                FOREIGN KEY (category_code) REFERENCES categories(code)
            );
        """)

        # ۱۳. جدول لاگ‌های خزشگر
        await db.execute("""
            CREATE TABLE IF NOT EXISTS crawler_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_username TEXT NOT NULL,
                status TEXT NOT NULL,           -- success, error, warning
                extracted_count INTEGER DEFAULT 0,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ۱۴. جدول گزارش خطاهای سوالات توسط کاربران
        await db.execute("""
            CREATE TABLE IF NOT EXISTS question_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                user_id INTEGER,
                reason TEXT NOT NULL,
                details TEXT,
                status TEXT DEFAULT 'pending', -- pending, resolved, dismissed
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (question_id) REFERENCES questions(id)
            );
        """)

        # ۱۵. ایجاد جداول جستجوی تمام‌متن FTS5
        await db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS news_fts USING fts5(
                title, content, tokenize='unicode61'
            );
        """)
        await db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS questions_fts USING fts5(
                question_text, explanation, tokenize='unicode61'
            );
        """)

        # ۱۶. استراتژی ایندکس‌گذاری پیشرفته (Covering & Partial & Specialized Indexes)
        # ایندکس‌های جدول سوالات
        await db.execute("CREATE INDEX IF NOT EXISTS idx_questions_cat_status ON questions(category, status);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_questions_hash ON questions(text_hash);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_questions_report ON questions(report_count);")

        # ایندکس‌های جدول اخبار
        await db.execute("CREATE INDEX IF NOT EXISTS idx_news_slug ON news(slug);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_news_cat ON news(category, is_published);")

        # ایندکس‌های جدول پاسخ‌ها (Covering Index)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_covering_user_score ON user_answers(user_id, attempt_id, is_correct);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_errors ON user_answers(user_id, is_correct);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_guest_answers ON user_answers(guest_token);")

        # ایندکس‌های جدول آزمون‌ها (Partial & Ranking Index)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_active_attempts ON exam_attempts(category, is_finished) WHERE is_finished = 0;")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_ranking_tscore ON exam_attempts(category, t_score DESC);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_attempts ON exam_attempts(user_id, is_finished);")

        # ثبت دسته‌بندی‌های پیش‌فرض
        categories = [
            ("icdl", "مهارت‌های هفتگانه ICDL", "مجموعه تست‌های استاندارد مهارت‌های هفتگانه کامپیوتر آزمون‌های استخدامی", "laptop", "blue", 1, 0),
            ("computer", "فناوری اطلاعات و کامپیوتر", "مفاهیم شبکه، سخت‌افزار، نرم‌افزار و مبانی فناوری اطلاعات", "server", "indigo", 1, 0),
            ("laws", "قوانین و مقررات اداری", "قانون مدیریت خدمات کشوری، قانون اساسی و مقررات استخدامی", "scale", "amber", 1, 0),
            ("maaref", "معارف و اندیشه اسلامی", "آزمون‌های جامع معارف اسلامی، اندیشه و اخلاق", "book-open", "emerald", 1, 0),
            ("employment", "اخبار استخدامی و دفترچه‌ها", "جدیدترین آگهی‌های استخدامی دستگاه‌های اجرایی، بانک‌ها و آموزش‌وپرورش", "briefcase", "rose", 0, 1),
            ("economy", "اخبار اقتصادی و بازار کار", "نرخ‌ها، تحلیل‌ها و اخبار اقتصادی موثر بر بازار کار", "chart-bar", "cyan", 0, 1)
        ]
        await db.executemany("""
            INSERT INTO categories (code, name_fa, description, icon, color, is_exam, is_news)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name_fa=excluded.name_fa,
                description=excluded.description,
                icon=excluded.icon,
                color=excluded.color
        """, categories)

        # ثبت کانال‌های پیش‌فرض تلگرام
        channels = [
            ("ICDL100", "question", "icdl", "کانال تست و نکات ICDL"),
            ("camputerraheeestekhdam", "question", "computer", "کانال فناوری اطلاعات و کامپیوتر"),
            ("gavaninraheeestekhdam", "question", "laws", "کانال قوانین و مقررات اداری"),
            ("maarefraheeeestekhdam", "question", "maaref", "کانال معارف و اندیشه اسلامی ۱"),
            ("maarefehrah", "question", "maaref", "کانال معارف و اطلاعات عمومی ۲"),
            ("Iranestekhdam_ir", "news", "employment", "ایران استخدام (اطلاعیه‌ها و دفترچه‌ها)"),
            ("raheeestekhdam2", "mixed", "employment", "راه استخدام (اخبار و نمونه سوالات)"),
            ("nerkh_net", "news", "economy", "شبکه نرخ و اخبار اقتصادی")
        ]
        await db.executemany("""
            INSERT INTO crawler_channels (channel_username, content_type, category_code, name_fa)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(channel_username) DO UPDATE SET
                content_type=excluded.content_type,
                category_code=excluded.category_code,
                name_fa=excluded.name_fa
        """, channels)

        # ثبت کاربر مدیر پیش‌فرض
        await db.execute("""
            INSERT INTO users (id, bale_chat_id, phone, full_name, role, is_vip)
            VALUES (1, 100001, '09120000000', 'مدیر ارشد سامانه', 'admin', 1)
            ON CONFLICT(id) DO NOTHING;
        """)

        await db.commit()
