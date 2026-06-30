Page({
  data: {
    cart: [],
    totalPrice: 0
  },

  onShow() {
    this.loadCart()
  },

  loadCart() {
    const cart = wx.getStorageSync('cart') || []
    // 处理封面URL
    const items = cart.map(item => ({
      ...item,
      coverUrl: item.cover_path ? 'http://localhost:8899/' + item.cover_path : ''
    }))
    const totalPrice = items.reduce((sum, item) => sum + (item.price || 0) * item.quantity, 0)
    this.setData({ cart: items, totalPrice: totalPrice.toFixed(2) })
  },

  changeQty(e) {
    const { index, op } = e.currentTarget.dataset
    let cart = wx.getStorageSync('cart') || []
    if (op === 'plus') {
      cart[index].quantity += 1
    } else {
      cart[index].quantity -= 1
      if (cart[index].quantity <= 0) {
        cart.splice(index, 1)
      }
    }
    wx.setStorageSync('cart', cart)
    this.loadCart()
  },

  removeItem(e) {
    const { index } = e.currentTarget.dataset
    let cart = wx.getStorageSync('cart') || []
    cart.splice(index, 1)
    wx.setStorageSync('cart', cart)
    this.loadCart()
  },

  checkout() {
    wx.showToast({ title: '即将接入微信支付', icon: 'none' })
  },

  goHome() {
    wx.switchTab({ url: '/pages/index/index' })
  }
})
