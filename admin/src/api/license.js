import request from './request'

// 获取授权码列表
export function getLicenses(params) {
  return request({
    url: '/licenses',
    method: 'get',
    params
  })
}

// 生成授权码
export function generateLicense(data) {
  return request({
    url: '/licenses/generate',
    method: 'post',
    data
  })
}

// 激活授权码
export function activateLicense(data) {
  return request({
    url: '/licenses/activate',
    method: 'post',
    data
  })
}

// 撤销授权码
export function revokeLicense(id) {
  return request({
    url: `/licenses/${id}/revoke`,
    method: 'post'
  })
}
