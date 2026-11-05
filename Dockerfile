# Dockerfile for Test98 Platform (test98.ir)
FROM python:3.11-slim

# تنظیم متغیرهای محیطی سیستم
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PORT=8000

# نصب پکیج‌های حداقلی سیستم‌عامل برای سلامت‌سنجی
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# نصب پیش‌نیازهای پایتون با کش لایه داکر
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کل کدهای پروژه به کانتینر
COPY . .

# ایجاد دایرکتوری داده در صورت نیاز
RUN mkdir -p /app/data

EXPOSE 8000

# فرمان اجرای سرور FastAPI با Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
