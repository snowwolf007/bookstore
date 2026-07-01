"""在线封面搜索与下载服务 - 纯异步 httpx 版本"""
import asyncio
import json
import os
import re
import uuid
from pathlib import Path
from typing import Optional

import httpx

from ..config import settings

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def _safe_filename(text: str, max_len: int = 60) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "_", text)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:max_len]


def _clean_isbn(isbn: str) -> Optional[str]:
    if not isbn or not isbn.strip():
        return None
    clean = isbn.strip().replace("-", "").replace(" ", "")
    if re.match(r"^\d{9}[\dX]$", clean) or re.match(r"^\d{13}$", clean):
        return clean
    return None


def _clean_title(title: str) -> str:
    title = re.sub(r"第[\d一二三四五六七八九十]+版", "", title)
    title = re.sub(r"(修订本|增订本|精装|平装| Hardcover|Paperback)", "", title, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", title).strip()


async def _fetch_url(url: str, timeout: int = 5, retries: int = 3) -> Optional[str]:
    """纯异步 HTTP 请求"""
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                )
                if resp.status_code == 200:
                    return resp.text
        except Exception:
            if attempt < retries - 1:
                await asyncio.sleep(1)
    return None


async def _download_file(url: str, save_path: Path, timeout: int = 8, retries: int = 3) -> bool:
    """纯异步下载文件"""
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                )
                if resp.status_code == 200 and len(resp.content) > 1000:
                    with open(save_path, "wb") as f:
                        f.write(resp.content)
                    return True
        except Exception:
            pass
        if attempt < retries - 1:
            await asyncio.sleep(1)
    return False


async def fetch_cover_from_douban(title: str) -> Optional[str]:
    """豆瓣通用搜索"""
    query = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", _clean_title(title)).strip()
    query = re.sub(r"\s+", "+", query)[:100]
    if not query:
        return None
    url = f"https://www.douban.com/search?q={query}&cat=1001"
    html = await _fetch_url(url, timeout=8, retries=2)
    if not html:
        return None
    urls = []
    idx = 0
    while True:
        img_start = html.find("<img", idx)
        if img_start < 0:
            break
        src_start = html.find('src="', img_start)
        if src_start < 0:
            idx = img_start + 4
            continue
        src_start += 5
        src_end = html.find('"', src_start)
        if src_end < 0:
            idx = src_start
            continue
        img_url = html[src_start:src_end]
        if img_url.startswith("http") and (".jpg" in img_url or ".jpeg" in img_url or ".png" in img_url):
            urls.append(img_url)
        idx = src_end + 1
    for c in urls:
        if "/subject/" in c or "/book/" in c:
            c = c.replace("/m/public/", "/l/public/").replace("/s/public/", "/l/public/")
            return c
    return None


async def fetch_cover_from_openlibrary_api(isbn: str) -> Optional[str]:
    """OpenLibrary API 按 ISBN 查"""
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    html = await _fetch_url(url, timeout=5)
    if not html:
        return None
    try:
        data = json.loads(html)
        cover = data.get(f"ISBN:{isbn}", {}).get("cover", {})
        for size in ["large", "medium", "small"]:
            img_url = cover.get(size)
            if img_url:
                return img_url
    except Exception:
        pass
    return None


async def fetch_cover_from_openlibrary_cdn(isbn: str) -> Optional[str]:
    """OpenLibrary 封面 CDN 直连"""
    for size in ["L", "M", "S"]:
        url = f"https://covers.openlibrary.org/b/isbn/{isbn}-{size}.jpg"
        filename = f"_ol_{isbn}_{size}.jpg"
        save_dir = settings.UPLOAD_DIR / "covers"
        save_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = save_dir / filename
        ok = await _download_file(url, tmp_path, timeout=3)
        if ok:
            return str(tmp_path)
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
    return None


async def fetch_cover_from_google(title: str, author: str = "") -> Optional[str]:
    """Google Books API"""
    query = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", _clean_title(title)).strip()
    query = re.sub(r"\s+", "+", query)[:80]
    if not query:
        return None
    if author:
        clean_author = re.sub(r"[^a-zA-Z\s]", "", author).strip()[:20].replace(" ", "+")
        if clean_author:
            query += f"+inauthor:{clean_author}"
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=5"
    html = await _fetch_url(url, timeout=5)
    if not html:
        return None
    try:
        data = json.loads(html)
        for item in data.get("items", []):
            imgs = item.get("volumeInfo", {}).get("imageLinks", {})
            for size in ["extraLarge", "large", "medium", "small", "thumbnail"]:
                img_url = imgs.get(size)
                if img_url:
                    return img_url.replace("http://", "https://").split("&")[0]
    except Exception:
        pass
    return None


async def download_cover(img_url: str, title: str) -> Optional[str]:
    if not img_url:
        return None
    ext = Path(img_url.split("?")[0]).suffix.lower()
    if ext not in ALLOWED_EXT:
        ext = ".jpg"
    filename = f"{_safe_filename(title)}_{uuid.uuid4().hex[:8]}{ext}"
    save_dir = settings.UPLOAD_DIR / "covers"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / filename
    ok = await _download_file(img_url, save_path)
    if ok:
        return f"uploads/covers/{filename}"
    return None


async def fetch_cover_for_book(
    title: str,
    title_en: str = "",
    author: str = "",
    isbn: str = "",
) -> str:
    search_title = title_en or title
    clean_isbn = _clean_isbn(isbn)

    # 1️⃣ ISBN → OpenLibrary CDN
    if clean_isbn:
        tmp = await fetch_cover_from_openlibrary_cdn(clean_isbn)
        if tmp:
            import shutil
            p = Path(tmp)
            fn = f"{_safe_filename(search_title)}_{uuid.uuid4().hex[:8]}{p.suffix}"
            dst = settings.UPLOAD_DIR / "covers" / fn
            shutil.copy2(p, dst)
            p.unlink(missing_ok=True)
            return f"uploads/covers/{fn}"

    # 2️⃣ ISBN → OpenLibrary API
    if clean_isbn:
        img = await fetch_cover_from_openlibrary_api(clean_isbn)
        if img:
            r = await download_cover(img, search_title)
            if r: return r

    # 3️⃣ 书名 → 豆瓣
    if search_title:
        img = await fetch_cover_from_douban(search_title)
        if img:
            r = await download_cover(img, search_title)
            if r: return r

    # 4️⃣ 书名 → Google Books
    if search_title:
        img = await fetch_cover_from_google(search_title, author)
        if img:
            r = await download_cover(img, search_title)
            if r: return r

    # 5️⃣ 原标题 → 豆瓣
    if title and title != search_title:
        img = await fetch_cover_from_douban(title)
        if img:
            r = await download_cover(img, title)
            if r: return r

    return ""


async def fetch_and_save_cover(book) -> str:
    return await fetch_cover_for_book(
        title=book.title,
        title_en=book.title_en or "",
        author=book.author or "",
        isbn=book.isbn or "",
    )
