import datetime
import jdatetime
from typing import Optional, Any

def to_jalali(value: Any, fmt: str = "%Y/%m/%d") -> str:
    """
    تبدیل تاریخ میلادی یا رشته زمان ISO به تاریخ شمسی فارسی
    مثال: 2026-11-04 -> ۱۴۰۵/۰۸/۱۴
    """
    if not value:
        return ""
    try:
        if isinstance(value, str):
            clean_val = value.split(".")[0].replace("T", " ")
            if len(clean_val) == 10:
                dt = datetime.datetime.strptime(clean_val, "%Y-%m-%d")
            else:
                dt = datetime.datetime.strptime(clean_val, "%Y-%m-%d %H:%M:%S")
        elif isinstance(value, (datetime.datetime, datetime.date)):
            dt = value
        else:
            return str(value)[:10]

        jdt = jdatetime.datetime.fromgregorian(datetime=dt)
        return jdt.strftime(fmt)
    except Exception:
        return str(value)[:10]
