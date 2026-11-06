# 🚀 راهنمای جامع نصب، راه‌اندازی و استقرار پلتفرم تست ۹۸ (test98.ir)

این سند راهنمای صفر تا صد نصب، پیکربندی و اجرای پلتفرم **تست ۹۸** روی محیط‌های **توسعه محلی (Localhost)** و **سرورهای عملیاتی (Linux Production)** است.

---

## 📋 فهرست مطالب
1. [پیش‌نیازهای سیستمی](#۱-پیش‌نیازهای-سیستمی)
2. [دریافت سورس کد و آماده‌سازی محیط پایتون](#۲-دریافت-سورس-کد-و-آماده‌سازی-محیط-پایتون)
3. [پیکربندی متغیرهای محیطی (.env)](#۳-پیکربندی-متغیرهای-محیطی-env)
4. [تنظیم و اتصال پیام‌رسان بله (Bale Bot)](#۴-تنظیم-و-اتصال-پیام‌رسان-بله-bale-bot)
5. [تنظیمات اختیاری تلگرام (Telethon Userbot)](#۵-تنظیمات-اختیاری-تلگرام-telethon-userbot)
6. [اجرا در محیط توسعه محلی (Local Development)](#۶-اجرا-در-محیط-توسعه-محلی-local-development)
7. [استقرار کامل روی سرور لینوکس (Production Deployment)](#۷-استقرار-کامل-روی-سرور-لینوکس-production-deployment)
   - [تنظیم سرویس‌دهنده systemd](#الف-تنظیم-سرویس‌دهنده-systemd)
   - [پیکربندی وب‌سرور Nginx](#ب-پیکربندی-وب‌سرور-nginx)
   - [فعال‌سازی گواهی رایگان SSL (Let's Encrypt)](#ج-فعال‌سازی-گواهی-رایگان-ssl-lets-encrypt)
8. [پشتیبان‌گیری و نگهداری پایگاه داده](#۸-پشتیبان‌گیری-و-نگهداری-پایگاه-داده)
9. [عیب‌یابی و پرسش‌های متداول (FAQ)](#۹-عیب‌یابی-و-پرسش‌های-متداول-faq)

---

## ۱. پیش‌نیازهای سیستمی

قبل از شروع، مطمئن شوید نرم‌افزارهای زیر روی سیستم یا سرور شما نصب باشند:

* **پایتون:** نسخه `3.10` یا بالاتر (`Python 3.10+`)
* **مدیریت بسته:** `pip`
* **ابزار کنترل نسخه:** `Git`
* **سیستم‌عامل‌های پشتیبانی‌شده:**
  * Windows 10/11 / Windows Server
  * Ubuntu 20.04 / 22.04 / 24.04 LTS
  * Debian 11 / 12
  * macOS (Apple Silicon / Intel)
* **حداقل سخت‌افزار مورد نیاز:**
  * پردازنده: ۱ هسته (1 vCPU)
  * حافظه رم: ۱ گیگابایت (1 GB RAM)
  * دیسک: حداقل ۳ گیگابایت فضای خالی

---

## ۲. دریافت سورس کد و آماده‌سازی محیط پایتون

### گام ۱: کلون کردن مخزن پروژه
```bash
git clone https://github.com/your-username/test98.git
cd test98
```

### گام ۲: ایجاد محیط مجازی (Virtual Environment)
ایجاد یک Virtualenv مجزا برای عدم تداخل با پکیج‌های عمومی سیستم الزامی است:

**در ویندوز (PowerShell یا CMD):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(اگر با خطای Execution Policy در ویندوز مواجه شدید، دستور `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` را یک‌بار اجرا کنید).*

**در لینوکس / مک:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### گام ۳: نصب وابستگی‌های پروژه
تمامی بسته‌های مورد نیاز با دستور زیر نصب می‌شوند:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## ۳. پیکربندی متغیرهای محیطی (.env)

پلتفرم تست ۹۸ کلیه تنظیمات حساس و عملیاتی خود را از فایل `.env` دریافت می‌کند.

یک کپی از فایل نمونه ایجاد کنید:
```bash
# در لینوکس / مک
cp .env.example .env

# در ویندوز
copy .env.example .env
```

محتوای فایل `.env` را به شکل زیر ویرایش کنید:

```env
# ========================================================
# پیکربندی عمومی نرم‌افزار
# ========================================================
APP_NAME="تست ۹۸ | سامانه آزمون‌ساز و خبرخوان هوشمند استخدامی"
APP_ENV=production                  # development برای محیط تست، production برای سرور
APP_HOST=0.0.0.0
APP_PORT=8000
SECRET_KEY=generate-a-strong-random-key-here-32-chars
SITE_URL=https://test98.ir           # آدرس کامل سایت شما با پروتکل https

# ========================================================
# تنظیمات پایگاه داده
# ========================================================
DATABASE_PATH=test98.db

# ========================================================
# تنظیمات پیام‌رسان بله (ورود بدون رمز و بازوی هوشمند)
# ========================================================
BALE_BOT_TOKEN=1018095732:A4OvrHoBlWixOP-4hqfzLZQqTybHFQDSJtU
BALE_BOT_USERNAME=test98_bot
BALE_ENABLED=true

# ========================================================
# تنظیمات تلگرام (اختیاری برای کوییزهای قفل و لاگین کاربری)
# ========================================================
TELEGRAM_API_ID=0
TELEGRAM_API_HASH=""
TELEGRAM_SESSION_NAME=test98_userbot
TELEGRAM_ENABLED=false
```

> ⚠️ **نکته امنیتی:** فایل `.env` در فایل `.gitignore` قرار داده شده است و هرگز نباید در مخزن گیت عمومی کامیت شود.

---

## ۴. تنظیم و اتصال پیام‌رسان بله (Bale Bot)

پلتفرم تست ۹۸ از پیام‌رسان ملی **بله** برای احراز هویت تک‌کلیکی بدون رمز و کدهای یک‌بار مصرف استفاده می‌کند.

### مراحل فعال‌سازی:
1. در اپلیکیشن بله، وارد ربات رسمی **`BotFather@`** شوید.
2. دستور `/newbot` را بفرستید و یک نام و آیدی انگلیسی که به `bot` ختم می‌شود ثبت کنید (مانند `test98_bot`).
3. توکن ربات را کپی کنید.
4. اسکریپت آماده پروژه را برای اعتبارسنجی و ثبت خودکار اجرا کنید:

```bash
# در ویندوز
.venv\Scripts\python.exe scripts/setup_bale.py

# در لینوکس
.venv/bin/python scripts/setup_bale.py
```

5. این اسکریپت صحت توکن را از سرورهای بله استعلام گرفته و فایل `.env` را خودکار تنظیم می‌کند.

> 💡 **نحوه عملکرد در سرور و لوکال:**
> * **در محیط لوکال:** سرویس داخلی **Long Polling** به طور خودکار پیام‌ها را دریافت و بدون نیاز به وب‌هوک پردازش می‌کند.
> * **در محیط سرور واقعی (با SSL فعال):** اسکریپت آدرس وب‌هوک شما را روی `https://test98.ir/auth/bale-webhook` ثبت می‌نماید.

---

## ۵. تنظیمات اختیاری تلگرام (Telethon Userbot)

پلتفرم تست ۹۸ به طور پیش‌فرض دارای یک موتور **وب‌اسکرپینگ عمومی بدون فیلترشکن** است که از تمام ۸ کانال استخدامی سوالات و اخبار را استخراج می‌کند و نیازی به ورود با شماره تلگرام ندارد.

اگر مایل هستید کلاینت تلگرام (Telethon) را نیز فعال کنید:
1. به سایت [my.telegram.org](https://my.telegram.org) مراجعه و وارد شوید.
2. در بخش **API development tools**، یک اپلیکیشن جدید بسازید و مقادیر `api_id` و `api_hash` را بردارید.
3. در فایل `.env` مقادیر را قرار دهید:
   ```env
   TELEGRAM_API_ID=12345678
   TELEGRAM_API_HASH=your_api_hash_here
   TELEGRAM_ENABLED=true
   ```
4. بار اول اجرای برنامه، در خط فرمان شماره تماس و کد تایید ارسالی تلگرام را وارد کنید تا فایل سشن ساخته شود.

---

## ۶. اجرا در محیط توسعه محلی (Local Development)

برای تست و مشاهده سایت روی کامپیوتر شخصی:

```bash
# در ویندوز
$env:PYTHONIOENCODING="utf-8"
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# در لینوکس / مک
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

پس از بالا آمدن سرور:
* **صفحه اصلی پلتفرم:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **صفحه ورود و آزمون بله:** [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)
* **پنل مدیریت (Admin):** [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)
* **مستندات تعاملی API (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

> دیتابیس SQLite (`test98.db`) در بار نخست اجرا، به صورت خودکار جداول را ایجاد کرده و با نمونه سوالات استاندارد ادوار گذشته اولیه پر (Seed) خواهد شد.

---

## ۷. استقرار کامل روی سرور لینوکس (Production Deployment)

این بخش مراحل استقرار حرفه‌ای پلتفرم را روی توزیع‌های اوبونتو و دبیان توضیح می‌دهد.

### الف) تنظیم سرویس‌دهنده systemd

یک فایل سرویس در مسیر `/etc/systemd/system/test98.service` بسازید:
```bash
sudo nano /etc/systemd/system/test98.service
```

محتوای زیر را درون آن قرار دهید (مسیرها و نام کاربری را با سرور خود تطبیق دهید):
```ini
[Unit]
Description=Test98 Intelligent Exam Platform (FastAPI)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/test98
Environment="PATH=/var/www/test98/.venv/bin"
EnvironmentFile=/var/www/test98/.env
ExecStart=/var/www/test98/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2 --loop uvloop --http httptools
Restart=always
RestartSec=5s

# محدودیت‌های دسترسی امنیتی
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=/var/www/test98

[Install]
WantedBy=multi-user.target
```

فعال‌سازی و شروع سرویس:
```bash
sudo systemctl daemon-reload
sudo systemctl enable test98
sudo systemctl start test98
sudo systemctl status test98
```

---

### ب) پیکربندی وب‌سرور Nginx

وب‌سرور Nginx به عنوان Reverse Proxy روبروی Uvicorn عمل کرده و ترافیک کاربر، فایل‌های استاتیک و فشرده‌سازی Gzip را مدیریت می‌کند.

یک پیکربندی جدید برای سایت بسازید:
```bash
sudo nano /etc/nginx/sites-available/test98
```

محتوای فایل پیکربندی Nginx:
```nginx
server {
    server_name test98.ir www.test98.ir;

    # لاگ‌های اختصاصی
    access_log /var/log/nginx/test98_access.log;
    error_log /var/log/nginx/test98_error.log;

    client_max_body_size 20M;

    # سرو مستقیم فایل‌های استاتیک توسط Nginx با هدر کش
    location /static/ {
        alias /var/www/test98/app/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # فوروارد بقیه درخواست‌ها به FastAPI Uvicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
    }
}
```

فعال‌سازی سایت و تست صحت تنظیمات:
```bash
sudo ln -s /etc/nginx/sites-available/test98 /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

### ج) فعال‌سازی گواهی رایگان SSL (Let's Encrypt)

برای فعال‌سازی HTTPS روی دامنه `test98.ir`، از ابزار `Certbot` استفاده کنید:

```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d test98.ir -d www.test98.ir
```

گواهینامه به طور خودکار فعال و تمدید خودکار (Auto-Renewal) نیز روی سرور تنظیم می‌گردد.

---

## ۸. پشتیبان‌گیری و نگهداری پایگاه داده

پایگاه داده در حالت **WAL (Write-Ahead Logging)** اجرا می‌شود که سرعت فوق‌العاده بالایی دارد. برای بکاپ‌گیری امن بدون نیاز به خاموش کردن سرور:

```bash
# ایجاد نسخه پشتیبان زنده از دیتابیس
sqlite3 /var/www/test98/test98.db ".backup '/var/backups/test98_backup_$(date +%F).db'"
```

می‌توانید این دستور را در crontab قرار دهید تا هر شب ساعت ۳ بامداد یک بکاپ کامل ذخیره شود:
```bash
crontab -e
# افزودن خط زیر:
0 3 * * * sqlite3 /var/www/test98/test98.db ".backup '/var/backups/test98_backup_\$(date +\%F).db'"
```

---

## ۹. عیب‌یابی و پرسش‌های متداول (FAQ)

### ۱. پیام‌های ارسالی کاربر در بله جواب داده نمی‌شود؟
* بررسی کنید `BALE_ENABLED=true` در `.env` باشد.
* مطمئن شوید سرویس تست ۹۸ در حال اجرا است (`systemctl status test98`).
* لاگ برنامه را بررسی کنید:
  ```bash
  sudo journalctl -u test98 -f
  ```

### ۲. آیا برای خزش تلگرام نیاز به نصب ابزار دور زدن تحریم روی سرور است؟
* **خیر.** لایه پیش‌فرض خزشگر از وب عمومی (`https://t.me/s/...`) استفاده می‌کند و بر روی اکثر سرورهای خارج و داخل به راحتی در دسترس است.

### ۳. چگونه کاربری را به سطح ادمین ارتقا دهیم؟
می‌توانید مستقیماً در دیتابیس نقش کاربر را به `admin` تغییر دهید:
```bash
sqlite3 test98.db "UPDATE users SET role = 'admin' WHERE id = 1;"
```

---
🎯 **پلتفرم تست ۹۸ هم‌اکنون با تمام امکانات آماده بهره‌برداری است.**
برای مشاهده مستندات تفصیلی سایر بخش‌ها به پوشه [docs/](file:///d:/test98/docs) مراجعه نمایید.
