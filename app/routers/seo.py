from fastapi import APIRouter, Response
import datetime
from app.config import settings
from app.database import get_db

router = APIRouter(tags=["seo"])

@router.get("/sitemap.xml", response_class=Response)
async def dynamic_sitemap():
    """تولید نقشه سایت XML پویا برای ایندکس سریع گوگل"""
    async with get_db() as db:
        cursor = await db.execute("SELECT slug, created_at FROM news WHERE is_published = 1 ORDER BY id DESC LIMIT 500")
        news_rows = await cursor.fetchall()

        cursor = await db.execute("SELECT code FROM categories WHERE is_exam = 1")
        cat_rows = await cursor.fetchall()

    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    # ۱. صفحات اصلی
    xml_lines.append(f"""  <url>
    <loc>{settings.SITE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>""")

    xml_lines.append(f"""  <url>
    <loc>{settings.SITE_URL}/exam/builder</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>""")

    xml_lines.append(f"""  <url>
    <loc>{settings.SITE_URL}/news</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.9</priority>
  </url>""")

    # ۲. دسته‌بندی‌های آزمون
    for (cat_code,) in cat_rows:
        xml_lines.append(f"""  <url>
    <loc>{settings.SITE_URL}/exam/builder?category={cat_code}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>""")

    # ۳. صفحات اخبار استخدامی
    for slug, created_at in news_rows:
        lastmod = created_at[:10] if created_at else today
        xml_lines.append(f"""  <url>
    <loc>{settings.SITE_URL}/news/{slug}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>""")

    xml_lines.append('</urlset>')

    return Response(content="\n".join(xml_lines), media_type="application/xml")

@router.get("/robots.txt", response_class=Response)
async def robots_txt():
    content = f"""User-agent: *
Allow: /
Allow: /news/
Allow: /exam/builder
Disallow: /admin/
Disallow: /user/
Disallow: /auth/

Sitemap: {settings.SITE_URL}/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")
