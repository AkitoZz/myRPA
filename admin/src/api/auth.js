import request from './request'

// 登录
export function login(data) {
  return request({
    url: '/auth/login',
    method: 'post',
    data
  })
}

// 注册
export function register(data) {
  return request({
    url: '/auth/register',
    method: 'post',
    data
  })
}

// 刷新Token
export function refreshToken() {
  return request({
    url: '/auth/refresh-token',
    method: 'post'
  })
}
