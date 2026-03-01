import request from './request'

// 获取用户列表
export function getUsers(params) {
  return request({
    url: '/users',
    method: 'get',
    params
  })
}

// 获取单个用户
export function getUser(id) {
  return request({
    url: `/users/${id}`,
    method: 'get'
  })
}

// 更新用户
export function updateUser(id, data) {
  return request({
    url: `/users/${id}`,
    method: 'put',
    data
  })
}

// 删除用户
export function deleteUser(id) {
  return request({
    url: `/users/${id}`,
    method: 'delete'
  })
}
