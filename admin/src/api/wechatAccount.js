import request from './request'

// 获取微信账号列表
export function getAccounts(params) {
  return request({
    url: '/wechat-accounts',
    method: 'get',
    params
  })
}

// 创建微信账号
export function createAccount(data) {
  return request({
    url: '/wechat-accounts',
    method: 'post',
    data
  })
}

// 更新微信账号
export function updateAccount(id, data) {
  return request({
    url: `/wechat-accounts/${id}`,
    method: 'put',
    data
  })
}

// 删除微信账号
export function deleteAccount(id) {
  return request({
    url: `/wechat-accounts/${id}`,
    method: 'delete'
  })
}
