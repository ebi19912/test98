# 🎓 پلتفرم آزمون‌ساز هوشمند و خبرخوان استخدامی تست ۹۸ (test98.ir)

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-009688?logo=fastapi&logoColor=white)
![SQLite WAL](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57?logo=sqlite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-v3-38B2AC?logo=tailwind-css&logoColor=white)
![HTMX](https://img.shields.io/badge/HTMX-1.9.10-3366CC)
![Bale Messenger](https://img.shields.io/badge/Bale%20Bot-Integrated-00A859)
![License](https://img.shields.io/badge/License-MIT-green)

**مرجع تخصصی نمونه سوالات سال‌های گذشته آزمون‌های استخدامی کشور، شبیه‌ساز آزمون‌های آنلاین با تراز کشوری، جعبه مرور لایتنر و خبرخوان هوشمند متصل به پیام‌رسان بله**

[مشاهده دمو و وب‌سایت](https://test98.ir) • [راهنمای تفصیلی اوبونتو](docs/UBUNTU_INSTALLATION.md) • [فهرست مستندات فنی](docs/README.md)

</div>

---

## 📋 فهرست مطالب
1. [معرفی و نمای کلی پلتفرم](#-معرفی-و-نمای-کلی-پلتفرم)
2. [راهنمای جامع نصب و راه‌اندازی (Installation Guide)](#-راهنمای-جامع-نصب-و-راه‌اندازی-installation-guide)
   - [پیش‌نیازهای سیستمی](#پیش‌نیازهای-سیستمی)
   - [روش اول: اجرای محلی (Windows / macOS / Linux Dev)](#روش-اول-اجرای-محلی-windows--macos--linux-dev)
   - [روش دوم: استقرار کامل روی سرور ابونتو (Ubuntu 20.04 / 22.04 / 24.04 LTS)](#روش-دوم-استقرار-کامل-روی-سرور-ابونتو-ubuntu-2004--2204--2404-lts)
   - [پیکربندی متغیرهای محیطی (.env)](#پیکربندی-متغیرهای-محیطی-env)
   - [راه‌اندازی و اتصال پیام‌رسان بله (Bale Bot Setup)](#راه‌اندازی-و-اتصال-پیام‌رسان-بله-bale-bot-setup)
3. [ویژگی‌ها و ماژول‌های سامانه](#-ویژگی‌ها-و-ماژول‌های-سامانه)
   - [موتور آزمون‌ساز تطبیقی و فرمول تراز کشوری](#۱-موتور-آزمون‌ساز-تطبیقی-و-فرمول-تراز-کشوری)
   - [جعبه لایتنر هوشمند ۵ مرحله‌ای](#۲-جعبه-لایتنر-هوشمند-۵-مرحله‌ای)
   - [پایپ‌لاین استخراج و ضدعفونی خودکار محتوا](#۳-پایپ‌لاین-استخراج-و-ضدعفونی-خودکار-محتوا)
   - [خبرخوان استخدامی و قیف تبدیل سئو (SEO Funnel)](#۴-خبرخوان-استخدامی-و-قیف-تبدیل-سئو-seo-funnel)
   - [احراز هویت بدون اصطکاک و همگام‌سازی پروفایل بله](#۵-احراز-هویت-بدون-اصطکاک-و-همگام‌سازی-پروفایل-بله)
   - [پنل مدیریت کل و ویرایش نامحدود سوالات](#۶-پنل-مدیریت-کل-و-ویرایش-نامحدود-سوالات)
4. [ساختار فایل‌ها و پوشه‌بندی مخزن](#-ساختار-فایل‌ها-و-پوشه‌بندی-مخزن)
5. [فهرست مستندات فنی و تخصصی](#-فهرست-مستندات-فنی-و-تخصصی)
6. [دستورات کاربردی مانیتورینگ و پشتیبان‌گیری](#-دستورات-کاربردی-مانیتورینگ-و-پشتیبان‌گیری)

---

## 🌟 معرفی و نمای کلی پلتفرم

پلتفرم **تست ۹۸** (`test98.ir`) با تلفیق یک **خزشگر هوشمند تلگرام**، **موتور شبیه‌ساز آزمون**، **جعبه لایتنر ۵ مرحله‌ای** و **خبرخوان متصل به سئو**، چرخه کاملی برای داوطلبان آزمون‌های استخدامی کشور (دستگاه‌های اجرایی، آموزش و پرورش، وزارت بهداشت و بانک‌ها) ایجاد می‌کند:

```
[ جستجوی خبر در گوگل ] ➔ [ صفحه اطلاعیه سئو ] ➔ [ بنر دعوت به آزمون ] ➔ [ آزمون شبیه‌ساز آنلاین ]
                                                                                   │
[ تثبیت در حافظه بلندمدت ]  [ جعبه لایتنر ۵ مرحله‌ای ]  [ کارنامه تحلیلی با تراز ] ─────┘
```

> 🔒 **محرمانگی منابع:** تمامی سوالات در بخش‌های عمومی سایت، بدون اشاره به هیچ کانال یا ابزار خزش، صرفاً با عنوان رسمی **«نمونه سوالات آزمون‌های استخدامی سال‌های گذشته کشور (سنجش و جهاد دانشگاهی)»** به کاربران معرفی می‌شوند.

---

## 🚀 راهنمای جامع نصب و راه‌اندازی (Installation Guide)

### پیش‌نیازهای سیستمی
* **پایتون:** نسخه `Python 3.10` یا بالاتر
* **ابزار کنترل نسخه:** `Git`
* **مدیریت بسته:** `pip`
* **سیستم‌عامل:** ویندوز ۱۰/۱۱، سرور ابونتو (20.04/22.04/24.04 LTS)، دبیان یا مک
* **حداقل مشخصات سخت‌افزاری:** ۱ هسته پردازنده، ۱ گیگابایت رم، ۲ گیگابایت دیسک

---

### روش اول: اجرای محلی (Windows / macOS / Linux Dev)

برای راه‌اندازی و مشاهده سایت روی کامپیوتر شخصی:

#### ۱. دریافت کد پروژه:
```bash
git clone https://github.com/ebi19912/test98.git
cd test98
```

#### ۲. ایجاد و فعال‌سازی محیط مجازی:
```bash
# در ویندوز (PowerShell):
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# در لینوکس / مک:
python3 -m venv .venv
source .venv/bin/activate
```

#### ۳. نصب وابستگی‌های پایتون:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### ۴. آماده‌سازی فایل تنظیمات `.env`:
```bash
# در ویندوز:
copy .env.example .env

# در لینوکس:
cp .env.example .env
```

#### ۵. اجرای سرور توسعه:
```bash
# در ویندوز:
$env:PYTHONIOENCODING="utf-8"
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# در لینوکس / مک:
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

#### ۶. آدرس‌های دسترسی در مرورگر:
* 🌐 **صفحه اصلی سایت:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* 📱 **صفحه ورود و آزمون بله:** [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)
* 👑 **پنل مدیریت کل:** [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)
* 📚 **مستندات تعاملی API (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### روش دوم: استقرار کامل روی سرور ابونتو (Ubuntu 20.04 / 22.04 / 24.04 LTS)

#### ⚡ حالت سریع (با اسکریپت خودکار یک‌کلیکی):
```bash
# ۱. کلون پروژه در مسیر استاندارد لینوکس:
sudo git clone https://github.com/ebi19912/test98.git /var/www/test98
cd /var/www/test98

# ۲. اجرای اسکریپت استقرار کامل:
sudo bash deploy/deploy.sh
```

---

#### 🛠️ حالت گام‌به‌گام دستی روی ابونتو:

##### گام ۱: به‌روزرسانی سیستم و نصب بسته‌ها
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git sqlite3 nginx curl ufw certbot python3-certbot-nginx
```

##### گام ۲: انتقال کد پروژه و ساخت Virtualenv
```bash
sudo mkdir -p /var/www/test98
sudo git clone https://github.com/ebi19912/test98.git /var/www/test98
cd /var/www/test98

sudo python3 -m venv .venv
sudo .venv/bin/pip install --upgrade pip
sudo .venv/bin/pip install -r requirements.txt
```

##### گام ۳: تنظیم فایل `.env` و مجوزهای فایل‌ها
```bash
sudo cp .env.example .env
sudo nano .env  # تنظیم مقادیر توکن بله و دامنه test98.ir

# تنظیم مالکیت امن برای کاربر وب‌سرور:
sudo chown -R www-data:www-data /var/www/test98
sudo chmod -R 775 /var/www/test98
sudo chmod 664 /var/www/test98/test98.db
```

##### گام ۴: پیکربندی سرویس دائمی Systemd
فایل سرویس را در `/etc/systemd/system/test98.service` بسازید:
```ini
[Unit]
Description=Test98 Platform (FastAPI Uvicorn)
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
راه‌اندازی سرویس:
```bash
sudo systemctl daemon-reload
sudo systemctl enable test98
sudo systemctl start test98
sudo systemctl status test98
```

##### گام ۵: پیکربندی وب‌سرور Nginx Reverse Proxy
فایل `/etc/nginx/sites-available/test98.conf` را بسازید:
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
    gzip on;
    gzip_types text/plain text/css text/xml application/json application/javascript font/woff2;

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
        proxy_read_timeout 120s;
    }
}
```
اعمال و راه‌اندازی Nginx:
```bash
sudo ln -sf /etc/nginx/sites-available/test98.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

##### گام ۶: فایروال و فعال‌سازی رایگان SSL با Certbot
```bash
# تنظیم فایروال:
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# دریافت و نصب خودکار گواهینامه SSL:
sudo certbot --nginx -d test98.ir -d www.test98.ir
```

---

### پیکربندی متغیرهای محیطی (.env)

فایل `.env` تنظیمات اصلی برنامه را در خود نگهداری می‌کند:

```env
APP_NAME="تست ۹۸ | سامانه آزمون‌ساز و خبرخوان هوشمند استخدامی"
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
SECRET_KEY=یک-رشته-تصادفی-طولانی-حداقل-۳۲-کاراکتر
SITE_URL=https://test98.ir

# دیتابیس
DATABASE_PATH=test98.db

# پیام‌رسان بله
BALE_BOT_TOKEN=1018095732:A4OvrHoBlWixOP-4hqfzLZQqTybHFQDSJtU
BALE_BOT_USERNAME=test98_bot
BALE_ENABLED=true

# تلگرام (اختیاری)
TELEGRAM_API_ID=0
TELEGRAM_API_HASH=""
TELEGRAM_ENABLED=false
```

---

### راه‌اندازی و اتصال پیام‌رسان بله (Bale Bot Setup)

1. در اپلیکیشن بله، وارد ربات **`BotFather@`** شوید و با دستور `/newbot` ربات خود را بسازید (مانند `test98_bot`).
2. توکن دریافتی را بردارید و اسکریپت خودکار زیر را اجرا کنید:
   ```bash
   python scripts/setup_bale.py
   ```
3. اسکریپت اتصال را تست کرده و فایل `.env` را به صورت خودکار به‌روزرسانی می‌کند.
4. **نحوه عملکرد:** در لوکال، سرویس داخلی **Long Polling** پیام‌ها را می‌خواند؛ در سرور پروداکشن، بله پیام‌ها را مستقیم به آدرس `https://test98.ir/auth/bale-webhook` ارسال می‌نماید.

---

## 💎 ویژگی‌ها و ماژول‌های سامانه

### ۱. موتور آزمون‌ساز تطبیقی و فرمول تراز کشوری
* **سه حالت آزمون:** سفارشی (انتخاب تعداد سوال و زمان)، آزمون جامع استاندارد سراسری و حالت مطالعه بدون زمان (Practice Mode با نمایش آنی پاسخ تشریحی).
* **فرمول نمره منفی یک‌سوم:**  
  $$\text{Score (\%)} = \frac{3C - W}{3 \times \text{Total}} \times 100$$
* **محاسبه تراز استاندارد کشوری (T-Score):**  
  $$T = 500 + 100 \times \left( \frac{\text{Raw} - \mu}{\sigma} \right)$$
* **کارنامه تحلیلی:** رتبه داوطلب در جامعه آماری، درصد تفکیکی دروس، نمودار نقاط قوت و ضعف و امکان **ثبت گزارش خطای سوال**.

### ۲. جعبه لایتنر هوشمند ۵ مرحله‌ای
* انتقال خودکار هر سوال غلط از آزمون‌ها به **خانه شماره ۱**.
* الگوریتم مرور فاصله‌دار علمی: خانه ۱ (۱ روز)، خانه ۲ (۲ روز)، خانه ۳ (۴ روز)، خانه ۴ (۸ روز) و خانه ۵ (۱۶ روز تا تثبیت دائم).
* در صورت پاسخ غلط در هر مرحله، سوال بلافاصله به خانه ۱ سقوط می‌کند.

### ۳. پایپ‌لاین استخراج و ضدعفونی خودکار محتوا
* **نگاشت ۸ کانال مرجع تلگرامی:** ICDL، فناوری اطلاعات، قوانین اداری، معارف اسلامی، ایران استخدام، نرخ نت و...
* **ورکر نوبتی ۳۰ دقیقه‌ای (Round-Robin):** سرکشی نوبتی مداوم همراه با صفحه‌بندی به عقب (Backward Pagination) برای استخراج آرشیوهای قدیمی.
* **فیلتر ضدتبلیغات و واترمارک:** پاکسازی کامل پست‌های پکیج و تخفیف و حذف آیدی‌های تلگرامی.
* **ضدتکرار دو لایه:** هش متنی `SHA-256` صورت سوال + مقایسه فازی متنی `RapidFuzz` با آستانه شباهت ۹۰٪.

### ۴. خبرخوان استخدامی و قیف تبدیل سئو (SEO Funnel)
* انتشار اطلاعیه‌ها و دفترچه‌های استخدامی با ساختار استاندارد سئو گوگل.
* نشانه‌گذاری ساختاریافته `Schema.org NewsArticle (JSON-LD)` و متاتگ‌های OpenGraph.
* سایت‌مپ داینامیک `/sitemap.xml` و فایل `/robots.txt`.
* **باکس فراخوان اقدام هوشمند (CTA):** در انتهای هر خبر، داوطلب بلافاصله به شرکت در آزمون شبیه‌ساز مرتبط با همان ارگان دعوت می‌شود.

### ۵. احراز هویت بدون اصطکاک و همگام‌سازی پروفایل بله
* **روش اول (تک‌کلیکی دیپ‌لینک):** لمس دکمه «ورود با بله» ➔ لمس «شروع» در ربات بله ➔ ورود خودکار به سایت در عرض ۱ ثانیه بدون تایپ حتی ۱ رقم!
* **روش دوم (کد ۴ رقمی دوطرفه):** امکان ارسال کد سایت به ربات یا دریافت کد از ربات و وارد کردن در سایت.
* **همگام‌سازی کامل هویت:** نام، آیدی کاربری، شناسه چت و شماره تلفن همراه (با دکمه یک‌کلیکی اشتراک مخاطب) از بله استخراج و در سایت نمایش داده می‌شود.

### ۶. پنل مدیریت کل و ویرایش نامحدود سوالات
* دسترسی به آدرس `/admin` (با دمو یا دسترسی سطح `admin`).
* **ویرایش کامل سوال:** تغییر صورت سوال، تک‌تک ۴ گزینه، تغییر گزینه صحیح، تغییر پاسخ تشریحی و سرفصل.
* کارتابل بازبینی و گزارش خطاهای داوطلبان (`/admin/moderation`).
* مرکز پایش خزشگرها و مانیتورینگ زنده کانال‌ها (`/admin/crawlers`).

---

## 📁 ساختار فایل‌ها و پوشه‌بندی مخزن

```
d:\test98\
├── main.py                     # نقطه ورود وب‌سرور FastAPI و چرخه حیات سرور
├── requirements.txt            # لیست پکیج‌های پایتون
├── test98.db                   # پایگاه داده SQLite در حالت WAL (۱۹۰ سوال و ۸۰ خبر)
├── INSTALLATION.md             # راهنمای جامع نصب و استقرار
├── README.md                   # مستندات اصلی مخزن در گیت‌هاب
├── .env.example                # نمونه متغیرهای محیطی
├── .gitignore                  # قوانین امنیتی عدم کامیت فایل‌های حساس
│
├── docs/                       # مجموعه مستندات تخصصی تفکیک‌شده
│   ├── README.md               # فهرست جامع مستندات
│   ├── UBUNTU_INSTALLATION.md  # راهنمای استقرار روی سرور ابونتو
│   ├── 02_ARCHITECTURE.md      # معماری و جریان داده‌ها
│   ├── 03_DATABASE.md          # ساختار ۱۲ جدول پایگاه داده
│   ├── 04_CRAWLER_PIPELINE.md  # پایپ‌لاین استخراج و ضدعفونی
│   ├── 05_EXAM_ENGINE.md       # موتور آزمون‌ساز و تراز کشوری
│   ├── 06_LEITNER_BOX.md       # جعبه لایتنر ۵ مرحله‌ای
│   ├── 07_BALE_MESSENGER.md    # اتصال به بله و ورود بدون رمز
│   ├── 08_NEWS_AND_SEO.md      # خبرخوان و قیف تبدیل سئو
│   ├── 09_ADMIN_PANEL.md       # پنل مدیریت و ویرایش سوالات
│   └── 10_USER_PANEL.md        # میز کار داوطلب و پروفایل
│
├── deploy/                     # اسکریپت‌ها و فایل‌های سرور لینوکس
│   ├── deploy.sh               # اسکریپت خودکار نصب کل سرور
│   ├── nginx.conf              # کانفیگ Nginx Reverse Proxy
│   └── test98.service          # سرویس سیستمی Systemd
│
├── scripts/
│   └── setup_bale.py           # ابزار خودکار اعتبارسنجی و ثبت وب‌هوک بله
│
└── app/
    ├── config.py               # تنظیمات و نگاشت کانال‌ها
    ├── database.py             # اتصال دیتابیس SQLite WAL
    ├── templates_config.py     # تنظیمات Jinja2 و تاریخ شمسی
    ├── exam_calculator.py      # فرمول‌های نمره منفی و تراز کشوری
    ├── leitner.py              # منطق ۵ خانه‌ای لایتنر
    ├── bale_bot.py             # سرویس دریافت پیام و ورود با بله
    ├── auth_helper.py          # مدیریت کوکی‌های کاربر و مهمان
    ├── crawler/                # ماژول‌های استخراج، وب‌اسکرپینگ و رفع تکرار
    ├── routers/                # مسیرهای سایت (آزمون، خبر، ورود، ادمین، کاربر)
    ├── templates/              # قالب‌های HTML راست‌چین با Tailwind و HTMX
    └── static/                 # فایل‌های استاتیک
```

---

## 📚 فهرست مستندات فنی و تخصصی

برای مطالعه عمیق جزئیات هر ماژول، مستندات اختصاصی آن را در پوشه [docs/](docs/README.md) بخوانید:

* 🐧 [راهنمای جامع استقرار در اوبونتو (docs/UBUNTU_INSTALLATION.md)](docs/UBUNTU_INSTALLATION.md)
* 🏛️ [معماری سیستم و جریان داده‌ها (docs/02_ARCHITECTURE.md)](docs/02_ARCHITECTURE.md)
* 🗄️ [پایگاه داده و دیاگرام داده‌ها (docs/03_DATABASE.md)](docs/03_DATABASE.md)
* 🕷️ [پایپ‌لاین استخراج و پالایش داده‌ها (docs/04_CRAWLER_PIPELINE.md)](docs/04_CRAWLER_PIPELINE.md)
* 🎓 [موتور آزمون‌ساز و کارنامه تحلیلی (docs/05_EXAM_ENGINE.md)](docs/05_EXAM_ENGINE.md)
* 📦 [جعبه لایتنر هوشمند ۵ مرحله‌ای (docs/06_LEITNER_BOX.md)](docs/06_LEITNER_BOX.md)
* 📱 [پیام‌رسان بله و سیستم ورود بدون رمز (docs/07_BALE_MESSENGER.md)](docs/07_BALE_MESSENGER.md)
* 📰 [خبرخوان استخدامی و سئو گوگل (docs/08_NEWS_AND_SEO.md)](docs/08_NEWS_AND_SEO.md)
* 👑 [پنل مدیریت کل و ویرایش سوالات (docs/09_ADMIN_PANEL.md)](docs/09_ADMIN_PANEL.md)
* 👤 [میز کار و پروفایل کاربری داوطلب (docs/10_USER_PANEL.md)](docs/10_USER_PANEL.md)

---

## 🛡️ دستورات کاربردی مانیتورینگ و پشتیبان‌گیری

```bash
# مشاهده وضعیت زنده سرویس در سرور لینوکس:
sudo systemctl status test98

# مشاهده لاگ‌های زنده خزشگرها و برنامه:
sudo journalctl -u test98 -f

# ری‌استارت سرویس پس از تغییرات:
sudo systemctl restart test98

# پشتیبان‌گیری زنده و بدون توقف از پایگاه داده SQLite WAL:
sqlite3 /var/www/test98/test98.db ".backup '/var/backups/test98_$(date +%F).db'"
```

---

<div align="center">

ساخته شده با ❤️ برای داوطلبان آزمون‌های استخدامی کشور  
**پلتفرم تست ۹۸ (test98.ir)**

</div>
