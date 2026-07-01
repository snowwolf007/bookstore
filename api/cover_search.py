"""Vercel 封面搜索服务 - 独立文件，不依赖 backend 目录"""
import json
import re
import urllib.request
from http.client import HTTPSConnection


def fetch(url, timeout=8):
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        return r.read().decode("utf-8", errors="replace")
    except:
        return None


def handler(request):
    """Vercel Serverless Function"""
    try:
        path = request.get("path", "")
        params = request.get("queryStringParameters", {}) or {}
        method = request.get("httpMethod", "GET")

        # CORS
        if method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
                "body": "",
            }

        # 健康检查
        if path == "/api/health":
            return {"statusCode": 200, "body": json.dumps({"status": "ok"})}

        # === 封面搜索 ===
        query = params.get("q", "")
        isbn = params.get("isbn", "")

        if not query and not isbn:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "需要 q (书名) 或 isbn 参数"}),
            }

        # 1️⃣ ISBN → OpenLibrary CDN
        if isbn:
            clean = isbn.replace("-", "").replace(" ", "")
            for size in ["L", "M", "S"]:
                url = f"https://covers.openlibrary.org/b/isbn/{clean}-{size}.jpg"
                try:
                    r = urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=5)
                    if r.status == 200:
                        return {
                            "statusCode": 302,
                            "headers": {"Location": url},
                            "body": "",
                        }
                except:
                    pass

        # 2️⃣ 书名 → Google Books
        if query:
            clean_q = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", query).strip()[:100]
            url = f"https://www.googleapis.com/books/v1/volumes?q={urllib.parse.quote(clean_q)}&maxResults=5"
            html = fetch(url)
            if html:
                try:
                    data = json.loads(html)
                    for item in data.get("items", []):
                        imgs = item.get("volumeInfo", {}).get("imageLinks", {})
                        for size in ["extraLarge", "large", "medium", "small", "thumbnail"]:
                            img = imgs.get(size)
                            if img:
                                img = img.replace("http://", "https://").split("&")[0]
                                return {
                                    "statusCode": 200,
                                    "body": json.dumps({
                                        "success": True,
                                        "cover_url": img,
                                        "title": item["volumeInfo"].get("title", ""),
                                        "source": "google_books",
                                    }),
                                }
                except:
                    pass

        # 3️⃣ 书名 → OpenLibrary
        if query:
            clean_q = re.sub(r"[^\w\s]", " ", query).strip()[:100]
            url = f"https://openlibrary.org/search.json?q={urllib.parse.quote(clean_q)}&limit=3"
            html = fetch(url)
            if html:
                try:
                    data = json.loads(html)
                    docs = data.get("docs", [])
                    for doc in docs:
                        cover = doc.get("cover_i")
                        if cover:
                            return {
                                "statusCode": 302,
                                "headers": {"Location": f"https://covers.openlibrary.org/b/id/{cover}-L.jpg"},
                                "body": "",
                            }
                except:
                    pass

        return {
            "statusCode": 200,
            "body": json.dumps({"success": False, "message": "未找到封面"}),
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
