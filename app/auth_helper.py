import secrets
from typing import Optional, Dict, Any, Tuple
from fastapi import Request, Response
import aiosqlite
from app.database import get_db

async def get_current_user_and_guest(request: Request, response: Optional[Response] = None) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    استخراج کاربر لاگین‌شده و شناسه مهمان (guest_token) از کوکی‌ها
    در صورت نبود guest_token، یک توکن تصادفی ساخته و در کوکی ست می‌کند.
    """
    user_id_cookie = request.cookies.get("user_id")
    guest_token = request.cookies.get("guest_token")

    if not guest_token:
        guest_token = secrets.token_urlsafe(16)
        if response:
            response.set_cookie(
                key="guest_token",
                value=guest_token,
                max_age=30 * 24 * 3600,
                httponly=True,
                samesite="lax"
            )

    user = None
    if user_id_cookie and user_id_cookie.isdigit():
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (int(user_id_cookie),))
            row = await cursor.fetchone()
            if row:
                user = dict(row)

    return user, guest_token
