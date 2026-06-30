Page({
  toOrders() {
    wx.showToast({ title: '订单功能即将上线', icon: 'none' })
  },
  toAddress() {
    wx.showToast({ title: '地址管理即将上线', icon: 'none' })
  },
  toFavorites() {
    wx.showToast({ title: '收藏功能即将上线', icon: 'none' })
  },
  about() {
    wx.showModal({
      title: '关于建筑书店',
      content: '厦门建筑书店，专注建筑、室内、景观设计类原版进口书刊。',
      showCancel: false
    })
  }
})
