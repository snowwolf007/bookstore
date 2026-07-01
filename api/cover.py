import json, re, urllib.request, urllib.parse

def fetch(url, timeout=8):
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        return r.read().decode()
    except: return None

def handler(event, context):
    method = event.get("httpMethod", "GET")
    params = event.get("queryStringParameters") or {}
    path = event.get("path", "")

    if method == "OPTIONS":
        return ok("", 200, cors=True)
    if path == "/api/health":
        return ok({"status": "ok"})

    query = params.get("q", "")
    isbn = params.get("isbn", "")

    if not query and not isbn:
        return ok({"error": "需要 q 或 isbn 参数"}, 400)

    # 1) ISBN → OpenLibrary CDN
    if isbn:
        ci = isbn.replace("-","").replace(" ","")
        for sz in ["L","M","S"]:
            u = f"https://covers.openlibrary.org/b/isbn/{ci}-{sz}.jpg"
            try:
                r = urllib.request.urlopen(urllib.request.Request(u,method="HEAD"),timeout=4)
                if r.status == 200:
                    return {"statusCode":302,"headers":{"Location":u},"body":""}
            except: pass

    # 2) Google Books
    if query:
        q = re.sub(r"[^\w\s\u4e00-\u9fff]"," ",query).strip()[:100]
        h = fetch(f"https://www.googleapis.com/books/v1/volumes?q={urllib.parse.quote(q)}&maxResults=5")
        if h:
            try:
                for item in json.loads(h).get("items",[]):
                    imgs = item.get("volumeInfo",{}).get("imageLinks",{})
                    for s in ["extraLarge","large","medium","small","thumbnail"]:
                        u = imgs.get(s)
                        if u:
                            return ok({"success":True,"cover_url":u.replace("http://","https://").split("&")[0],"title":item["volumeInfo"].get("title",""),"source":"google_books"})
            except: pass

    # 3) OpenLibrary search
    if query:
        q = re.sub(r"[^\w\s]"," ",query).strip()[:100]
        h = fetch(f"https://openlibrary.org/search.json?q={urllib.parse.quote(q)}&limit=3")
        if h:
            try:
                for doc in json.loads(h).get("docs",[]):
                    c = doc.get("cover_i")
                    if c:
                        return {"statusCode":302,"headers":{"Location":f"https://covers.openlibrary.org/b/id/{c}-L.jpg"},"body":""}
            except: pass

    return ok({"success":False,"message":"未找到封面"})

def ok(body, code=200, cors=False):
    h = {"Content-Type":"application/json"}
    if cors: h["Access-Control-Allow-Origin"]="*"
    return {"statusCode":code,"headers":h,"body":json.dumps(body,ensure_ascii=False)}
