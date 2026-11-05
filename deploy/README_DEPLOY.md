# راهنمای استقرار پلتفرم تست ۹۸ (test98.ir) روی سرور لینوکس (VPS)

این پلتفرم برای اجرای پایدار، کم‌مصرف و مقیاس‌پذیر به صورت MVP روی یک سرور لینوکسی (حتی با ۱ هسته CPU و ۱ گیگابایت رم) طراحی شده است.

---

## روش اول: استقرار با داکر و داکر کامپوز (Docker Compose) - پیشنهاد سریع

### مراحل:
۱. اتصال به سرور از طریق SSH:
```bash
ssh root@YOUR_SERVER_IP
```

۲. نصب Docker و Docker Compose (در صورت عدم نصب):
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

۳. انتقال فایل‌های پروژه به سرور:
```bash
mkdir -p /opt/test98
cd /opt/test98
# فایل‌های پروژه را کپی کنید یا مخزن گیت را کلون کنید
```

۴. ایجاد فایل تنظیمات محیطی:
```bash
cp .env.example .env
nano .env
```

۵. اجرای پروژه در پس‌زمینه:
```bash
docker compose up -d --build
```

۶. بررسی لاگ‌ها و وضعیت سرویس:
```bash
docker compose logs -f
```

---

## روش دوم: استقرار مستقیم با Systemd و Nginx (Native VPS)

### مراحل:
۱. اجرای اسکریپت خودکار نصب:
```bash
cd /path/to/test98/deploy
sudo bash deploy.sh
```

۲. دستورات مدیریتی سرویس:
- **بررسی وضعیت سرویس:**
  ```bash
  sudo systemctl status test98.service
  ```
- **مشاهده لاگ‌های زنده برنامه و خزشگر تلگرام:**
  ```bash
  sudo journalctl -u test98.service -f
  ```
- **راه‌اندازی مجدد سرویس:**
  ```bash
  sudo systemctl restart test98.service
  ```
- **تست کانفیگ Nginx:**
  ```bash
  sudo nginx -t
  sudo systemctl reload nginx
  ```

---

## فعال‌سازی دامنه و SSL رایگان (Let's Encrypt)

پس از اینکه رکورد `A` دامنه `test98.ir` و `www.test98.ir` را روی IP سرور خود ست کردید:
```bash
sudo certbot --nginx -d test98.ir -d www.test98.ir
```
سرت‌بات به صورت خودکار Nginx را برای HTTPS و ریدایرکت ترافیک امن کانفیگ می‌کند.
