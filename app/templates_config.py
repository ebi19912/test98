from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.utils import to_jalali
from app.config import settings

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# افزودن فیلتر تاریخ شمسی
templates.env.filters["jalali"] = to_jalali
templates.env.globals["settings"] = settings
