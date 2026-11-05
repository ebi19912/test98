import secrets
import httpx
import logging
import datetime
from typing import Optional, Dict, Any
import aiosqlite

from app.config import settings
from app.database import get_db

logger = logging.getLogger("bale_bot")

async def create_bale_login_session(guest_token: Optional[str] = None) -> Dict[str, Any]:
    """
    ایجاد نشست ورود سریع با لینک جادویی و کد OTP برای بله
    """
    token = secrets.token_urlsafe(16)
    otp_code = str(secrets.randbelow(9000) + 1000)
    expires = (datetime.datetime.utcnow() + datetime.timedelta(minutes=10)).isoformat()

    async with get_db() as db:
        await db.execute("""
            INSERT INTO auth_sessions (token, guest_token, otp_code, expires_at)
            VALUES (?, ?, ?, ?)
        """, (token, guest_token, otp_code, expires))
        await db.commit()

    return {
        "token": token,
        "bale_url": f"https://ble.ir/{settings.BALE_BOT_USERNAME}?start=auth_{token}",
        "otp_code": otp_code,
        "expires_at": expires
    }

async def send_bale_message(chat_id: int, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> bool:
    """ارسال پیام به کاربر یا کانال در پیام‌رسان بله"""
    if not settings.BALE_API_URL or not settings.BALE_ENABLED:
        logger.debug(f"[Bale Disabled] Message to {chat_id}: {text[:50]}...")
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "chat_id": chat_id,
                "text": text
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup

            res = await client.post(f"{settings.BALE_API_URL}/sendMessage", json=payload)
            return res.status_code == 200
    except Exception as e:
        logger.error(f"خطا در ارسال پیام به بله: {e}")
        return False

async def handle_bale_webhook(update: Dict[str, Any]):
    """
    پردازش پیام‌های ورودی از وب‌هوک ربات بله
    """
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    sender = message.get("from", {})
    first_name = sender.get("first_name", "کاربر تست ۹۸")
    text = message.get("text", "").strip()
    contact = message.get("contact")

    async with get_db() as db:
        # حالت ۱: ورود با لینک جادویی دیپ‌لینک (/start auth_XXXX)
        if text.startswith("/start auth_"):
            token = text.replace("/start auth_", "").strip()

            # ۱. بازیابی یا ایجاد کاربر در جدول users
            await db.execute("""
                INSERT INTO users (bale_chat_id, full_name)
                VALUES (?, ?)
                ON CONFLICT(bale_chat_id) DO UPDATE SET full_name = excluded.full_name
            """, (chat_id, first_name))

            cursor = await db.execute("SELECT id, phone FROM users WHERE bale_chat_id = ?", (chat_id,))
            user_row = await cursor.fetchone()
            user_id = user_row[0]
            phone = user_row[1]

            # ۲. اعتبارسنجی توکن نشست
            cursor = await db.execute("""
                SELECT guest_token FROM auth_sessions
                WHERE token = ? AND status = 'pending' AND expires_at > ?
            """, (token, datetime.datetime.utcnow().isoformat()))
            session_row = await cursor.fetchone()

            if session_row:
                guest_token = session_row[0]
                await db.execute("""
                    UPDATE auth_sessions
                    SET status = 'verified', user_id = ?
                    WHERE token = ?
                """, (user_id, token))

                # انتقال سوابق آزمون‌های مهمان به حساب کاربر
                if guest_token:
                    await db.execute("""
                        UPDATE exam_attempts
                        SET user_id = ?
                        WHERE guest_token = ? AND user_id IS NULL
                    """, (user_id, guest_token))

                    await db.execute("""
                        UPDATE user_answers
                        SET user_id = ?
                        WHERE guest_token = ? AND user_id IS NULL
                    """, (user_id, guest_token))

                await db.commit()

                # پاسخ تایید به کاربر در بله
                reply_markup = {}
                welcome_msg = f"✅ سلام {first_name} عزیز!\nورود شما به سامانه **تست ۹۸** با موفقیت تایید شد. هم‌اکنون به صفحه مرورگر بازگردید تا به صورت خودکار به کارنامه یا داشبورد منتقل شوید."

                if not phone:
                    welcome_msg += "\n\n📱 جهت ثبت شماره موبایل برای اطلاع‌رسانی آزمون‌ها، دکمه زیر را لمس کنید:"
                    reply_markup = {
                        "keyboard": [[{"text": "📱 تایید و اشتراک شماره موبایل", "request_contact": True}]],
                        "resize_keyboard": True,
                        "one_time_keyboard": True
                    }

                await send_bale_message(chat_id, welcome_msg, reply_markup)

        # حالت ۲: دریافت شماره موبایل کاربر از دکمه اشتراک مخاطب
        elif contact:
            phone_number = contact.get("phone_number")
            if phone_number:
                await db.execute("""
                    UPDATE users SET phone = ? WHERE bale_chat_id = ?
                """, (phone_number, chat_id))
                await db.commit()

                confirm_msg = f"🎉 شماره موبایل شما ({phone_number}) با موفقیت تایید و در پروفایل تست ۹۸ ذخیره شد."
                await send_bale_message(chat_id, confirm_msg, {"remove_keyboard": True})

        # حالت ۳: شروع عادی یا منوی اصلی ربات (/start)
        elif text == "/start":
            welcome = (
                f"سلام {first_name} گرامی!\n"
                f"به ربات هوشمند **تست ۹۸ (test98.ir)** خوش آمدید.\n\n"
                f"🚀 با تست ۹۸ به هزاران تست واقعی آزمون‌های استخدامی کشور و آخرین اطلاعیه‌ها دسترسی دارید.\n\n"
                f"جهت استفاده از خدمات زیر انتخاب کنید:"
            )
            markup = {
                "inline_keyboard": [
                    [{"text": "🌐 ورود به وب‌سایت test98.ir", "url": settings.SITE_URL}],
                    [{"text": "📝 شرکت در آزمون آزمایشی", "url": f"{settings.SITE_URL}/exam/builder"}],
                    [{"text": "📰 مشاهده آخرین اخبار استخدامی", "url": f"{settings.SITE_URL}/news"}]
                ]
            }
            await send_bale_message(chat_id, welcome, markup)

async def check_session_status(token: str) -> Dict[str, Any]:
    """بررسی وضعیت تایید نشست احراز هویت توسط مرورگر (HTMX Polling)"""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT status, user_id FROM auth_sessions
            WHERE token = ? AND expires_at > ?
        """, (token, datetime.datetime.utcnow().isoformat()))
        row = await cursor.fetchone()
        if not row:
            return {"status": "expired"}
        return {"status": row[0], "user_id": row[1]}
