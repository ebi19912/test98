#!/bin/bash
# ==============================================================================
# اسکریپت استقرار خودکار و راه‌اندازی سرور تست ۹۸ (test98.ir)
# سیستم‌عامل پیشنهادی: Ubuntu 22.04 LTS / 24.04 LTS یا Debian 12
# ==============================================================================

set -e

# بررسی دسترسی روت
if [ "$EUID" -ne 0 ]; then
  echo "خطا: لطفاً این اسکریپت را با دسترسی sudo یا root اجرا کنید:"
  echo "sudo bash deploy.sh"
  exit 1
fi

APP_DIR="/var/www/test98"
REPO_URL="https://github.com/your-username/test98.git" # در صورت نیاز به کلون گیت

echo "=========================================="
echo "🚀 شروع آماده‌سازی و راه‌اندازی سرور تست ۹۸"
echo "=========================================="

# ۱. به‌روزرسانی مخازن لینوکس و نصب بسته‌های مورد نیاز
echo "📦 در حال نصب پکیج‌های سیستمی..."
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git sqlite3 nginx certbot python3-certbot-nginx curl ufw

# ۲. ایجاد پوشه پروژه در صورت عدم وجود
mkdir -p "$APP_DIR"

# اگر پوشه از قبل کدهای پروژه را ندارد (مثلا استقرار دستی یا کلون گیت)
if [ ! -f "$APP_DIR/main.py" ]; then
    echo "📂 کپی فایل‌های پروژه به $APP_DIR..."
    CURRENT_DIR=$(pwd)
    if [ -f "$CURRENT_DIR/main.py" ]; then
        cp -r "$CURRENT_DIR"/* "$APP_DIR"/
    fi
fi

cd "$APP_DIR"

# ۳. راه‌اندازی محیط مجازی پایتون (Virtual Environment)
echo "🐍 در حال تنظیم محیط مجازی پایتون..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# ۴. ایجاد فایل .env در صورت عدم وجود
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "⚠️ فایل .env ایجاد شد. لطفاً در صورت نیاز کلیدهای API را ویرایش کنید."
    fi
fi

# ۵. تنظیم دسترسی پوشه‌ها برای کاربر www-data
echo "🔒 در حال تنظیم دسترسی‌ها و مجوزهای فایل‌ها..."
chown -R www-data:www-data "$APP_DIR"
chmod -R 775 "$APP_DIR"
if [ -f "$APP_DIR/test98.db" ]; then
    chmod 664 "$APP_DIR/test98.db"
fi

# ۶. تنظیم سرویس Systemd
echo "⚙️ در حال پیکربندی سرویس Systemd..."
cp "$APP_DIR/deploy/test98.service" /etc/systemd/system/test98.service
systemctl daemon-reload
systemctl enable test98.service
systemctl restart test98.service

# ۷. تنظیم Nginx
echo "🌐 در حال پیکربندی وب‌سرور Nginx..."
cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/test98.conf
ln -sf /etc/nginx/sites-available/test98.conf /etc/nginx/sites-enabled/test98.conf

# غیرفعال‌سازی سایت پیش‌فرض در صورت فعال بودن
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm -f /etc/nginx/sites-enabled/default
fi

# تست و اعمال تنظیمات Nginx
nginx -t
systemctl reload nginx

# ۸. تنظیم فایروال UFW
echo "🛡️ تنظیم فایروال..."
ufw allow 'Nginx Full'
ufw allow OpenSSH
ufw --force enable

echo "=========================================="
echo "✅ راه‌اندازی اولیه پلتفرم با موفقیت انجام شد!"
echo "سرویس فعال شده و روی پورت 80 در حال پاسخگویی است."
echo ""
echo "📌 مراحل بعدی برای فعال‌سازی SSL (HTTPS):"
echo "دستور زیر را در سرور اجرا کنید تا گواهینامه رایگان SSL ثبت شود:"
echo "sudo certbot --nginx -d test98.ir -d www.test98.ir"
echo "=========================================="
