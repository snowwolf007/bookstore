const { api } = require('../../utils/api')

Page({
  data: {
    book: null
  },

  onLoad(options) {
    if (options.id) {
      this.loadBook(options.id)
    }
  },

  async loadBook(id) {
    try {
      const book = await api.getBookDetail(id)
      if (book.cover_path) {
        book.coverUrl = 'http://localhost:8899/' + book.cover_path
      }
      this.setData({ book })
    } catch (err) {
      console.error(err)
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  addToCart() {
    const book = this.data.book
    if (!book) return
    let cart = wx.getStorageSync('cart') || []
    const existing = cart.find(item => item.id === book.id)
    if (existing) {
      existing.quantity += 1
    } else {
      cart.push({
        id: book.id,
        title: book.title_cn || book.title_en || book.title,
        cover_path: book.cover_path,
        price: book.price,
        quantity: 1
      })
    }
    wx.setStorageSync('cart', cart)
    wx.showToast({ title: '已加入购物车', icon: 'success' })
  },

  buyNow() {
    this.addToCart()
    wx.switchTab({ url: '/pages/cart/cart' })
  }
})
