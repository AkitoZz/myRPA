import request from './request'

// 获取任务列表
export function getTasks(params) {
  return request({
    url: '/tasks',
    method: 'get',
    params
  })
}

// 获取单个任务
export function getTask(id) {
  return request({
    url: `/tasks/${id}`,
    method: 'get'
  })
}

// 创建任务
export function createTask(data) {
  return request({
    url: '/tasks',
    method: 'post',
    data
  })
}

// 更新任务
export function updateTask(id, data) {
  return request({
    url: `/tasks/${id}`,
    method: 'put',
    data
  })
}

// 删除任务
export function deleteTask(id) {
  return request({
    url: `/tasks/${id}`,
    method: 'delete'
  })
}

// 启动任务
export function startTask(id) {
  return request({
    url: `/tasks/${id}/start`,
    method: 'post'
  })
}

// 暂停任务
export function pauseTask(id) {
  return request({
    url: `/tasks/${id}/pause`,
    method: 'post'
  })
}

// 停止任务
export function stopTask(id) {
  return request({
    url: `/tasks/${id}/stop`,
    method: 'post'
  })
}
