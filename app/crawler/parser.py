import re
import hashlib
from typing import Optional, Dict, Any, List

# کلمات کلیدی تبلیغاتی که پیام‌های حاوی آن‌ها فورا حذف می‌شوند
AD_KEYWORDS = [
    "رزرو تبلیغ", "تبلیغات", "پکیج فروشی", "قیمت پکیج", "تخفیف ویژه",
    "کد تخفیف", "خرید پکیج", "ادمین کانال", "تبادل", "ظرفیت محدود",
    "واریز وجه", "هزینه ثبت نام", "پیج اینستاگرام", "مشاوره خصوصی"
]

def is_advertisement(text: str) -> bool:
    """تشخیص پست‌های تبلیغاتی اسپم"""
    if not text:
        return True
    text_lower = text.lower()
    for kw in AD_KEYWORDS:
        if kw in text_lower:
            return True
    return False

def clean_telegram_text(text: str) -> str:
    """
    پاکسازی متن از لینک‌ها، آیدی‌ها، واترمارک‌ها و خطوط تبلیغاتی کانال‌های تلگرام
    """
    if not text:
        return ""

    # ۱. حذف لینک‌های وب و لینک‌های t.me
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"t\.me/\S+", "", text)

    # ۲. حذف آیدی‌های تلگرامی مثل @channel_id
    text = re.sub(r"@\w+", "", text)

    # ۳. حذف ایموجی‌های تزیینی مزاحم در خطوط ابتدا و انتها
    lines = text.splitlines()
    cleaned_lines = []

    skip_line_patterns = [
        r"عضویت", r"کانال", r"لینک", r"منبع", r"کلیک کنید", r"فوروارد",
        r"join", r"channel", r"راه استخدام", r"ایران استخدام", r"نرخ نت",
        r"آدرس سایت", r"دانلود جزوه", r"مشاهده کارنامه"
    ]

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        # اگر خط حاوی الگوهای متداول فوتر کانال‌ها بود حذف شود
        if any(re.search(pat, line_clean, re.IGNORECASE) for pat in skip_line_patterns):
            # بررسی کنیم اگر خط سوال اصلی نیست
            if not any(marker in line_clean for marker in ["سوال", "تست", "گزینه", "کدام", "چیست", "پاسخ"]):
                continue

        cleaned_lines.append(line_clean)

    result = "\n".join(cleaned_lines).strip()
    return result

def normalize_persian_text(text: str) -> str:
    """یکسان‌سازی حروف و اعداد فارسی و عربی جهت مقایسه و هش"""
    if not text:
        return ""
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = text.replace("۰", "0").replace("۱", "1").replace("۲", "2").replace("۳", "3")
    text = text.replace("۴", "4").replace("۵", "5").replace("۶", "6").replace("۷", "7")
    text = text.replace("۸", "8").replace("۹", "9")
    # حذف فاصله‌های تکراری و نیم‌فاصله‌های اضافه
    text = re.sub(r"\s+", " ", text).strip()
    return text

def calculate_text_hash(text: str) -> str:
    """تولید هش متنی یکتا جهت جلوگیری از درج رکورد تکراری دقیق"""
    normalized = normalize_persian_text(text).lower()
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()

def parse_text_question(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    استخراج ساختار سوال چهارگزینه‌ای از متن ساده با انواع فرمت‌ها
    (۱- ۲- ۳- ۴- یا الف ب ج د یا ۱) ۲) ۳) ۴))
    """
    if not raw_text or is_advertisement(raw_text):
        return None

    cleaned = clean_telegram_text(raw_text)
    if len(cleaned) < 20:
        return None

    # الگوهای گزینه‌ها
    # الف) ... ب) ... ج) ... د) ...
    # یا ۱) ... ۲) ... ۳) ... ۴) ...
    # یا ۱- ... ۲- ... ۳- ... ۴- ...
    pattern = (
        r"^(?P<q>.+?)\n+"
        r"(?:1|۱|الف)[\)\-\.\:\s]+(?P<o1>.+?)\n+"
        r"(?:2|۲|ب)[\)\-\.\:\s]+(?P<o2>.+?)\n+"
        r"(?:3|۳|ج)[\)\-\.\:\s]+(?P<o3>.+?)\n+"
        r"(?:4|۴|د)[\)\-\.\:\s]+(?P<o4>[^\n]+)"
        r"(?:\n+(?P<extra>.*))?$"
    )

    match = re.search(pattern, cleaned, re.DOTALL)
    if not match:
        # الگوی جایگزین: گزینه‌ها در یک خط یا ساختار با فاصله‌های مختلف
        alt_pattern = (
            r"(?P<q>.+?)(?:\r?\n)+"
            r"[1۱الف][\)\-\.\s](?P<o1>.+?)(?:\r?\n)+"
            r"[2۲ب][\)\-\.\s](?P<o2>.+?)(?:\r?\n)+"
            r"[3۳ج][\)\-\.\s](?P<o3>.+?)(?:\r?\n)+"
            r"[4۴د][\)\-\.\s](?P<o4>.+)"
        )
        match = re.search(alt_pattern, cleaned, re.DOTALL)
        if not match:
            return None

    data = match.groupdict()
    question_text = data['q'].strip()
    # پاکسازی شماره تست از اول صورت سوال (مثل: تست ۱۲: ...)
    question_text = re.sub(r"^(?:سوال|تست|مسئله)?\s*\d+[\-\:\.\)]\s*", "", question_text)

    options = [
        data['o1'].strip(),
        data['o2'].strip(),
        data['o3'].strip(),
        data['o4'].strip()
    ]

    # استخراج پاسخ صحیح و توضیح تشریحی از بخش اضافه (extra)
    extra_text = data.get('extra', '') or ''
    correct_idx = None
    explanation = None

    ans_match = re.search(r"(?:پاسخ|جواب|گزینه صحیح|کلید)\s*[\:\=\-]?\s*(?:گزینه\s*)?([1-4۱-۴الفبجد])", extra_text + "\n" + cleaned)
    if ans_match:
        val = ans_match.group(1)
        mapping = {
            '1': 0, '۱': 0, 'الف': 0,
            '2': 1, '۲': 1, 'ب': 1,
            '3': 2, '۳': 2, 'ج': 2,
            '4': 3, '۴': 3, 'د': 3
        }
        correct_idx = mapping.get(val)

    # استخراج توضیح تشریحی
    exp_match = re.search(r"(?:توضیح|پاسخ تشریحی|نکته|علت)[\:\s]+(.+)", extra_text, re.DOTALL)
    if exp_match:
        explanation = exp_match.group(1).strip()
    elif extra_text and not ans_match:
        explanation = extra_text.strip()

    status = "published" if correct_idx is not None else "needs_review"

    return {
        "question_text": question_text,
        "options": options,
        "correct_index": correct_idx,
        "explanation": explanation,
        "status": status,
        "text_hash": calculate_text_hash(question_text)
    }

def slugify(text: str) -> str:
    """تولید اسلاگ امن و تمیز برای آدرس صفحات وب"""
    text = normalize_persian_text(text)
    # جایگزینی علائم نگارشی با خط تیره
    slug = re.sub(r"[^\w\s\-آ-ی]", "", text)
    slug = re.sub(r"[\s\_]+", "-", slug).strip("-")
    words = slug.split("-")[:8] # حداکثر ۸ کلمه
    return "-".join(words) if words else f"news-{hashlib.md5(text.encode()).hexdigest()[:8]}"

def parse_news_post(raw_text: str, default_category: str = "employment") -> Optional[Dict[str, Any]]:
    """
    استخراج و قالب‌بندی خبر استخدامی یا اقتصادی از پیام تلگرام جهت رتبه سئو
    """
    if not raw_text or is_advertisement(raw_text):
        return None

    cleaned = clean_telegram_text(raw_text)
    lines = [l.strip() for l in cleaned.splitlines() if l.strip()]
    if not lines or len(lines) < 2:
        return None

    # خط اول به عنوان تیتر خبر
    title = lines[0]
    # حذف شکلک‌ها یا عباراتی مثل 🔴 فوری: از تیتر
    title = re.sub(r"^[🔴📢🔔⚠️📌📍🔥⭐️]\s*", "", title)
    title = re.sub(r"^(?:فوری|مهم|خبر فوری|اطلاعیه)[\:\-]\s*", "", title).strip()

    if len(title) < 10:
        if len(lines) > 1:
            title = f"{title} - {lines[1]}"

    # خلاصه خبر (پاراگراف اول متن)
    summary = lines[1] if len(lines) > 1 else title
    if len(summary) > 200:
        summary = summary[:197] + "..."

    # متن کامل به صورت پاراگراف‌بندی شده
    content = "\n\n".join(lines[1:]) if len(lines) > 1 else cleaned

    slug = slugify(title)

    # تشخیص هوشمند دسته‌بندی برای آزمون مرتبط در بنر CTA
    cta_category = "employment"
    content_lower = content.lower()
    if any(k in content_lower for k in ["کامپیوتر", "it", "برنامه‌نویسی", "فناوری اطلاعات"]):
        cta_category = "computer"
    elif any(k in content_lower for k in ["icdl", "مهارت هفتگانه", "آفیس", "اکسل", "ورد"]):
        cta_category = "icdl"
    elif any(k in content_lower for k in ["قوانین", "خدمات کشوری", "حقوق اداری", "دیوان عدالت"]):
        cta_category = "laws"
    elif any(k in content_lower for k in ["معارف", "اندیشه اسلامی", "دینی", "آموزش و پرورش", "فرهنگی"]):
        cta_category = "maaref"

    return {
        "title": title,
        "slug": slug,
        "summary": summary,
        "content": content,
        "category": default_category,
        "cta_category": cta_category
    }
