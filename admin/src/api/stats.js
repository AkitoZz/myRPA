import request from './request'

// 获取仪表盘统计数据
export function getDashboardStats() {
  return request({
    url: '/stats/dashboard',
    method: 'get'
  })
}
