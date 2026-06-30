const API_BASE = 'http://localhost:8899'

// ===== API 封装 =====
function request(url, data = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: API_BASE + url,
      data: data,
      success: res => {
        if (res.statusCode === 200) resolve(res.data)
        else reject({ code: res.statusCode, msg: res.data })
      },
      fail: err => reject(err)
    })
  })
}

// 公开接口
const api = {
  // 首页 - 获取推荐书单
  getFeaturedBooks() {
    return request('/api/books/', { featured: true })
  },
  // 分类列表
  getCategories() {
    return request('/api/books/categories')
  },
  // 按分类获取书单
  getBooksByCategory(categoryId, page = 1) {
    return request('/api/books/', { category_id: categoryId, page, page_size: 20 })
  },
  // 搜索
  searchBooks(keyword, page = 1) {
    return request('/api/books/', { search: keyword, page, page_size: 20 })
  },
  // 书籍详情
  getBookDetail(bookId) {
    return request('/api/books/' + bookId)
  },
  // 全部书单（首页用）
  getAllBooks(page = 1) {
    return request('/api/books/', { page, page_size: 20 })
  }
}

module.exports = { api }
