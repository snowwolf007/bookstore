"""
自定义 DNS 解析器 — 通过 HTTP DNS API (DoH) 解析域名。
绕过系统 DNS，适用于 MSYS2/bash 环境下系统 DNS 不可用的情况。
"""
import socket
import json
import http.client
import time
from typing import Optional

# 阿里云 DNS over HTTP (免费，国内速度快)
ALI_DNS_URL = "http://223.5.5.5/resolve?name={hostname}&type=A&short=1"

# DNS 响应缓存
_cache: dict = {}
_cache_ttl: int = 300  # 5 分钟


def resolve(hostname: str, timeout: float = 3.0) -> Optional[str]:
    """
    通过阿里云 HTTP DNS API 解析域名，返回 IP 地址。
    自动缓存结果。
    """
    now = time.time()
    if hostname in _cache:
        ip, expire = _cache[hostname]
        if now < expire:
            return ip

    try:
        conn = http.client.HTTPConnection("223.5.5.5", 80, timeout=timeout)
        path = f"/resolve?name={hostname}&type=A"
        conn.request("GET", path, headers={"Host": "dns.alidns.com"})
        resp = conn.getresponse()
        data = json.loads(resp.read())
        conn.close()

        # 阿里 DNS 返回格式有两种：
        # 1. 完整格式: {"Status":0, "Answer":[{"type":1,"data":"1.2.3.4"}]}
        # 2. short 格式: ["1.2.3.4", ...]
        if isinstance(data, list):
            for ip in data:
                if isinstance(ip, str) and ip.count(".") == 3:
                    _cache[hostname] = (ip, now + _cache_ttl)
                    return ip
        elif isinstance(data, dict) and data.get("Status") == 0:
            answers = data.get("Answer", [])
            for ans in answers:
                if ans.get("type") == 1:
                    ip = ans["data"]
                    ttl = ans.get("TTL", 300)
                    _cache[hostname] = (ip, now + min(ttl, _cache_ttl))
                    return ip
    except Exception:
        pass

    return None


def patch_socket():
    """
    修补 socket.getaddrinfo，使 urllib/httpx/requests 等库
    自动使用自定义 DNS 解析。
    """
    original_getaddrinfo = socket.getaddrinfo

    def patched_getaddrinfo(host, port, family=0, type_=0, proto=0, flags=0):
        # 如果是 IP 地址，直接使用原始函数
        try:
            socket.inet_aton(host)
            return original_getaddrinfo(host, port, family, type_, proto, flags)
        except OSError:
            pass

        # 尝试自定义 DNS 解析
        ip = resolve(host)
        if ip:
            return original_getaddrinfo(ip, port, family, type_, proto, flags)

        # 兜底
        return original_getaddrinfo(host, port, family, type_, proto, flags)

    socket.getaddrinfo = patched_getaddrinfo
    return True


# 测试
if __name__ == "__main__":
    import sys
    test_hosts = sys.argv[1:] if len(sys.argv) > 1 else [
        "www.googleapis.com",
        "openlibrary.org",
        "www.google.com",
    ]

    print("DNS Resolver Test (via Alibaba HTTP DNS)")
    print("=" * 50)
    for host in test_hosts:
        ip = resolve(host)
        if ip:
            print(f"  ✅ {host:35s} -> {ip}")
        else:
            print(f"  ❌ {host:35s} -> FAILED")

    print()
    print("Testing with patched socket + urllib...")
    patch_socket()
    try:
        import urllib.request
        r = urllib.request.urlopen(
            "https://www.googleapis.com/books/v1/volumes?q=architecture&maxResults=1",
            timeout=10
        )
        data = json.loads(r.read())
        items = data.get("items", [])
        if items:
            print(f"  ✅ Google Books: {items[0]['volumeInfo']['title']}")
        else:
            print("  ⚠️  No results")
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
