"""在线封面搜索与下载服务

搜索策略（按豆包建议优化）：
  ISBN精准查 → ISBN直查CDN → 书名+作者 → 纯书名 → 英文名提取
  每步失败自动重试3次，间隔1秒
"""
import asyncio
import json
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import requests as _requests

from ..config import settings

# 修补 DNS 解析
try:
    from .dns_resolver import patch_socket
    patch_socket()
except Exception:
    pass

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
_cover_pool = ThreadPoolExecutor(max_workers=2)


# ========== 工具函数 ==========

def _safe_filename(text: str, max_len: int = 60) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "_", text)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:max_len]


def _clean_isbn(isbn: str) -> Optional[str]:
    """清洗 ISBN：去横线/空格，校验合法性"""
    if not isbn or not isbn.strip():
        return None
    clean = isbn.strip().replace("-", "").replace(" ", "")
    # ISBN10 = 10位数字(最后一位可能是X), ISBN13 = 13位数字
    if re.match(r"^\d{9}[\dX]$", clean) or re.match(r"^\d{13}$", clean):
        return clean
    return None


def _clean_title(title: str) -> str:
    """清洗书名：去除版次、丛书名、标点噪音"""
    # 去除 "第X版" "修订本" "精装" 等后缀
    title = re.sub(r"第[\d一二三四五六七八九十]+版", "", title)
    title = re.sub(r"(修订本|增订本|精装|平装| Hardcover|Paperback)", "", title, flags=re.IGNORECASE)
    # 去除多余的空白
    title = re.sub(r"\s+", " ", title).strip()
    return title


# ========== HTTP 请求（带重试） ==========

async def _fetch_url(url: str, timeout: int = 5, retries: int = 3) -> Optional[str]:
    """获取网页内容，自动重试3次"""
    loop = asyncio.get_event_loop()
    last_err = None
    for attempt in range(retries):
        try:
            resp = await loop.run_in_executor(
                _cover_pool,
                lambda: _requests.get(
                    url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                    },
                    timeout=timeout,
                ),
            )
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                await asyncio.sleep(1)  # 间隔1秒再试
    return None


async def _download_file(url: str, save_path: Path, timeout: int = 8, retries: int = 3) -> bool:
    """下载文件，自动重试3次"""
    loop = asyncio.get_event_loop()

    def _dl():
        try:
            resp = _requests.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
                timeout=timeout,
                stream=True,
            )
            if resp.status_code == 200 and int(resp.headers.get("content-length", 1)) > 1000:
                with open(save_path, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                return True
        except Exception:
            pass
        return False

    for attempt in range(retries):
        ok = await loop.run_in_executor(_cover_pool, _dl)
        if ok:
            return True
        if attempt < retries - 1:
            await asyncio.sleep(1)
    return False


# ========== 各数据源 ==========

async def fetch_cover_from_douban(title: str) -> Optional[str]:
    """豆瓣通用搜索"""
    query = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", _clean_title(title)).strip()
    query = re.sub(r"\s+", "+", query)[:100]
    if not query:
        return None

    url = f"https://www.douban.com/search?q={query}&cat=1001"
    html = await _fetch_url(url)
    if not html:
        return None

    # 提取封面图片URL
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
            c = c.replace("/m/public/", "/l/public/")
            c = c.replace("/s/public/", "/l/public/")
            return c
    return None


async def fetch_cover_from_openlibrary_api(isbn: str) -> Optional[str]:
    """OpenLibrary API 按 ISBN 查（返回大图URL）"""
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    html = await _fetch_url(url)
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
    """OpenLibrary 封面 CDN 直连（无需API，直接下载）"""
    for size in ["L", "M", "S"]:
        cdn_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-{size}.jpg"
        ext = ".jpg"
        filename = f"_ol_test_{isbn}_{size}{ext}"
        save_dir = settings.UPLOAD_DIR / "covers"
        save_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = save_dir / filename

        ok = await _download_file(cdn_url, tmp_path, timeout=2)
        if ok:
            return str(tmp_path)
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
    return None


async def fetch_cover_from_google(title: str, author: str = "") -> Optional[str]:
    """Google Books API"""
    query = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", _clean_title(title)).strip()
    query = re.sub(r"\s+", "+", query)[:100]
    if not query:
        return None
    if author:
        clean_author = re.sub(r"[^a-zA-Z\s]", "", author).strip()[:30].replace(" ", "+")
        if clean_author:
            query += f"+inauthor:{clean_author}"

    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=5"
    html = await _fetch_url(url)
    if not html:
        return None

    try:
        data = json.loads(html)
        for item in data.get("items", []):
            img_links = item.get("volumeInfo", {}).get("imageLinks", {})
            for size in ["extraLarge", "large", "medium", "small", "thumbnail"]:
                img_url = img_links.get(size)
                if img_url:
                    return img_url.replace("http://", "https://").split("&")[0]
    except Exception:
        pass
    return None


async def download_cover(img_url: str, title: str) -> Optional[str]:
    """下载封面图片到本地"""
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


# ========== 主搜索入口 ==========

async def fetch_cover_for_book(
    title: str,
    title_en: str = "",
    author: str = "",
    isbn: str = "",
) -> str:
    """
    为书刊查找封面，返回保存后的相对路径。
    
    搜索链（按优先级）：
      1. ISBN → OpenLibrary CDN 直连（2秒超时）
      2. ISBN → OpenLibrary API（3秒超时）
      3. 书名+作者 → Google Books（3秒超时）
      4. 书名 → 豆瓣（3秒超时）
      5. 书名 → Google Books
      6. 英文名 → 豆瓣/Google
      
    总超时控制在15秒以内。
    """
    search_title = title_en or title
    clean_isbn = _clean_isbn(isbn)

    # 1️⃣ ISBN → OpenLibrary CDN 直连（超短超时）
    if clean_isbn:
        tmp_path_str = await fetch_cover_from_openlibrary_cdn(clean_isbn)
        if tmp_path_str:
            tmp_path = Path(tmp_path_str)
            ext = tmp_path.suffix
            filename = f"{_safe_filename(search_title)}_{uuid.uuid4().hex[:8]}{ext}"
            save_dir = settings.UPLOAD_DIR / "covers"
            save_path = save_dir / filename
            import shutil
            shutil.copy2(tmp_path, save_path)
            tmp_path.unlink(missing_ok=True)
            return f"uploads/covers/{filename}"

    # 2️⃣ ISBN → OpenLibrary API
    if clean_isbn:
        img_url = await fetch_cover_from_openlibrary_api(clean_isbn)
        if img_url:
            result = await download_cover(img_url, search_title)
            if result:
                return result

    # 3️⃣ 书名+作者 → Google Books
    if search_title:
        img_url = await fetch_cover_from_google(search_title, author)
        if img_url:
            result = await download_cover(img_url, search_title)
            if result:
                return result

    # 4️⃣ 书名 → 豆瓣
    if search_title:
        img_url = await fetch_cover_from_douban(search_title)
        if img_url:
            result = await download_cover(img_url, search_title)
            if result:
                return result

    # 5️⃣ 原标题 → Google Books
    if title and title != search_title:
        img_url = await fetch_cover_from_google(title, author)
        if img_url:
            result = await download_cover(img_url, title)
            if result:
                return result

    # 6️⃣ 英文名提取
    if "，" in title or "," in title:
        parts = re.split(r"[，,]", title, maxsplit=1)
        en_part = parts[0].strip()
        if en_part and en_part not in (search_title, title):
            img_url = await fetch_cover_from_google(en_part, author)
            if not img_url:
                img_url = await fetch_cover_from_douban(en_part)
            if img_url:
                result = await download_cover(img_url, en_part)
                if result:
                    return result

    return ""


async def fetch_and_save_cover(book) -> str:
    return await fetch_cover_for_book(
        title=book.title,
        title_en=book.title_en or "",
        author=book.author or "",
        isbn=book.isbn or "",
    )
