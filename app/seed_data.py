import json
import hashlib
from app.database import get_db
from app.crawler.parser import calculate_text_hash, slugify

SAMPLE_QUESTIONS = [
    # --- سوالات ICDL ---
    {
        "category": "icdl",
        "question_text": "کلید میانبر برای قفل کردن سیستم در سیستم عامل ویندوز چیست؟",
        "options": ["Windows + L", "Windows + D", "Ctrl + Shift + Esc", "Alt + F4"],
        "correct_index": 0,
        "explanation": "کلید ترکیبی Windows Logo + L بلافاصله حساب کاربری جاری را در ویندوز قفل (Lock) می‌کند.",
        "difficulty_level": "easy",
        "source_channel": "ICDL100"
    },
    {
        "category": "icdl",
        "question_text": "در نرم‌افزار اکسل (Excel)، کدام تابع برای شمارش سلول‌های حاوی عدد به کار می‌رود؟",
        "options": ["COUNTA", "COUNT", "COUNTIF", "SUM"],
        "correct_index": 1,
        "explanation": "تابع COUNT فقط سلول‌های حاوی داده‌های عددی را شمارش می‌کند؛ در حالی که COUNTA همه سلول‌های پر (عددی یا متنی) را می‌شمارد.",
        "difficulty_level": "medium",
        "source_channel": "ICDL100"
    },
    {
        "category": "icdl",
        "question_text": "پسوند پیش‌فرض قالب‌های ذخیره‌شده (Template) در نسخه ۲۰۱۶ به بعد نرم‌افزار Word کدام است؟",
        "options": [".docx", ".docm", ".dotx", ".dotm"],
        "correct_index": 2,
        "explanation": "پسوند فایلهای الگو یا قالب آماده در نرم افزار ورد .dotx می‌باشد و x نشانگر ساختار بر پایه XML است.",
        "difficulty_level": "medium",
        "source_channel": "ICDL100"
    },
    {
        "category": "icdl",
        "question_text": "در نرم‌افزار پاورپوینت، کدام نما (View) برای مرتب‌سازی سریع اسلایدها و جابجایی ترتیبی آن‌ها مناسب‌تر است؟",
        "options": ["Slide Sorter", "Normal", "Reading View", "Slide Master"],
        "correct_index": 0,
        "explanation": "نمای Slide Sorter تمام اسلایدهای ارائه را در کنار هم به صورت کوچک نمایش داده و امکان کشیدن و رها کردن برای تغییر چیدمان را فراهم می‌کند.",
        "difficulty_level": "easy",
        "source_channel": "ICDL100"
    },
    {
        "category": "icdl",
        "question_text": "کدام پروتکل اینترنتی برای انتقال امن صفحات وب و تبادل رمزنگاری‌شده داده‌ها استفاده می‌شود؟",
        "options": ["HTTP", "HTTPS", "FTP", "SMTP"],
        "correct_index": 1,
        "explanation": "پروتکل HTTPS از گواهی SSL/TLS برای رمزنگاری تبادلات میان کلاینت و سرور استفاده می‌کند (پورت ۴۴۳).",
        "difficulty_level": "easy",
        "source_channel": "ICDL100"
    },
    {
        "category": "icdl",
        "question_text": "در اکسل، ارجاع مطلق به سلول B5 با کدام قالب ثبت می‌شود تا در کپی کردن تغییر نکند؟",
        "options": ["B$5", "$B$5", "$B5", "&B&5"],
        "correct_index": 1,
        "explanation": "علامت $ قبل از نام ستون و شماره ردیف ($B$5) سلول را کاملاً قفل و به مرجع مطلق تبدیل می‌کند.",
        "difficulty_level": "medium",
        "source_channel": "ICDL100"
    },
    {
        "category": "icdl",
        "question_text": "کدام نوع بدافزار برای کنترل از راه دور سیستم کاربر بدون اطلاع وی استفاده می‌شود و اغلب پشت یک برنامه مفید پنهان است؟",
        "options": ["اسب تروا (Trojan)", "کرم (Worm)", "ویروس ماکرو", "جاسوس‌افزار (Spyware)"],
        "correct_index": 0,
        "explanation": "تروجان یا اسب تروا در ظاهر برنامه‌ای مشروع است اما پس از اجرا دسترسی پنهانی و کنترل سیستم را در اختیار مهاجم قرار می‌دهد.",
        "difficulty_level": "hard",
        "source_channel": "ICDL100"
    },
    {
        "category": "icdl",
        "question_text": "کلید میانبر ایجاد یک پوشه جدید در محیط ویندوز فایل اکسپلورر چیست؟",
        "options": ["Ctrl + Shift + N", "Ctrl + N", "Alt + Shift + N", "Shift + F10"],
        "correct_index": 0,
        "explanation": "در ویندوز کلید میانبر Ctrl + Shift + N یک New Folder بلافاصله می‌سازد.",
        "difficulty_level": "easy",
        "source_channel": "ICDL100"
    },

    # --- سوالات فناوری اطلاعات و کامپیوتر ---
    {
        "category": "computer",
        "question_text": "در مدل هفت‌لایه‌ای OSI، کدام لایه وظیفه مسیریابی (Routing) و آدرس‌دهی منطقی (IP) بسته‌ها را بر عهده دارد؟",
        "options": ["لایه پیوند داده (Data Link)", "لایه شبکه (Network)", "لایه انتقال (Transport)", "لایه فیزیکی (Physical)"],
        "correct_index": 1,
        "explanation": "لایه سوم مدل OSI یعنی لایه شبکه (Network Layer) مدیریت آدرس‌دهی منطقی IP و مسیریابی بسته‌های اطلاعاتی بین شبکه‌ها را انجام می‌دهد.",
        "difficulty_level": "medium",
        "source_channel": "camputerraheeestekhdam"
    },
    {
        "category": "computer",
        "question_text": "پیچیدگی زمانی مرتب‌سازی ادغامی (Merge Sort) در بدترین حالت (Worst-case) کدام است؟",
        "options": ["O(n)", "O(n log n)", "O(n²)", "O(log n)"],
        "correct_index": 1,
        "explanation": "مرتب‌سازی ادغامی بر پایه تقسیم و حل کار می‌کند و پیچیدگی زمانی آن در بهترین، میانگین و بدترین حالت همیشه O(n log n) باقی می‌ماند.",
        "difficulty_level": "medium",
        "source_channel": "camputerraheeestekhdam"
    },
    {
        "category": "computer",
        "question_text": "در پایگاه داده رابطه‌ای، ویژگی ACID که تضمین می‌کند یک تراکنش یا به طور کامل انجام می‌شود یا اصلاً اثری از آن باقی نمی‌ماند چیست؟",
        "options": ["Atomicity (تجزیه‌ناپذیری)", "Consistency (سازگاری)", "Isolation (انزوا)", "Durability (پایداری)"],
        "correct_index": 0,
        "explanation": "اصل Atomicity بیانگر قاعده همه‌یاهیچ (All-or-Nothing) در تراکنش‌های پایگاه داده است.",
        "difficulty_level": "easy",
        "source_channel": "camputerraheeestekhdam"
    },
    {
        "category": "computer",
        "question_text": "کدام الگوریتم زمان‌بندی پردازنده در سیستم عامل‌ها ممکن است منجر به گرسنگی (Starvation) فرآیندهای طولانی شود؟",
        "options": ["Round Robin (نوبت گردشی)", "First-Come First-Served (FCFS)", "Shortest Job First (SJF)", "Priority Scheduling با روش Aging"],
        "correct_index": 2,
        "explanation": "در الگوریتم SJF، در صورتی که دائماً کارهای کوتاه وارد صف شوند، کارهای طولانی ممکن است هرگز شانس اجرا پیدا نکنند که پدیده Starvation است.",
        "difficulty_level": "hard",
        "source_channel": "camputerraheeestekhdam"
    },
    {
        "category": "computer",
        "question_text": "دستور SQL مناسب برای حذف دائمی ساختار یک جدول به همراه تمام داده‌ها و ایندکس‌های آن کدام است؟",
        "options": ["DELETE TABLE", "TRUNCATE TABLE", "DROP TABLE", "REMOVE TABLE"],
        "correct_index": 2,
        "explanation": "دستور DROP TABLE کل جدول، شما، ایندکس‌ها و داده‌ها را از دیتابیس پاک می‌کند؛ در حالی که TRUNCATE فقط ردیف‌های داده را خالی می‌کند.",
        "difficulty_level": "easy",
        "source_channel": "camputerraheeestekhdam"
    },

    # --- سوالات قوانین و مقررات اداری ---
    {
        "category": "laws",
        "question_text": "بر اساس ماده ۴۵ قانون مدیریت خدمات کشوری، استخدام در دستگاه‌های اجرایی به چه شکل‌هایی مجاز است؟",
        "options": ["رسمی و پیمانی", "رسمی، پیمانی و قراردادی", "پیمانی و کارمزدی", "رسمی و شرکتی"],
        "correct_index": 0,
        "explanation": "طبق ماده ۴۵ قانون مدیریت خدمات کشوری، استخدام به دو صورت رسمی (برای تصدی پست‌های ثابت در مشاغل حاکمیتی) و پیمانی (برای تصدی پست‌های سازمانی برای مدت معین) صورت می‌گیرد.",
        "difficulty_level": "medium",
        "source_channel": "gavaninraheeestekhdam"
    },
    {
        "category": "laws",
        "question_text": "طبق قانون مدیریت خدمات کشوری، حداکثر سقف مجاز پرداخت اضافه کار ماهانه به کارمندان معادل چند ساعت در ماه است؟",
        "options": ["۱۲۰ ساعت", "۱۷۵ ساعت", "۱۴۰ ساعت", "۱۶۰ ساعت"],
        "correct_index": 1,
        "explanation": "طبق مقررات ماده ۹۳ قانون مدیریت خدمات کشوری، سقف اضافه کار ماهانه حداکثر ۱۷۵ ساعت تعیین شده است.",
        "difficulty_level": "hard",
        "source_channel": "gavaninraheeestekhdam"
    },
    {
        "category": "laws",
        "question_text": "کدام مرجع صالح به رسیدگی به شکایات و اعتراضات مردم نسبت به آیین‌نامه‌ها و مصوبات دولتی خلاف قانون است؟",
        "options": ["شورای حل اختلاف", "دیوان عدالت اداری", "سازمان بازرسی کل کشور", "دیوان محاسبات کشور"],
        "correct_index": 1,
        "explanation": "بر اساس اصل ۱۷۳ قانون اساسی، دیوان عدالت اداری به منظور رسیدگی به شکایات، تظلمات و اعتراضات مردم نسبت به مأمورین یا واحدها یا آیین‌نامه‌های دولتی تشکیل شده است.",
        "difficulty_level": "easy",
        "source_channel": "gavaninraheeestekhdam"
    },
    {
        "category": "laws",
        "question_text": "مرخصی استحقاقی سالانه کارمندان مشمول قانون مدیریت خدمات کشوری چند روز در سال است؟",
        "options": ["۲۶ روز", "۳۰ روز", "۳۵ روز", "۲۰ روز"],
        "correct_index": 1,
        "explanation": "طبق ماده ۸۴ قانون مدیریت خدمات کشوری، کارمندان دستگاه‌های اجرایی سالانه ۳۰ روز حق استفاده از مرخصی استحقاقی با استفاده از حقوق و فوق‌العاده‌های مربوط را دارند.",
        "difficulty_level": "easy",
        "source_channel": "gavaninraheeestekhdam"
    },
    {
        "category": "laws",
        "question_text": "مطابق قانون اساسی جمهوری اسلامی ایران، تفسیر قوانین عادی بر عهده کدام نهاد است؟",
        "options": ["شورای نگهبان", "مجلس شورای اسلامی", "رئیس قوه قضائیه", "مجمع تشخیص مصلحت نظام"],
        "correct_index": 1,
        "explanation": "طبق اصل ۷۳ قانون اساسی، شرح و تفسیر قوانین عادی در صلاحیت مجلس شورای اسلامی است (تفسیر قانون اساسی بر عهده شورای نگهبان است).",
        "difficulty_level": "medium",
        "source_channel": "gavaninraheeestekhdam"
    },

    # --- سوالات معارف و اندیشه اسلامی ---
    {
        "category": "maaref",
        "question_text": "اعتقاد به اینکه هیچ پدیده‌ای بدون اراده و مشیت خداوند در جهان هستی رخ نمی‌دهد، بیانگر کدام مرتبه از توحید است؟",
        "options": ["توحید در خالقیت", "توحید در ربوبیت", "توحید در افعال", "توحید در الوهیت"],
        "correct_index": 2,
        "explanation": "توحید افعالی یعنی همه حوادث، پدیده‌ها و کنش‌های جهان تحت قدرت و اراده بالذات خداوند جاری است (لا موثّر فی الوجود الا الله).",
        "difficulty_level": "medium",
        "source_channel": "maarefraheeeestekhdam"
    },
    {
        "category": "maaref",
        "question_text": "کدام سوره در قرآن کریم به «قلب قرآن» شهرت دارد؟",
        "options": ["سوره یاسین", "سوره الرحمن", "سوره حمد", "سوره واقعه"],
        "correct_index": 0,
        "explanation": "بر اساس روایات معتبر ائمه معصومین (ع)، سوره مبارکه «یس» قلب قرآن کریم نامیده شده است.",
        "difficulty_level": "easy",
        "source_channel": "maarefraheeeestekhdam"
    },
    {
        "category": "maaref",
        "question_text": "مهم‌ترین دلیل عقلی ضرورت معاد در آموزه‌های کلامی و فلسفه اسلامی چیست؟",
        "options": ["برهان حکمت و برهان عدالت", "برهان نظم و برهان علیت", "برهان امکان و وجوب", "برهان تجربه درونی"],
        "correct_index": 0,
        "explanation": "دو برهان اساسی عقلی بر ضرورت معاد، برهان حکمت خداوند (بیهوده نبودن آفرینش انسان) و برهان عدالت الهی (پاداش نیکوکاران و کیفر ستمکاران) می‌باشند.",
        "difficulty_level": "medium",
        "source_channel": "maarefehrah"
    },
    {
        "category": "maaref",
        "question_text": "نامه مشهور حضرت علی (ع) به مالک اشتر نخعی در نهج‌البلاغه با چه موضوع و نامه‌ای شماره‌گذاری شده است؟",
        "options": ["نامه ۳۱ (توصیه به فرزند)", "نامه ۵۳ (عهدنامه مالک اشتر - منشور حکومت)", "خطبه ۱۹۳ (همام)", "نامه ۴۷ (وصیت)"],
        "correct_index": 1,
        "explanation": "نامه ۵۳ نهج البلاغه عهدنامه تاریخی و منشور جامع حکومتداری و حقوق شهروندان خطاب به مالک اشتر است.",
        "difficulty_level": "easy",
        "source_channel": "maarefehrah"
    },

    # --- سوال نمونه نیازمند بررسی ادمین (Quarantine Review Queue) ---
    {
        "category": "laws",
        "question_text": "حداقل سن استخدام برای داوطلبان دارای مدرک تحصیلی کارشناسی در آزمون‌های استخدامی چند سال است؟",
        "options": ["۲۰ سال", "۲۲ سال", "۲۴ سال", "۲۵ سال"],
        "correct_index": None, # فاقد پاسخ صریح جهت تست صف بررسی ادمین!
        "explanation": "نیازمند تطبیق با آخرین اصلاحیه دفترچه آزمون فراگیر سال جدید.",
        "difficulty_level": "medium",
        "status": "needs_review",
        "source_channel": "raheeestekhdam2"
    }
]

SAMPLE_NEWS = [
    {
        "title": "انتشار دفترچه راهنمای یازدهمین آزمون استخدامی مشترک فراگیر دستگاه‌های اجرایی کشور",
        "slug": "announcement-11th-executive-employment-exam",
        "summary": "ثبت‌نام یازدهمین آزمون مشترک فراگیر دستگاه‌های اجرایی کشور برای جذب در بیش از ۵۰ وزارتخانه و سازمان دولتی آغاز شد.",
        "content": """ثبت‌نام یازدهمین آزمون استخدامی مشترک فراگیر دستگاه‌های اجرایی کشور از طریق سایت مرکز آزمون جهاد دانشگاهی آغاز شد.

داوطلبان متقاضی استخدام در رشته‌های شغلی مختلف از جمله کارشناس فناوری اطلاعات، امور اداری، حقوقی، حسابداری و آموزش‌وپرورش می‌توانند با مطالعه دقیق دفترچه راهنما اقدام به ثبت‌نام نمایند.

مواد آزمون در حیطه عمومی شامل:
۱. فناوری اطلاعات و مهارت‌های هفتگانه (ICDL)
۲. معارف و اندیشه اسلامی
۳. قوانین و مقررات اداری و استخدامی
۴. زبان و ادبیات فارسی
۵. هوش و توانمندی‌های ذهنی

کارت ورود به جلسه آزمون در دهه اول ماه آینده منتشر خواهد شد و نتایج مرحله اول کتبی ظرف ۴۵ روز اعلام می‌گردد.""",
        "category": "employment",
        "source_channel": "Iranestekhdam_ir",
        "cta_category": "icdl"
    },
    {
        "title": "جزییات استخدام ۲۰ هزار نیروی جدید در وزارت بهداشت و کادر درمان",
        "slug": "health-ministry-hiring-20000-staff",
        "summary": "معاون توسعه وزارت بهداشت از اخذ مجوزهای نهایی جهت جذب ۲۰ هزار پرستار، ماما و نیروی درمانی و پشتیبانی در سراسر کشور خبر داد.",
        "content": """معاونت توسعه مدیریت و منابع وزارت بهداشت، درمان و آموزش پزشکی اعلام کرد با موافقت سازمان اداری و استخدامی کشور، مجوز جذب و به‌کارگیری ۲۰ هزار نیروی انسانی در بیمارستان‌ها و مراکز درمانی تازه تأسیس صادر شد.

آزمون کتبی متمرکز شامل دو بخش عمومی و تخصصی خواهد بود. در بخش آزمون عمومی، پاسخگویی به سوالات قوانین اداری، فناوری اطلاعات و احکام اسلامی الزامی است.

داوطلبان می‌توانند از هم‌اکنون با شرکت در آزمون‌های آزمایشی استاندارد سایت تست ۹۸ آمادگی خود را افزایش دهند.""",
        "category": "employment",
        "source_channel": "Iranestekhdam_ir",
        "cta_category": "laws"
    },
    {
        "title": "ابلاغ جدول افزایش حقوق و حق بیمه کارمندان و شاغلین در سال جاری",
        "slug": "salary-increase-and-insurance-rates-table",
        "summary": "شورای عالی کار و سازمان برنامه و بودجه آخرین بخشنامه پیرامون تغییرات حداقل دستمزد و سهم بیمه بازنشستگی را اعلام کردند.",
        "content": """بر اساس مصوبه جدید هیئت وزیران، ضوابط پرداخت حقوق و مزایای مستمر کارکنان دستگاه‌های اجرایی موضوع ماده ۵ قانون مدیریت خدمات کشوری ابلاغ شد.

نکات برجسته بخشنامه:
- افزایش ضریب ریالی حقوق به میزان مصوب مجلس شورای اسلامی
- تعیین سقف فوق‌العاده شغل و اضافه کار
- تسهیلات ویژه برای کارکنان دارای فرزند

برای مطالعه کامل مفاد قانونی و تست‌های مربوط به قوانین استخدامی به بخش آزمون‌های قوانین سایت مراجعه کنید.""",
        "category": "economy",
        "source_channel": "nerkh_net",
        "cta_category": "laws"
    },
    {
        "title": "اعلام تاریخ برگزاری آزمون استخدامی بانک‌های سپه، صادرات و تجارت",
        "slug": "bank-recruitment-exams-schedule",
        "summary": "تقویم زمان‌بندی آزمون‌های کتبی بانک‌های دولتی و خصوصی کشور برای مشاغل بانکدار و متصدی فناوری اطلاعات منتشر گردید.",
        "content": """داوطلبان گرامی متقاضی استخدام در شبکه بانکی کشور توجه فرمایند:
آزمون‌های کتبی استخدامی بانک‌ها بر مبنای دفترچه منتشر شده در ماه‌های آینده برگزار می‌شود. بیشترین ضریب در دروس عمومی به مهارت‌های هفتگانه کامپیوتر (ICDL) و هوش و ریاضیات اختصاص داده شده است.

سایت تست ۹۸ پکیج جامع سوالات سال‌های گذشته بانک‌ها را در قالب آزمون‌های شبیه‌ساز آنلاین رایگان در اختیار شما قرار داده است.""",
        "category": "employment",
        "source_channel": "raheeestekhdam2",
        "cta_category": "icdl"
    }
]

async def seed_initial_data():
    """تزریق داده‌های اولیه واقعی به پایگاه داده"""
    async with get_db() as db:
        # درج سوالات
        for q in SAMPLE_QUESTIONS:
            text_hash = calculate_text_hash(q["question_text"])
            status = q.get("status", "published")
            await db.execute("""
                INSERT INTO questions (
                    category, question_text, options_json, correct_index,
                    explanation, difficulty_level, status, text_hash, source_channel
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(text_hash) DO NOTHING
            """, (
                q["category"],
                q["question_text"],
                json.dumps(q["options"], ensure_ascii=False),
                q["correct_index"],
                q.get("explanation"),
                q.get("difficulty_level", "medium"),
                status,
                text_hash,
                q.get("source_channel", "system")
            ))

        # درج اخبار
        for n in SAMPLE_NEWS:
            await db.execute("""
                INSERT INTO news (
                    title, slug, summary, content, category,
                    source_channel, cta_category, is_published
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(slug) DO UPDATE SET
                    title=excluded.title,
                    summary=excluded.summary,
                    content=excluded.content,
                    cta_category=excluded.cta_category
            """, (
                n["title"],
                n["slug"],
                n["summary"],
                n["content"],
                n["category"],
                n["source_channel"],
                n.get("cta_category", "employment")
            ))

            # ایندکس در FTS5
            await db.execute("""
                INSERT INTO news_fts (title, content)
                VALUES (?, ?)
            """, (n["title"], n["content"]))

        await db.commit()
    print("Seed data injected successfully!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_initial_data())
