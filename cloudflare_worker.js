// Cloudflare Worker — Google Books 封面搜索代理
// 部署方式：登录 cloudflare.com → Workers & Pages → 创建 Worker → 粘贴此代码

export default {
  async fetch(request) {
    const url = new URL(request.url);
    
    // 处理 CORS
    const headers = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Content-Type': 'application/json',
    };
    
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers });
    }

    // 健康检查
    if (url.pathname === '/health') {
      return new Response(JSON.stringify({ status: 'ok' }), { headers });
    }

    // 获取搜索参数
    const query = url.searchParams.get('q');
    const isbn = url.searchParams.get('isbn');
    
    if (!query && !isbn) {
      return new Response(JSON.stringify({ error: '需要 q (书名) 或 isbn 参数' }), { status: 400, headers });
    }

    let coverUrl = null;
    let bookTitle = null;

    // 1️⃣ 按 ISBN 查 OpenLibrary 封面 CDN
    if (isbn) {
      const cleanIsbn = isbn.replace(/[-\s]/g, '');
      if (/^\d{9}[\dX]$/.test(cleanIsbn) || /^\d{13}$/.test(cleanIsbn)) {
        for (const size of ['L', 'M', 'S']) {
          const cdnUrl = `https://covers.openlibrary.org/b/isbn/${cleanIsbn}-${size}.jpg`;
          const resp = await fetch(cdnUrl, { method: 'HEAD' });
          if (resp.ok) {
            // 重定向到原图
            return Response.redirect(cdnUrl, 302);
          }
        }
      }
    }

    // 2️⃣ 按书名查 Google Books
    const cleanQuery = query.replace(/[^\w\s\u4e00-\u9fff]/g, ' ').trim().slice(0, 100);
    const googleUrl = `https://www.googleapis.com/books/v1/volumes?q=${encodeURIComponent(cleanQuery)}&maxResults=5`;
    
    try {
      const resp = await fetch(googleUrl);
      const data = await resp.json();
      
      for (const item of data.items || []) {
        const imgs = item.volumeInfo?.imageLinks || {};
        for (const size of ['extraLarge', 'large', 'medium', 'small', 'thumbnail']) {
          const imgUrl = imgs[size];
          if (imgUrl) {
            const finalUrl = imgUrl.replace('http://', 'https://').split('&')[0];
            // 返回封面图片 URL
            return new Response(JSON.stringify({
              success: true,
              cover_url: finalUrl,
              title: item.volumeInfo?.title,
              source: 'google_books'
            }), { headers });
          }
        }
      }
    } catch(e) {
      // Google Books 失败，继续尝试其他源
    }

    // 3️⃣ 按书名查 OpenLibrary
    const olUrl = `https://openlibrary.org/search.json?q=${encodeURIComponent(cleanQuery)}&limit=3`;
    try {
      const resp = await fetch(olUrl);
      const data = await resp.json();
      const doc = data.docs?.[0];
      if (doc?.cover_i) {
        return Response.redirect(`https://covers.openlibrary.org/b/id/${doc.cover_i}-L.jpg`, 302);
      }
    } catch(e) {}

    return new Response(JSON.stringify({ success: false, message: '未找到封面' }), { headers });
  }
};
