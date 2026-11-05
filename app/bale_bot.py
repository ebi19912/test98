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
    if not text:
        return ""
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    for i in range(10):
        text = text.replace(persian_digits[i], str(i)).replace(arabic_digits[i], str(i))
    return text.strip()

def get_bale_main_keyboard(has_phone: bool = True) -> Dict[str, Any]:
    """کیبورد منوی اصلی ربات در بله با دکمه‌های بزرگ و کاربردی"""
    buttons = [
        [{"text": "🔑 دریافت کد ورود به سایت"}, {"text": "🚀 شرکت در آزمون آزمایشی"}]
    ]
    if not has_phone:
        buttons.append([{"text": "📱 تایید و اشتراک شماره موبایل", "request_contact": True}])
    buttons.append([{"text": "👤 مشخصات حساب من"}, {"text": "📰 اخبار و دفترچه‌ها"}])
    buttons.append([{"text": "🌐 ورود به سایت test98.ir"}])

    return {
        "keyboard": buttons,
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
    first_name = sender.get("first_name", "").strip()
    last_name = sender.get("last_name", "").strip()
    full_name = f"{first_name} {last_name}".strip() if (first_name or last_name) else "داوطلب آزمون"
    bale_username = sender.get("username", "").strip()
    raw_text = message.get("text", "").strip()
    contact = message.get("contact")
    norm_text = normalize_digits(raw_text)

    async with get_db() as db:
        # ۱. ذخیره یا به‌روزرسانی هویت کاربر در دیتابیس (نام، آیدی بله، Chat ID)
        await db.execute("""
            INSERT INTO users (bale_chat_id, bale_username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(bale_chat_id) DO UPDATE SET
                full_name = CASE WHEN excluded.full_name != '' THEN excluded.full_name ELSE users.full_name END,
                bale_username = CASE WHEN excluded.bale_username != '' THEN excluded.bale_username ELSE users.bale_username END
        """, (chat_id, bale_username, full_name))
        await db.commit()

        cursor = await db.execute("SELECT id, phone, full_name, bale_username FROM users WHERE bale_chat_id = ?", (chat_id,))
        user_row = await cursor.fetchone()
        user_id = user_row[0] if user_row else 1
        phone = user_row[1] if user_row else None
        user_name = user_row[2] or full_name
        has_phone = bool(phone)

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
                    f"✅ **سلام {user_name} عزیز!**\n\n"
                    f"🎉 ورود شما به پلتفرم **تست ۹۸ (test98.ir)** با موفقیت تایید شد.\n\n"
                    f"▫️ نام شما: {user_name}\n"
                    f"▫️ شناسه بله: {chat_id}\n"
                    f"▫️ آیدی: @{bale_username or '-'}\n\n"
                    f"صفحه مرورگر شما هم‌اکنون به صورت خودکار باز شده و وارد پنل کاربری می‌شوید."
                )
                await send_bale_message(chat_id, welcome_msg, get_bale_main_keyboard(has_phone))
            else:
                await send_bale_message(chat_id, "⚠️ این لینک ورود منقضی شده یا قبلاً استفاده شده است. لطفاً از صفحه لاگین سایت مجدداً اقدام کنید.", get_bale_main_keyboard(has_phone))

        # حالت ۲: درخواست کد ورود یک‌بار مصرف از ربات برای وارد کردن در سایت
        elif "دریافت کد" in raw_text or raw_text == "/code" or "کد ورود" in raw_text:
            generated_otp = str(secrets.randbelow(9000) + 1000)
            token = secrets.token_urlsafe(16)
            expires = (datetime.datetime.utcnow() + datetime.timedelta(minutes=15)).isoformat()

            await db.execute("""
                INSERT INTO auth_sessions (token, user_id, otp_code, status, expires_at)
                VALUES (?, ?, ?, 'pending', ?)
            """, (token, user_id, generated_otp, expires))
            await db.commit()

            code_msg = (
                f"🔑 **کد ورود یک‌بار مصرف شما به سایت:**\n\n"
                f"🔢 **{generated_otp}**\n\n"
                f"⏱️ این کد تا ۱۵ دقیقه معتبر است.\n"
                f"وارد صفحه ورود سایت (test98.ir/login) شوید، این کد را در کادر «کد دریافتی از ربات» وارد کرده و دکمه ورود را بزنید."
            )
            await send_bale_message(chat_id, code_msg, get_bale_main_keyboard(has_phone))

        # حالت ۳: کاربر کدی که در سایت نمایش داده شده را برای ربات ارسال کرده است
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
                    f"سلام {user_name} گرامی، مشخصات و نام شما از پیام‌رسان بله استخراج و ثبت شد:\n"
                    f"▫️ نام در سایت: {user_name}\n"
                    f"▫️ شناسه بله: {chat_id}\n\n"
                    f"لطفاً به صفحه مرورگر خود نگاه کنید؛ ورود خودکار به میز کار داوطلب انجام شد."
                )
                await send_bale_message(chat_id, confirm_msg, get_bale_main_keyboard(has_phone))
            else:
                err_msg = (
                    f"❌ کد ارسالی ({otp_input}) یافت نشد یا زمان اعتبار آن به پایان رسیده است.\n\n"
                    f"لطفاً صفحه ورود سایت را بررسی کنید یا دکمه «🔑 دریافت کد ورود به سایت» را در همین منو لمس کنید."
                )
                await send_bale_message(chat_id, err_msg, get_bale_main_keyboard(has_phone))

        # حالت ۴: ارسال شماره تماس توسط کاربر (Contact Share)
        elif contact:
            phone_number = contact.get("phone_number")
            c_first = contact.get("first_name", "").strip()
            c_last = contact.get("last_name", "").strip()
            c_name = f"{c_first} {c_last}".strip() if (c_first or c_last) else None

            if phone_number:
                await db.execute("""
                    UPDATE users 
                    SET phone = ?,
                        full_name = COALESCE(?, full_name)
                    WHERE bale_chat_id = ?
                """, (phone_number, c_name, chat_id))
                await db.commit()

                confirm_msg = (
                    f"🎉 **شماره همراه شما با موفقیت ثبت شد!**\n\n"
                    f"📱 شماره تایید شده: `{phone_number}`\n"
                    f"این شماره در پروفایل کاربری شما در سایت تست ۹۸ قرار گرفت و برای اطلاع‌رسانی نتایج آزمون استفاده می‌شود."
                )
                await send_bale_message(chat_id, confirm_msg, get_bale_main_keyboard(has_phone=True))

        # حالت ۵: مشاهده مشخصات و پروفایل کاربر
        elif "مشخصات" in raw_text or "پروفایل" in raw_text or "حساب" in raw_text:
            cursor = await db.execute("SELECT COUNT(*) FROM exam_attempts WHERE user_id = ?", (user_id,))
            exam_count = (await cursor.fetchone())[0]

            profile_text = (
                f"👤 **مشخصات کاربری شما در تست ۹۸ (استخراج‌شده از بله):**\n\n"
                f"▫️ **نام داوطلب:** {user_name}\n"
                f"▫️ **شناسه کاربری بله (Chat ID):** `{chat_id}`\n"
                f"▫️ **نام کاربری بله:** @{bale_username or 'ثبت نشده'}\n"
                f"▫️ **شماره همراه:** {phone or 'ثبت نشده (دکمه اشتراک شماره را بزنید)'}\n"
                f"▫️ **تعداد آزمون‌های انجام‌شده:** {exam_count} آزمون\n"
                f"▫️ **وضعیت:** داوطلب فعال و تایید هویت شده ✅\n\n"
                f"🔗 ورود به داشبورد و کارنامه‌ها: {settings.SITE_URL}/user/dashboard"
            )
            await send_bale_message(chat_id, profile_text, get_bale_main_keyboard(has_phone))

        # حالت ۶: دکمه «🚀 شرکت در آزمون آزمایشی»
        elif "آزمون" in raw_text:
            exam_text = (
                f"📝 **شبیه‌ساز هوشمند آزمون‌های استخدامی کشور**\n\n"
                f"بانک سوالات سال‌های گذشته آماده برگزاری آزمون آزمایشی است:\n"
                f"🔹 مهارت‌های هفتگانه ICDL\n"
                f"🔹 قوانین و مقررات اداری و استخدامی\n"
                f"🔹 معارف و اندیشه اسلامی\n"
                f"🔹 فناوری اطلاعات و کامپیوتر\n\n"
                f"همین الان با محاسبه نمره منفی و کارنامه تراز در آزمون شرکت کنید:\n"
                f"{settings.SITE_URL}/exam/builder"
            )
            markup = {
                "inline_keyboard": [
                    [{"text": "⚡ شروع آزمون سریع ۱۰ سوالی", "url": f"{settings.SITE_URL}/exam/builder"}],
                    [{"text": "📊 مشاهده کارنامه‌ها و نتایج", "url": f"{settings.SITE_URL}/user/history"}]
                ]
            }
            await send_bale_message(chat_id, exam_text, markup)

        # حالت ۷: دکمه «📰 اخبار و دفترچه‌ها»
        elif "اخبار" in raw_text or "دفترچه" in raw_text:
            cursor = await db.execute("SELECT title, slug FROM news ORDER BY created_at DESC LIMIT 3")
            latest = await cursor.fetchall()
            news_text = "📢 **جدیدترین اطلاعیه‌ها و دفترچه‌های استخدامی کشور:**\n\n"
            for n in latest:
                news_text += f"▪️ {n[0]}\n🔗 {settings.SITE_URL}/news/{n[1]}\n\n"
            news_text += f"📂 مشاهده تمام اطلاعیه‌ها: {settings.SITE_URL}/news"
            await send_bale_message(chat_id, news_text, get_bale_main_keyboard(has_phone))

        # حالت ۸: منوی /start یا «ورود به سایت»
        elif raw_text == "/start" or "سایت" in raw_text:
            welcome = (
                f"سلام {user_name} گرامی! 🎓\n"
                f"به بازوی هوشمند **تست ۹۸ (test98.ir)** خوش آمدید.\n\n"
                f"اطلاعات شما از پیام‌رسان بله استخراج و آماده همگام‌سازی با سایت است:\n"
                f"▫️ نام: **{user_name}**\n"
                f"▫️ آیدی بله: **@{bale_username or '-'}**\n\n"
                f"💡 **برای ورود به سایت یکی از راه‌های زیر را انتخاب کنید:**\n"
                f"۱️⃣ دکمه **«🔑 دریافت کد ورود به سایت»** را بزنید و کد داده‌شده را در سایت تایپ کنید.\n"
                f"۲️⃣ یا در صفحه لاگین سایت روی **«ورود با اپلیکیشن بله»** بزنید تا بدون تایپ وارد شوید!\n"
                f"۳️⃣ برای ثبت شماره همراه در سایت، دکمه **«📱 تایید و اشتراک شماره موبایل»** را لمس نمایید."
            )
            await send_bale_message(chat_id, welcome, get_bale_main_keyboard(has_phone))

        # حالت پیش‌فرض: سایر پیام‌ها
        else:
            help_text = (
                f"سلام {user_name} عزیز! ✋\n\n"
                f"برای ورود به سایت تست ۹۸ می‌توانید:\n"
                f"▫️ دکمه **«🔑 دریافت کد ورود به سایت»** را لمس کنید تا کد اختصاصی برایتان صادر شود.\n"
                f"▫️ یا اگر در صفحه سایت کدی می‌بینید، آن را همینجا بفرستید تا ورود شما تایید شود.\n\n"
                f"همچنین از منوی زیر می‌توانید به آزمون‌ها و اخبار دسترسی داشته باشید:"
            )
            await send_bale_message(chat_id, help_text, get_bale_main_keyboard(has_phone))

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
