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
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
HEADERS_REF = {**HEADERS, "Referer": "https://www.douban.com/"}


async def _fetch(url: str, timeout: int = 5, retries: int = 2) -> Optional[str]:
    for a in range(retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as c:
                r = await c.get(url, headers=HEADERS)
                if r.status_code == 200:
                    return r.text
        except:
            if a < retries - 1:
                await asyncio.sleep(1)
    return None


async def _download(url: str, path: Path, timeout: int = 6, retries: int = 2) -> bool:
    for a in range(retries):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as c:
                r = await c.get(url, headers=HEADERS_REF)
                if r.status_code == 200 and len(r.content) > 2000:
                    with open(path, "wb") as f:
                        f.write(r.content)
                    return True
        except:
            if a < retries - 1:
                await asyncio.sleep(1)
    return False


def _safe_name(t: str, n: int = 60) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", re.sub(r"\s+", "_", t.strip()))[:n]


def _clean_isbn(s: str) -> Optional[str]:
    s = s.strip().replace("-", "").replace(" ", "") if s else ""
    if re.match(r"^\d{9}[\dX]$", s) or re.match(r"^\d{13}$", s):
        return s
    return None


def _clean_title(t: str) -> str:
    t = re.sub(r"第[\d一二三四五六七八九十]+版", "", t)
    t = re.sub(r"(修订本|增订本|精装|平装|Hardcover|Paperback)", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip()


# ========== DOUBAN ==========

async def douban_search(title: str) -> Optional[str]:
    """豆瓣搜索 → 取搜索结果页的封面"""
    q = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", _clean_title(title)).strip()
    q = re.sub(r"\s+", "+", q)[:100]
    if not q:
        return None

    html = await _fetch(f"https://www.douban.com/search?q={q}&cat=1001", timeout=8)
    if not html:
        return None

    # 提取封面和 subject ID
    urls = []
    subjects = []
    i = 0
    while True:
        a = html.find("<img", i)
        if a < 0:
            break
        b = html.find('src="', a)
        if b < 0:
            i = a + 4
            continue
        b += 5
        c = html.find('"', b)
        if c < 0:
            i = b
            continue
        u = html[b:c]
        if u.startswith("http") and any(x in u for x in [".jpg", ".jpeg", ".png"]):
            urls.append(u)
            # 提取 subject ID
            # 搜索附近是否有 subject/数字 的链接
            nearby = html[max(0, a - 200):c + 200]
            sub_match = re.findall(r"https://book\.douban\.com/subject/(\d+)/", nearby)
            if sub_match:
                subjects.append(sub_match[0])
        i = c + 1

    # 优先取带 subject 的封面（大图）
    for u, sid in zip(urls, subjects) if subjects else ([], []):
        u_big = u.replace("/m/public/", "/l/public/").replace("/s/public/", "/l/public/")
        return u_big

    # 没有 subject ID，直接取第一个封面
    for u in urls:
        if "/subject/" in u or "/book/" in u:
            return u.replace("/m/public/", "/l/public/").replace("/s/public/", "/l/public/")

    return None


async def douban_subject(subject_id: str) -> Optional[str]:
    """从豆瓣图书详情页取大封面"""
    html = await _fetch(f"https://book.douban.com/subject/{subject_id}/", timeout=8)
    if not html:
        return None
    # 找大图 cover
    m = re.search(r'src="(https://img[^"]+\.(?:jpg|jpeg|png))"', html)
    if m:
        return m.group(1).replace("/m/public/", "/l/public/").replace("/s/public/", "/l/public/")
    return None


# ========== OPENLIBRARY ==========

async def ol_cdn(isbn: str) -> Optional[str]:
    for s in ["L", "M", "S"]:
        fn = f"_ol_{isbn}_{s}.jpg"
        d = settings.UPLOAD_DIR / "covers"
        d.mkdir(parents=True, exist_ok=True)
        p = d / fn
        ok = await _download(f"https://covers.openlibrary.org/b/isbn/{isbn}-{s}.jpg", p, timeout=3)
        if ok:
            return str(p)
        if p.exists():
            p.unlink(missing_ok=True)
    return None


async def ol_api(isbn: str) -> Optional[str]:
    h = await _fetch(f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data")
    if not h:
        return None
    try:
        cv = json.loads(h).get(f"ISBN:{isbn}", {}).get("cover", {})
        for s in ["large", "medium", "small"]:
            u = cv.get(s)
            if u:
                return u
    except:
        pass
    return None


# ========== GOOGLE ==========

async def google(title: str, author: str = "") -> Optional[str]:
    q = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", _clean_title(title)).strip()
    q = re.sub(r"\s+", "+", q)[:80]
    if not q:
        return None
    if author:
        a = re.sub(r"[^a-zA-Z\s]", "", author).strip()[:20].replace(" ", "+")
        if a:
            q += f"+inauthor:{a}"
    h = await _fetch(f"https://www.googleapis.com/books/v1/volumes?q={q}&maxResults=5", timeout=5)
    if not h:
        return None
    try:
        for item in json.loads(h).get("items", []):
            imgs = item.get("volumeInfo", {}).get("imageLinks", {})
            for s in ["extraLarge", "large", "medium", "small", "thumbnail"]:
                u = imgs.get(s)
                if u:
                    return u.replace("http://", "https://").split("&")[0]
    except:
        pass
    return None


# ========== DOWNLOAD ==========

async def _dl(img_url: str, title: str) -> Optional[str]:
    if not img_url:
        return None
    ext = Path(img_url.split("?")[0]).suffix.lower() or ".jpg"
    fn = f"{_safe_name(title)}_{uuid.uuid4().hex[:8]}{ext}"
    d = settings.UPLOAD_DIR / "covers"
    d.mkdir(parents=True, exist_ok=True)
    p = d / fn
    ok = await _download(img_url, p)
    return f"uploads/covers/{fn}" if ok else None


# ========== MAIN SEARCH ==========

async def fetch_cover_for_book(
    title: str, title_en: str = "", author: str = "", isbn: str = ""
) -> str:
    """
    搜索链：
      1. ISBN → OpenLibrary CDN
      2. ISBN → OpenLibrary API
      3. 书名 → 豆瓣搜索（取搜索结果封面）
      4. 英文名 → 豆瓣搜索
      5. 书名 → Google Books
      6. 中文名 → 豆瓣搜索
      7. 提取关键英文词 → 豆瓣搜索
    """
    st = title_en or title
    ci = _clean_isbn(isbn)

    # --- ISBN 源 ---
    if ci:
        tmp = await ol_cdn(ci)
        if tmp:
            import shutil
            p = Path(tmp)
            fn = f"{_safe_name(st)}_{uuid.uuid4().hex[:8]}{p.suffix}"
            dst = settings.UPLOAD_DIR / "covers" / fn
            shutil.copy2(p, dst)
            p.unlink(missing_ok=True)
            return f"uploads/covers/{fn}"

    if ci:
        u = await ol_api(ci)
        if u:
            r = await _dl(u, st)
            if r:
                return r

    # --- 书名多策略搜索 ---
    queries = [st, title]
    if title_en:
        queries.append(title_en)

    # 提取英文部分（逗号前）
    if "，" in title or "," in title:
        parts = re.split(r"[，,]", title, maxsplit=1)
        queries.append(parts[0].strip())

    # 提取中文部分
    cn = re.search(r"[\u4e00-\u9fff]{2,}", title)
    if cn:
        queries.append(cn.group())

    # 提取关键英文词（前2个英文词）
    en_words = re.findall(r"[a-zA-Z]{3,}", title)
    if len(en_words) >= 2:
        queries.append(f"{en_words[0]} {en_words[1]}")

    # 去重
    seen = set()
    unique_queries = []
    for q in queries:
        if q and q not in seen:
            seen.add(q)
            unique_queries.append(q)

    # 依次尝试每个搜索词
    for q in unique_queries:
        u = await douban_search(q)
        if u:
            r = await _dl(u, st)
            if r:
                return r

    # --- Google Books ---
    for q in unique_queries[:3]:
        u = await google(q, author)
        if u:
            r = await _dl(u, st)
            if r:
                return r

    return ""


async def fetch_and_save_cover(book) -> str:
    return await fetch_cover_for_book(
        title=book.title,
        title_en=book.title_en or "",
        author=book.author or "",
        isbn=book.isbn or "",
    )
