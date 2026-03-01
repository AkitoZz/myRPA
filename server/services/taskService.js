const { Task, TaskLog, Device, WechatAccount, User } = require('../models');
const { Op } = require('sequelize');

class TaskService {
  /**
   * 创建任务
   * @param {object} data - 任务数据
   * @param {number} userId - 用户ID
   * @returns {Promise<object>} 创建的任务
   */
  async create(data, userId) {
    const { deviceId, wechatAccountId, type, name, config, scheduleType, scheduledAt, cronExpression, total } = data;

    // 验证设备归属
    if (deviceId) {
      const device = await Device.findByPk(deviceId);
      if (!device) {
        const error = new Error('设备不存在');
        error.statusCode = 404;
        throw error;
      }
      if (device.userId !== userId) {
        const error = new Error('该设备不属于当前用户');
        error.statusCode = 403;
        throw error;
      }
    }

    // 验证微信账号归属
    if (wechatAccountId) {
      const wxAccount = await WechatAccount.findByPk(wechatAccountId);
      if (!wxAccount) {
        const error = new Error('微信账号不存在');
        error.statusCode = 404;
        throw error;
      }
      if (wxAccount.userId !== userId) {
        const error = new Error('该微信账号不属于当前用户');
        error.statusCode = 403;
        throw error;
      }
    }

    const task = await Task.create({
      userId,
      deviceId: deviceId || null,
      wechatAccountId: wechatAccountId || null,
      type,
      name,
      config: config || {},
      status: 'pending',
      progress: 0,
      total: total || 0,
      scheduleType: scheduleType || 'immediate',
      scheduledAt: scheduledAt || null,
      cronExpression: cronExpression || null,
    });

    return task;
  }

  /**
   * 获取任务列表
   * @param {object} query - { page, pageSize, status, type, userId }
   * @param {number} userId - 当前用户ID
   * @param {string} role - 当前用户角色
   * @returns {Promise<object>}
   */
  async list(query, userId, role) {
    const { page = 1, pageSize = 20, status, type } = query;
    const offset = (page - 1) * pageSize;
    const where = {};

    if (role !== 'admin') {
      where.userId = userId;
    } else if (query.userId) {
      where.userId = query.userId;
    }

    if (status) {
      where.status = status;
    }

    if (type) {
      where.type = type;
    }

    const { rows, count } = await Task.findAndCountAll({
      where,
      include: [
        { model: User, as: 'user', attributes: ['id', 'phone', 'nickname'] },
        { model: Device, as: 'device', attributes: ['id', 'deviceName'] },
        { model: WechatAccount, as: 'wechatAccount', attributes: ['id', 'wxid', 'nickname'] },
      ],
      order: [['createdAt', 'DESC']],
      offset,
      limit: parseInt(pageSize, 10),
    });

    return {
      list: rows,
      total: count,
      page: parseInt(page, 10),
      pageSize: parseInt(pageSize, 10),
    };
  }

  /**
   * 获取任务详情
   * @param {number} taskId - 任务ID
   * @param {number} userId - 当前用户ID
   * @param {string} role - 当前用户角色
   * @returns {Promise<object>}
   */
  async getById(taskId, userId, role) {
    const task = await Task.findByPk(taskId, {
      include: [
        { model: User, as: 'user', attributes: ['id', 'phone', 'nickname'] },
        { model: Device, as: 'device', attributes: ['id', 'deviceName'] },
        { model: WechatAccount, as: 'wechatAccount', attributes: ['id', 'wxid', 'nickname'] },
        {
          model: TaskLog,
          as: 'logs',
          order: [['createdAt', 'DESC']],
          limit: 50,
        },
      ],
    });

    if (!task) {
      const error = new Error('任务不存在');
      error.statusCode = 404;
      throw error;
    }

    if (role !== 'admin' && task.userId !== userId) {
      const error = new Error('无权查看此任务');
      error.statusCode = 403;
      throw error;
    }

    return task;
  }

  /**
   * 更新任务
   * @param {number} taskId - 任务ID
   * @param {object} data - 更新数据
   * @param {number} userId - 当前用户ID
   * @param {string} role - 当前用户角色
   * @returns {Promise<object>}
   */
  async update(taskId, data, userId, role) {
    const task = await Task.findByPk(taskId);
    if (!task) {
      const error = new Error('任务不存在');
      error.statusCode = 404;
      throw error;
    }

    if (role !== 'admin' && task.userId !== userId) {
      const error = new Error('无权修改此任务');
      error.statusCode = 403;
      throw error;
    }

    // 运行中的任务不能修改配置
    if (task.status === 'running') {
      const error = new Error('运行中的任务不能修改');
      error.statusCode = 400;
      throw error;
    }

    const updateData = {};
    if (data.name !== undefined) updateData.name = data.name;
    if (data.config !== undefined) updateData.config = data.config;
    if (data.deviceId !== undefined) updateData.deviceId = data.deviceId;
    if (data.wechatAccountId !== undefined) updateData.wechatAccountId = data.wechatAccountId;
    if (data.scheduleType !== undefined) updateData.scheduleType = data.scheduleType;
    if (data.scheduledAt !== undefined) updateData.scheduledAt = data.scheduledAt;
    if (data.cronExpression !== undefined) updateData.cronExpression = data.cronExpression;
    if (data.total !== undefined) updateData.total = data.total;

    await task.update(updateData);
    return task;
  }

  /**
   * 删除任务
   * @param {number} taskId - 任务ID
   * @param {number} userId - 当前用户ID
   * @param {string} role - 当前用户角色
   * @returns {Promise<void>}
   */
  async delete(taskId, userId, role) {
    const task = await Task.findByPk(taskId);
    if (!task) {
      const error = new Error('任务不存在');
      error.statusCode = 404;
      throw error;
    }

    if (role !== 'admin' && task.userId !== userId) {
      const error = new Error('无权删除此任务');
      error.statusCode = 403;
      throw error;
    }

    if (task.status === 'running') {
      const error = new Error('运行中的任务不能删除，请先停止');
      error.statusCode = 400;
      throw error;
    }

    // 同时删除关联的任务日志
    await TaskLog.destroy({ where: { taskId } });
    await task.destroy();
  }

  /**
   * 启动任务
   * @param {number} taskId - 任务ID
   * @param {number} userId - 当前用户ID
   * @param {string} role - 当前用户角色
   * @returns {Promise<object>}
   */
  async start(taskId, userId, role) {
    const task = await Task.findByPk(taskId);
    if (!task) {
      const error = new Error('任务不存在');
      error.statusCode = 404;
      throw error;
    }

    if (role !== 'admin' && task.userId !== userId) {
      const error = new Error('无权操作此任务');
      error.statusCode = 403;
      throw error;
    }

    if (!['pending', 'paused', 'failed'].includes(task.status)) {
      const error = new Error(`当前状态(${task.status})不允许启动`);
      error.statusCode = 400;
      throw error;
    }

    await task.update({
      status: 'running',
      errorMsg: null,
    });

    // 记录任务日志
    await TaskLog.create({
      taskId,
      action: 'start',
      target: '',
      result: 'success',
      detail: { operator: userId },
    });

    return task;
  }

  /**
   * 暂停任务
   * @param {number} taskId - 任务ID
   * @param {number} userId - 当前用户ID
   * @param {string} role - 当前用户角色
   * @returns {Promise<object>}
   */
  async pause(taskId, userId, role) {
    const task = await Task.findByPk(taskId);
    if (!task) {
      const error = new Error('任务不存在');
      error.statusCode = 404;
      throw error;
    }

    if (role !== 'admin' && task.userId !== userId) {
      const error = new Error('无权操作此任务');
      error.statusCode = 403;
      throw error;
    }

    if (task.status !== 'running') {
      const error = new Error('只有运行中的任务可以暂停');
      error.statusCode = 400;
      throw error;
    }

    await task.update({ status: 'paused' });

    await TaskLog.create({
      taskId,
      action: 'pause',
      target: '',
      result: 'success',
      detail: { operator: userId },
    });

    return task;
  }

  /**
   * 停止任务
   * @param {number} taskId - 任务ID
   * @param {number} userId - 当前用户ID
   * @param {string} role - 当前用户角色
   * @returns {Promise<object>}
   */
  async stop(taskId, userId, role) {
    const task = await Task.findByPk(taskId);
    if (!task) {
      const error = new Error('任务不存在');
      error.statusCode = 404;
      throw error;
    }

    if (role !== 'admin' && task.userId !== userId) {
      const error = new Error('无权操作此任务');
      error.statusCode = 403;
      throw error;
    }

    if (!['running', 'paused'].includes(task.status)) {
      const error = new Error('当前状态不允许停止');
      error.statusCode = 400;
      throw error;
    }

    await task.update({ status: 'completed' });

    await TaskLog.create({
      taskId,
      action: 'stop',
      target: '',
      result: 'success',
      detail: { operator: userId, progress: task.progress, total: task.total },
    });

    return task;
  }

  /**
   * 更新任务进度（通常由设备端通过 WebSocket 上报）
   * @param {number} taskId - 任务ID
   * @param {object} data - { progress, total, result, errorMsg, status }
   * @returns {Promise<object>}
   */
  async updateProgress(taskId, data) {
    const task = await Task.findByPk(taskId);
    if (!task) {
      const error = new Error('任务不存在');
      error.statusCode = 404;
      throw error;
    }

    const updateData = {};
    if (data.progress !== undefined) updateData.progress = data.progress;
    if (data.total !== undefined) updateData.total = data.total;
    if (data.result !== undefined) updateData.result = data.result;
    if (data.errorMsg !== undefined) updateData.errorMsg = data.errorMsg;
    if (data.status !== undefined) updateData.status = data.status;

    await task.update(updateData);
    return task;
  }
}

module.exports = new TaskService();
