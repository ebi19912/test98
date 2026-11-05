import secrets
import httpx
import logging
import asyncio
import datetime
from typing import Optional, Dict, Any

from app.config import settings
from app.database import get_db

logger = logging.getLogger("bale_bot")

def normalize_digits(text: str) -> str:
    """تبدیل ارقام فارسی و عربی به انگلیسی"""
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    for i in range(10):
        text = text.replace(persian_digits[i], str(i)).replace(arabic_digits[i], str(i))
    return text.strip()

def get_bale_main_keyboard() -> Dict[str, Any]:
    """کیبورد منوی اصلی ربات در بله"""
    return {
        "keyboard": [
            [{"text": "🚀 شرکت در آزمون آزمایشی"}, {"text": "📰 اخبار و دفترچه‌ها"}],
            [{"text": "👤 حساب کاربری من"}, {"text": "🌐 ورود به سایت test98.ir"}]
        ],
        "resize_keyboard": True
    }

async def create_bale_login_session(guest_token: Optional[str] = None) -> Dict[str, Any]:
    """ایجاد نشست ورود سریع با لینک جادویی و کد OTP برای بله"""
    token = secrets.token_urlsafe(16)
    otp_code = str(secrets.randbelow(9000) + 1000)
    expires = (datetime.datetime.utcnow() + datetime.timedelta(minutes=15)).isoformat()

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
    """ارسال پیام به کاربر در پیام‌رسان بله"""
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
            if res.status_code != 200:
                logger.warning(f"Bale API error ({res.status_code}): {res.text}")
            return res.status_code == 200
    except Exception as e:
        logger.error(f"خطا در ارسال پیام به بله: {e}")
        return False

async def handle_bale_webhook(update: Dict[str, Any]):
    """پردازش پیام‌های ورودی از وب‌هوک یا پولینگ ربات بله"""
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    sender = message.get("from", {})
    first_name = sender.get("first_name", "کاربر تست ۹۸")
    raw_text = message.get("text", "").strip()
    contact = message.get("contact")
    norm_text = normalize_digits(raw_text)

    async with get_db() as db:
        # ۱. ذخیره یا بازیابی هویت کاربر بر اساس شناسه بله
        await db.execute("""
            INSERT INTO users (bale_chat_id, full_name)
            VALUES (?, ?)
            ON CONFLICT(bale_chat_id) DO UPDATE SET full_name = excluded.full_name
        """, (chat_id, first_name))
        await db.commit()

        cursor = await db.execute("SELECT id, phone, role FROM users WHERE bale_chat_id = ?", (chat_id,))
        user_row = await cursor.fetchone()
        user_id = user_row[0] if user_row else 1
        phone = user_row[1] if user_row else None

        # حالت ۱: دیپ‌لینک ورود سریع (/start auth_XXXX)
        if raw_text.startswith("/start auth_"):
            token = raw_text.replace("/start auth_", "").strip()
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

                if guest_token:
                    await db.execute("UPDATE exam_attempts SET user_id = ? WHERE guest_token = ? AND user_id IS NULL", (user_id, guest_token))
                    await db.execute("UPDATE user_answers SET user_id = ? WHERE guest_token = ? AND user_id IS NULL", (user_id, guest_token))

                await db.commit()

                welcome_msg = (
                    f"✅ سلام {first_name} عزیز!\n\n"
                    f"🎉 ورود شما به سامانه **تست ۹۸ (test98.ir)** با موفقیت تایید شد.\n"
                    f"صفحه مرورگر شما هم‌اکنون به صورت خودکار وارد پنل کاربری می‌شود."
                )
                await send_bale_message(chat_id, welcome_msg, get_bale_main_keyboard())
            else:
                await send_bale_message(chat_id, "⚠️ این لینک ورود منقضی شده یا قبلاً استفاده شده است. لطفاً از صفحه لاگین سایت مجدداً اقدام کنید.", get_bale_main_keyboard())

        # حالت ۲: کاربر کد عددی ۴ رقمی ورود را تایپ کرده (مانند ۹۷۹۶ یا 9796)
        elif norm_text.isdigit() and len(norm_text) in (4, 5, 6):
            otp_input = norm_text
            cursor = await db.execute("""
                SELECT token, guest_token FROM auth_sessions
                WHERE otp_code = ? AND status = 'pending' AND expires_at > ?
                ORDER BY created_at DESC LIMIT 1
            """, (otp_input, datetime.datetime.utcnow().isoformat()))
            session_row = await cursor.fetchone()

            if session_row:
                token, guest_token = session_row
                await db.execute("""
                    UPDATE auth_sessions
                    SET status = 'verified', user_id = ?
                    WHERE token = ?
                """, (user_id, token))

                if guest_token:
                    await db.execute("UPDATE exam_attempts SET user_id = ? WHERE guest_token = ? AND user_id IS NULL", (user_id, guest_token))
                    await db.execute("UPDATE user_answers SET user_id = ? WHERE guest_token = ? AND user_id IS NULL", (user_id, guest_token))

                await db.commit()

                confirm_msg = (
                    f"✅ **کد تایید {otp_input} با موفقیت پذیرفته شد!**\n\n"
                    f"سلام {first_name} گرامی، نشست شما در سایت تست ۹۸ فعال شد. لطفاً به صفحه مرورگر خود نگاه کنید تا ورود خودکار به پنل را مشاهده فرمایید."
                )
                await send_bale_message(chat_id, confirm_msg, get_bale_main_keyboard())
            else:
                err_msg = (
                    f"❌ کد ارسالی ({otp_input}) یافت نشد یا زمان اعتبار ۱۰ دقیقه‌ای آن پایان یافته است.\n\n"
                    f"لطفاً صفحه ورود سایت را رفرش کنید و کد جدید را ارسال فرمایید، یا در سایت دکمه «ورود مستقیم با اپلیکیشن بله» را لمس کنید."
                )
                await send_bale_message(chat_id, err_msg, get_bale_main_keyboard())

        # حالت ۳: ارسال شماره تماس (Contact)
        elif contact:
            phone_number = contact.get("phone_number")
            if phone_number:
                await db.execute("UPDATE users SET phone = ? WHERE bale_chat_id = ?", (phone_number, chat_id))
                await db.commit()
                confirm_msg = f"🎉 شماره موبایل شما ({phone_number}) با موفقیت تایید و ثبت شد."
                await send_bale_message(chat_id, confirm_msg, get_bale_main_keyboard())

        # حالت ۴: دکمه «🚀 شرکت در آزمون آزمایشی»
        elif "آزمون" in raw_text:
            exam_text = (
                f"📝 **شبیه‌ساز هوشمند آزمون‌های استخدامی کشور**\n\n"
                f"شما می‌توانید با نمونه سوالات ادوار گذشته دروس زیر آزمون دهید:\n"
                f"🔹 مهارت‌های هفتگانه ICDL\n"
                f"🔹 قوانین و مقررات اداری\n"
                f"🔹 معارف و اندیشه اسلامی\n"
                f"🔹 فناوری اطلاعات و کامپیوتر\n\n"
                f"جهت ساخت آزمون آنلاین با محاسبه نمره منفی و کارنامه روی لینک زیر بزنید:\n"
                f"{settings.SITE_URL}/exam/builder"
            )
            markup = {
                "inline_keyboard": [
                    [{"text": "⚡ شروع آزمون سریع ۱۰ سوالی", "url": f"{settings.SITE_URL}/exam/builder"}],
                    [{"text": "🌐 ورود به پنل آزمون‌ها", "url": f"{settings.SITE_URL}/user/exams"}]
                ]
            }
            await send_bale_message(chat_id, exam_text, markup)

        # حالت ۵: دکمه «📰 اخبار و دفترچه‌ها»
        elif "اخبار" in raw_text or "دفترچه" in raw_text:
            cursor = await db.execute("SELECT title, slug FROM news ORDER BY created_at DESC LIMIT 3")
            latest = await cursor.fetchall()
            news_text = "📢 **جدیدترین اطلاعیه‌ها و دفترچه‌های استخدامی:**\n\n"
            for n in latest:
                news_text += f"▪️ {n[0]}\n🔗 {settings.SITE_URL}/news/{n[1]}\n\n"
            news_text += f"📂 آرشیو کامل اخبار: {settings.SITE_URL}/news"
            await send_bale_message(chat_id, news_text, get_bale_main_keyboard())

        # حالت ۶: دکمه «👤 حساب کاربری من»
        elif "حساب" in raw_text or "پروفایل" in raw_text:
            cursor = await db.execute("SELECT COUNT(*) FROM exam_attempts WHERE user_id = ?", (user_id,))
            exam_count = (await cursor.fetchone())[0]
            profile_text = (
                f"👤 **مشخصات حساب داوطلب در تست ۹۸**\n\n"
                f"▫️ نام: {first_name}\n"
                f"▫️ شماره تماس: {phone or 'ثبت نشده'}\n"
                f"▫️ تعداد آزمون‌های شرکت کرده: {exam_count}\n"
                f"▫️ وضعیت دسترسی: داوطلب فعال\n\n"
                f"🔗 ورود به داشبورد داوطلب: {settings.SITE_URL}/user/dashboard"
            )
            await send_bale_message(chat_id, profile_text, get_bale_main_keyboard())

        # حالت ۷: دکمه «🌐 ورود به سایت» یا منوی /start
        elif raw_text == "/start" or "سایت" in raw_text:
            welcome = (
                f"سلام {first_name} عزیز! 🎓\n"
                f"به ربات هوشمند **تست ۹۸ (test98.ir)** خوش آمدید.\n\n"
                f"این بازو متصل به بانک نمونه سوالات ادوار گذشته و سیستم ورود بدون رمز سایت است.\n\n"
                f"💡 **راهنمای ورود به سایت:**\n"
                f"۱. وارد صفحه ورود سایت شوید.\n"
                f"۲. کد ۴ رقمی که روی صفحه نمایش داده شده را همینجا ارسال کنید!\n\n"
                f"همچنین از دکمه‌های زیر می‌توانید برای دسترسی سریع استفاده کنید:"
            )
            await send_bale_message(chat_id, welcome, get_bale_main_keyboard())

        # حالت پیش‌فرض: سایر پیام‌ها
        else:
            help_text = (
                f"سلام {first_name} عزیز! ✋\n\n"
                f"اگر قصد **ورود به سایت تست ۹۸** را دارید، کافیست کد ۴ رقمی نمایش‌داده‌شده روی صفحه کامپیوتر یا مرورگر را همینجا تایپ و ارسال کنید.\n\n"
                f"همچنین می‌توانید از منوی زیر برای آزمون‌ها و اخبار استفاده نمایید:"
            )
            await send_bale_message(chat_id, help_text, get_bale_main_keyboard())

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

async def bale_polling_worker():
    """
    ورکر پس‌زمینه برای دریافت زنده پیام‌های بله (Long Polling)
    بدون نیاز به وبهوک یا دامنه عمومی، پیام‌ها در لحظه پردازش و پاسخ داده می‌شوند.
    """
    if not settings.BALE_ENABLED or not settings.BALE_BOT_TOKEN:
        logger.info("سرویس بله غیرفعال است؛ ورکر پولینگ اجرا نمی‌شود.")
        return

    logger.info("راه‌اندازی سرویس دریافت پیام‌های زنده بله (Long Polling)...")

    # حذف هرگونه وبهوک ثبت‌شده تا getUpdates فعال شود
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.get(f"{settings.BALE_API_URL}/deleteWebhook")
            logger.info("وبهوک بله با موفقیت پاکسازی شد و حالت Polling فعال گردید.")
    except Exception as e:
        logger.warning(f"عدم موفقیت در پاکسازی وبهوک بله: {e}")

    last_offset = 0

    while True:
        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                url = f"{settings.BALE_API_URL}/getUpdates"
                params = {"timeout": 20}
                if last_offset > 0:
                    params["offset"] = last_offset + 1

                res = await client.get(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("ok"):
                        updates = data.get("result", [])
                        for update in updates:
                            update_id = update.get("update_id", 0)
                            if update_id > last_offset:
                                last_offset = update_id

                            try:
                                await handle_bale_webhook(update)
                            except Exception as ex:
                                logger.error(f"خطا در پردازش پیام بله (update_id {update_id}): {ex}")
                else:
                    await asyncio.sleep(2)
        except asyncio.CancelledError:
            logger.info("ورکر پولینگ بله متوقف شد.")
            break
        except Exception as e:
            logger.warning(f"خطا در پولینگ پیام‌های بله: {e}")
            await asyncio.sleep(3)
