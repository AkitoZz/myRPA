import request from './request'

// 获取设备列表
export function getDevices(params) {
  return request({
    url: '/devices',
    method: 'get',
    params
  })
}

// 获取单个设备
export function getDevice(id) {
  return request({
    url: `/devices/${id}`,
    method: 'get'
  })
}

// 更新设备
export function updateDevice(id, data) {
  return request({
    url: `/devices/${id}`,
    method: 'put',
    data
  })
}

// 删除设备
export function deleteDevice(id) {
  return request({
    url: `/devices/${id}`,
    method: 'delete'
  })
}
