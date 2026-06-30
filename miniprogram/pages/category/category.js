const { api } = require('../../utils/api')

Page({
  data: {
    categories: [],
    activeCat: 0,
    books: [],
    loading: true,
    page: 1
  },

  onLoad() {
    this.loadCategories()
  },

  async loadCategories() {
    try {
      const cats = await api.getCategories()
      const categories = (cats || []).map(c => ({ id: c.id, name: c.name, count: '' }))
      this.setData({ categories }, () => {
        if (categories.length > 0) this.selectCatByIndex(0)
      })
    } catch (err) {
      console.error(err)
      this.setData({ loading: false })
    }
  },

  selectCat(e) {
    const index = e.currentTarget.dataset.index
    this.selectCatByIndex(index)
  },

  async selectCatByIndex(index) {
    const cat = this.data.categories[index]
    if (!cat) return
    this.setData({ activeCat: index, loading: true, page: 1 })
    try {
      const res = await api.getBooksByCategory(cat.id, 1)
      const books = (res.items || res || []).map(b => ({
        ...b,
        coverUrl: b.cover_path ? 'http://localhost:8899/' + b.cover_path : ''
      }))
      this.setData({ books, loading: false })
    } catch (err) {
      console.error(err)
      this.setData({ loading: false })
    }
  },

  loadMore() {},

  toBook(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/book/book?id=${id}` })
  }
})
