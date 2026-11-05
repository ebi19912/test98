#!/usr/bin/env python3
"""
اسکریپت اعتبارسنجی و اتصال خودکار وب‌هوک ربات بله برای پلتفرم تست ۹۸ (test98.ir)
نحوه اجرا:
python scripts/setup_bale.py
"""

import os
import sys
from pathlib import Path
import httpx
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BALE_TOKEN = os.getenv("BALE_BOT_TOKEN", "").strip()
BALE_USERNAME = os.getenv("BALE_BOT_USERNAME", "").strip()
SITE_URL = os.getenv("SITE_URL", "https://test98.ir").strip().rstrip("/")

print("=" * 60)
print("🤖 ابزار راه‌اندازی و اتصال خودکار پیام‌رسان بله (تست ۹۸)")
print("=" * 60)

if not BALE_TOKEN or BALE_TOKEN == "your_bale_bot_token_here":
    print("⚠️ توکن بله در فایل .env تنظیم نشده است.")
    BALE_TOKEN = input("لطفاً توکن ربات بله (دریافتی از @BotFather) را وارد کنید: ").strip()

if not BALE_TOKEN:
    print("❌ خطا: توکن وارد نشد. عملیات لغو شد.")
    sys.exit(1)

API_BASE = f"https://tapi.bale.ai/bot{BALE_TOKEN}"

def check_bot():
    print(f"\n1. بررسی صحت توکن ربات در سرورهای بله...")
    try:
        resp = httpx.get(f"{API_BASE}/getMe", timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                bot_user = data.get("result", {})
                username = bot_user.get("username", "")
                name = bot_user.get("first_name", "")
                print(f"✅ ربات با موفقیت تایید شد!")
                print(f"   نام ربات: {name}")
                print(f"   نام کاربری (آیدی): @{username}")
                print(f"   شناسه بات: {bot_user.get('id')}")
                return username
        print(f"❌ خطا در تایید توکن! پاسخ سرور بله: {resp.text}")
        return None
    except Exception as e:
        print(f"❌ خطای اتصال به سرورهای بله: {e}")
        return None

def set_webhook(bot_username: str):
    webhook_url = f"{SITE_URL}/auth/bale-webhook"
    print(f"\n2. تنظیم وب‌هوک به آدرس: {webhook_url}")
    
    try:
        resp = httpx.post(
            f"{API_BASE}/setWebhook",
            json={"url": webhook_url},
            timeout=10.0
        )
        if resp.status_code == 200 and resp.json().get("ok"):
            print("✅ وب‌هوک با موفقیت روی سرور بله ثبت شد!")
        else:
            print(f"⚠️ پاسخ سرور بله به تنظیم وب‌هوک: {resp.text}")
    except Exception as e:
        print(f"❌ خطا در ثبت وب‌هوک: {e}")

    # دریافت وضعیت وب‌هوک
    try:
        info_resp = httpx.get(f"{API_BASE}/getWebhookInfo", timeout=10.0)
        print(f"ℹ️ وضعیت فعلی وب‌هوک: {info_resp.json().get('result', {})}")
    except Exception:
        pass

def update_env(bot_username: str):
    env_file = BASE_DIR / ".env"
    lines = []
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

    keys_to_update = {
        "BALE_BOT_TOKEN": BALE_TOKEN,
        "BALE_BOT_USERNAME": bot_username or BALE_USERNAME,
        "BALE_ENABLED": "true"
    }

    new_lines = []
    seen = set()
    for line in lines:
        updated = False
        for k, v in keys_to_update.items():
            if line.startswith(f"{k}="):
                new_lines.append(f"{k}={v}\n")
                seen.add(k)
                updated = True
                break
        if not updated:
            new_lines.append(line)

    for k, v in keys_to_update.items():
        if k not in seen:
            new_lines.append(f"{k}={v}\n")

    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"\n✅ مقادیر BALE_BOT_TOKEN، BALE_BOT_USERNAME و BALE_ENABLED در فایل .env به‌روزرسانی شدند.")

if __name__ == "__main__":
    bot_user = check_bot()
    if bot_user:
        set_webhook(bot_user)
        update_env(bot_user)
        print("\n" + "=" * 60)
        print("🎉 تبریک! ربات بله پلتفرم تست ۹۸ با موفقیت متصل شد.")
        print(f"لینک مستقیم ورود داوطلبان: https://ble.ir/{bot_user}")
        print("=" * 60)
