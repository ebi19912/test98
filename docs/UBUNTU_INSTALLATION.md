# 🐧 راهنمای جامع نصب و راه‌اندازی پلتفرم تست ۹۸ روی اوبونتو (Ubuntu Deployment Guide)

این راهنما مراحل نصب، پیکربندی و استقرار پلتفرم **تست ۹۸** را روی سرورهای لینوکس **Ubuntu 20.04 / 22.04 / 24.04 LTS** (یا Debian 11/12) به صورت کاملاً گام‌به‌گام و عملی توضیح می‌دهد.

---

## 📋 فهرست مطالب
1. [پیش‌نیازها و مشخصات سرور](#۱-پیش‌نیازها-و-مشخصات-سرور)
2. [روش اول: نصب سریع و خودکار (با یک دستور)](#۲-روش-اول-نصب-سریع-و-خودکار-با-یک-دستور)
3. [روش دوم: نصب گام‌به‌گام دستی](#۳-روش-دوم-نصب-گام‌به‌گام-دستی)
   - [گام ۱: به‌روزرسانی سرور و نصب بسته‌های مورد نیاز](#گام-۱-به‌روزرسانی-سرور-و-نصب-بسته‌های-مورد-نیاز)
   - [گام ۲: انتقال یا کلون پروژه به سرور](#گام-۲-انتقال-یا-کلون-پروژه-به-سرور)
   - [گام ۳: ایجاد محیط مجازی و نصب کتابخانه‌های پایتون](#گام-۳-ایجاد-محیط-مجازی-و-نصب-کتابخانه‌های-پایتون)
   - [گام ۴: پیکربندی فایل تنظیمات (.env)](#گام-۴-پیکربندی-فایل-تنظیمات-env)
   - [گام ۵: تنظیم مجوزها و دسترسی‌های لینوکس](#گام-۵-تنظیم-مجوزها-و-دسترسی‌های-لینوکس)
   - [گام ۶: پیکربندی سرویس Systemd (اجرای ۲۴/۷)](#گام-۶-پیکربندی-سرویس-systemd-اجرای-۲۴۷)
   - [گام ۷: راه‌اندازی و تنظیم وب‌سرور Nginx](#گام-۷-راه‌اندازی-و-تنظیم-وب‌سرور-nginx)
   - [گام ۸: تنظیم فایروال سرور (UFW)](#گام-۸-تنظیم-فایروال-سرور-ufw)
   - [گام ۹: دریافت گواهینامه رایگان SSL با Certbot](#گام-۹-دریافت-گواهینامه-رایگان-ssl-با-certbot)
   - [گام ۱۰: فعال‌سازی وب‌هوک پیام‌رسان بله](#گام-۱۰-فعال‌سازی-وب‌هوک-پیام‌رسان-بله)
4. [دستورات کاربردی مدیریت و مانیتورینگ سرور](#۴-دستورات-کاربردی-مدیریت-و-مانیتورینگ-سرور)
5. [پشتیبان‌گیری خودکار روزانه از دیتابیس (Cron Job)](#۵-پشتیبان‌گیری-خودکار-روزانه-از-دیتابیس-cron-job)

---

## ۱. پیش‌نیازها و مشخصات سرور

* **سیستم‌عامل:** Ubuntu 22.04 LTS یا Ubuntu 24.04 LTS (پیشنهادی)
* **دسترسی:** دسترسی کاربری `root` یا کاربری با دسترسی `sudo`
* **حداقل سخت‌افزار پیشنهادی:**
  * رم (RAM): حداقل ۱ گیگابایت (۲ گیگابایت برای عملکرد ایده‌آل)
  * پردازنده (CPU): ۱ هسته (1 vCPU)
  * دیسک (Disk): ۱۰ گیگابایت SSD/NVMe
* **دامنه اینترنتی:** دامنه ثبت‌شده `test98.ir` که رکورد `A` آن به آی‌پی سرور شما متصل شده باشد.

---

## ۲. روش اول: نصب سریع و خودکار (با یک دستور)

اگر فایل‌های پروژه را روی سرور کپی کرده‌اید، می‌توانید از اسکریپت استقرار خودکار که در پوشه `deploy/` تعبیه شده استفاده کنید:

```bash
# رفتن به پوشه پروژه و اجرای اسکریپت استقرار با دسترسی روت:
cd /path/to/test98
sudo bash deploy/deploy.sh
```

این اسکریپت تمام بسته‌ها را نصب کرده، محیط مجازی را ساخته، دسترسی‌ها را تنظیم، Nginx و Systemd را فعال و سرور را بالا می‌آورد. پس از اتمام فقط [گام ۹ (SSL)](#گام-۹-دریافت-گواهینامه-رایگان-ssl-با-certbot) را اجرا کنید.

---

## ۳. روش دوم: نصب گام‌به‌گام دستی

### گام ۱: به‌روزرسانی سرور و نصب بسته‌های مورد نیاز

ابتدا از طریق SSH به سرور متصل شوید و مخازن سیستم‌عامل را به‌روزرسانی و نرم‌افزارهای مورد نیاز را نصب کنید:

```bash
sudo apt update && sudo apt upgrade -y

# نصب پایتون، pip، محیط مجازی، ابزارهای شبکه و Nginx
sudo apt install -y python3 python3-pip python3-venv git sqlite3 nginx curl ufw certbot python3-certbot-nginx
```

---

### گام ۲: انتقال یا کلون پروژه به سرور

مسیر استاندارد برای قرارگیری وب‌سایت در لینوکس پوشه `/var/www/test98` است:

```bash
# ایجاد پوشه مقصد
sudo mkdir -p /var/www/test98

# اگر از گیت استفاده می‌کنید:
sudo git clone https://github.com/your-username/test98.git /var/www/test98

# یا اگر فایل‌ها را از سیستم محلی با scp آپلود کرده‌اید، آن‌ها را به این مسیر منتقل کنید:
# cd /var/www/test98
```

---

### گام ۳: ایجاد محیط مجازی و نصب کتابخانه‌های پایتون

```bash
cd /var/www/test98

# ایجاد Virtual Environment
sudo python3 -m venv .venv

# فعال‌سازی محیط مجازی و نصب پکیج‌ها
sudo .venv/bin/pip install --upgrade pip
sudo .venv/bin/pip install -r requirements.txt
```

---

### گام ۴: پیکربندی فایل تنظیمات (.env)

فایل `.env.example` را کپی کرده و اطلاعات سرور و ربات بله را در آن بنویسید:

```bash
sudo cp .env.example .env
sudo nano .env
```

مقادیر زیر را در فایل `.env` بررسی و ذخیره کنید (`Ctrl+O` سپس `Enter` و `Ctrl+X` برای خروج):

```env
APP_NAME="تست ۹۸ | سامانه آزمون‌ساز و خبرخوان هوشمند استخدامی"
APP_ENV=production
APP_HOST=127.0.0.1
APP_PORT=8000
SECRET_KEY=یک-رشته-تصادفی-طولانی-حداقل-۳۲-کاراکتر
SITE_URL=https://test98.ir

DATABASE_PATH=test98.db

# تنظیمات پیام‌رسان بله (استخراج‌شده از BotFather@)
BALE_BOT_TOKEN=1018095732:A4OvrHoBlWixOP-4hqfzLZQqTybHFQDSJtU
BALE_BOT_USERNAME=test98_bot
BALE_ENABLED=true

# تنظیمات تلگرام (در صورت نیاز به فعال‌سازی یوزربات)
TELEGRAM_API_ID=0
TELEGRAM_API_HASH=""
TELEGRAM_ENABLED=false
```

---

### گام ۵: تنظیم مجوزها و دسترسی‌های لینوکس

سرویس‌های وب در اوبونتو تحت کاربر امن `www-data` اجرا می‌شوند. برای اینکه دیتابیس SQLite بتواند لاگ‌های WAL را بنویسد، مالکیت پوشه را تنظیم کنید:

```bash
sudo chown -R www-data:www-data /var/www/test98
sudo chmod -R 775 /var/www/test98

# در صورت وجود فایل دیتابیس، مجوز خواندن و نوشتن آن:
if [ -f /var/www/test98/test98.db ]; then
    sudo chmod 664 /var/www/test98/test98.db
fi
```

---

### گام ۶: پیکربندی سرویس Systemd (اجرای ۲۴/۷)

یک سرویس لینوکسی می‌سازیم تا اپلیکیشن FastAPI به صورت ۲۴ ساعته اجرا شود و در صورت ری‌استارت سرور یا بروز خطا، خودکار بالا بیاید:

```bash
sudo nano /etc/systemd/system/test98.service
```

محتوای زیر را قرار دهید:

```ini
[Unit]
Description=Test98 Exam Platform (FastAPI Uvicorn)
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/test98
EnvironmentFile=/var/www/test98/.env
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONIOENCODING=utf-8"
ExecStart=/var/www/test98/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2

Restart=always
RestartSec=5s

ProtectSystem=full
PrivateTmp=true
ReadWritePaths=/var/www/test98

[Install]
WantedBy=multi-user.target
```

فعال‌سازی و شروع سرویس:
```bash
sudo systemctl daemon-reload
sudo systemctl enable test98
sudo systemctl start test98

# بررسی وضعیت سرویس:
sudo systemctl status test98
```
*(باید وضعیت `active (running)` با رنگ سبز نمایش داده شود).*

---

### گام ۷: راه‌اندازی و تنظیم وب‌سرور Nginx

وب‌سرور Nginx درخواست‌های کاربران روی پورت 80 و 443 را دریافت کرده و به پورت محلی 8000 (FastAPI) فوروارد می‌کند:

```bash
sudo nano /etc/nginx/sites-available/test98.conf
```

محتوای فایل پیکربندی Nginx:

```nginx
upstream test98_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name test98.ir www.test98.ir;

    client_max_body_size 25M;

    # فشرده‌سازی خودکار برای لود پرسرعت
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript font/woff2;

    # سرو مستقیم فایل‌های استاتیک توسط Nginx
    location /static/ {
        alias /var/www/test98/app/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location / {
        proxy_pass http://test98_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
}
```

فعال‌سازی سایت در Nginx:
```bash
# ایجاد لینک به sites-enabled
sudo ln -sf /etc/nginx/sites-available/test98.conf /etc/nginx/sites-enabled/

# حذف سایت پیش‌فرض آپاچی/انجینکس
sudo rm -f /etc/nginx/sites-enabled/default

# تست صحت سینتکس کانفیگ Nginx
sudo nginx -t

# بارگذاری مجدد Nginx
sudo systemctl reload nginx
```

---

### گام ۸: تنظیم فایروال سرور (UFW)

برای امنیت سرور، فقط پورت‌های وب و SSH را باز کنید:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# مشاهده وضعیت فایروال:
sudo ufw status
```

---

### گام ۹: دریافت گواهینامه رایگان SSL با Certbot

برای تبدیل آدرس به `https://test98.ir` و فعال‌سازی قفل سبز مرورگر، دستور زیر را اجرا کنید:

```bash
sudo certbot --nginx -d test98.ir -d www.test98.ir
```
* ایمیل خود را وارد کرده و با قوانین موافقت کنید (`Y`).
* ابزار Certbot به طور خودکار گواهی را صادر، در کانفیگ Nginx تزریق و تمدید خودکار (Auto-renewal) را در زمان‌بندی سرور فعال می‌کند.

---

### گام ۱۰: فعال‌سازی وب‌هوک پیام‌رسان بله

اکنون که سرور روی دامنه با HTTPS بالا آمده است، اسکریپت راه‌اندازی بله را در محیط مجازی اجرا کنید:

```bash
cd /var/www/test98
sudo -u www-data .venv/bin/python scripts/setup_bale.py
```
* آدرس وب‌هوک شما روی `https://test98.ir/auth/bale-webhook` ثبت می‌شود.
* از این پس هر پیامی که کاربران در بله ارسال کنند یا دکمه ورود را لمس کنند، بلافاصله توسط سرور لینوکس شما پردازش و تایید می‌گردد.

---

## ۴. دستورات کاربردی مدیریت و مانیتورینگ سرور

### مشاهده لاگ‌های زنده سیستم:
```bash
# مشاهده لاگ‌های فرآیند پایتون و خزشگرها به صورت زنده
sudo journalctl -u test98 -f

# مشاهده لاگ‌های خطای وب‌سرور Nginx
sudo tail -f /var/log/nginx/error.log
```

### ری‌استارت، توقف یا بررسی وضعیت:
```bash
# ری‌استارت سرویس پس از تغییر کد یا فایل .env
sudo systemctl restart test98

# بررسی وضعیت زنده سرویس
sudo systemctl status test98

# بارگذاری مجدد Nginx
sudo systemctl reload nginx
```

---

## ۵. پشتیبان‌گیری خودکار روزانه از دیتابیس (Cron Job)

دیتابیس SQLite در حالت WAL است و می‌توان بدون توقف سرور، نسخه پشتیبان زنده از آن گرفت:

یک اسکریپت بکاپ در `/var/www/test98/backup.sh` بسازید:
```bash
sudo mkdir -p /var/backups/test98
sudo nano /var/www/test98/backup.sh
```

محتوای فایل:
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/test98"
DATE=$(date +%Y-%m-%d_%H%M)
sqlite3 /var/www/test98/test98.db ".backup '$BACKUP_DIR/test98_$DATE.db'"
# حذف بکاپ‌های قدیمی‌تر از ۳۰ روز
find "$BACKUP_DIR" -type f -name "*.db" -mtime +30 -delete
```

دادن مجوز اجرا:
```bash
sudo chmod +x /var/www/test98/backup.sh
```

افزودن به کرون‌جاب لینوکس (هر شب ساعت ۳ بامداد):
```bash
sudo crontab -e
# افزودن خط زیر:
0 3 * * * /bin/bash /var/www/test98/backup.sh >/dev/null 2>&1
```

---
🎉 **تبریک! پلتفرم تست ۹۸ با امنیت کامل، وب‌سرور Nginx، گواهینامه SSL و اتصال دائمی به پیام‌رسان بله روی سرور اوبونتو شما مستقر گردید.**
