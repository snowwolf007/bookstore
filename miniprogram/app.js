App({
  onLaunch() {
    // 检查网络可用性
    wx.getNetworkType({
      success: res => {
        this.globalData.networkType = res.networkType
      }
    })
  },
  globalData: {
    networkType: 'wifi'
  }
})
