const { api } = require('../../utils/api')

Page({
  data: {
    keyword: '',
    books: [],
    total: 0,
    searched: false,
    loading: false,
    page: 1
  },

  onInput(e) {
    this.setData({ keyword: e.detail.value })
  },

  async onSearch() {
    const kw = this.data.keyword.trim()
    if (!kw) return
    this.setData({ searched: true, loading: true, page: 1 })
    try {
      const res = await api.searchBooks(kw, 1)
      const items = res.items || res || []
      this.setData({
        books: items.map(b => ({ ...b, coverUrl: b.cover_path ? 'http://localhost:8899/' + b.cover_path : '' })),
        total: res.total || items.length,
        loading: false
      })
    } catch (err) {
      console.error(err)
      this.setData({ loading: false })
    }
  },

  toBook(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/book/book?id=${id}` })
  }
})
