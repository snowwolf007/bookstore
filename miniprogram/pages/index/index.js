const { api } = require('../../utils/api')

const CATEGORY_ICONS = {
  '建筑设计': '🏗️',
  '室内设计': '🛋️',
  '室内设计-软装': '🎨',
  '景观/园林': '🌿',
  '建筑理论/历史': '📐',
  '杂志/期刊': '📰',
  '日文原版': '🗾',
}

Page({
  data: {
    banners: [],
    categories: [],
    books: [],
    loading: true,
    errorMsg: ''
  },

  onLoad() {
    this.loadData()
  },

  async loadData() {
    try {
      wx.showLoading({ title: '加载中...' })
      
      const [catRes, bookRes] = await Promise.all([
        api.getCategories().catch(e => { throw new Error('分类加载失败: ' + JSON.stringify(e)) }),
        api.getAllBooks(1).catch(e => { throw new Error('书单加载失败: ' + JSON.stringify(e)) })
      ])

      const categories = (catRes || []).map(c => ({
        id: c.id,
        name: c.name,
        icon: CATEGORY_ICONS[c.name] || '📖'
      }))

      const items = bookRes.items || bookRes || []
      const books = items.map(b => ({
        ...b,
        coverUrl: b.cover_path ? 'http://localhost:8899/' + b.cover_path : ''
      }))

      const banners = books.filter(b => b.coverUrl).slice(0, 5).map(b => ({
        id: b.id,
        title: b.title_cn || b.title_en || b.title,
        coverUrl: b.coverUrl
      }))

      this.setData({ banners, categories, books, loading: false, errorMsg: '' })
      wx.hideLoading()
    } catch (err) {
      console.error('加载失败', err)
      this.setData({ loading: false, errorMsg: err.message || '网络请求失败，请检查：\n1. 开发者工具→设置→安全→不校验合法域名 是否勾选\n2. http://localhost:8899 是否正常运行' })
      wx.hideLoading()
    }
  },

  toBook(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/book/book?id=${id}` })
  },

  toCategory(e) {
    wx.switchTab({ url: `/pages/category/category` })
  }
})
