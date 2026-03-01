const { Device, User } = require('../models');
const { Op } = require('sequelize');

class DeviceService {
  /**
   * 注册设备（如已注册则更新信息）
   * @param {object} data - { deviceName, fingerprint, os, ip }
   * @param {number} userId - 用户ID
   * @returns {Promise<object>} 设备信息
   */
  async register(data, userId) {
    const { deviceName, fingerprint, os, ip } = data;

    // 查找是否已存在该指纹的设备
    let device = await Device.findOne({ where: { fingerprint } });

    if (device) {
      // 设备已注册，检查归属
      if (device.userId !== userId) {
        const error = new Error('该设备已被其他用户绑定');
        error.statusCode = 409;
        throw error;
      }

      // 更新设备信息
      await device.update({
        deviceName: deviceName || device.deviceName,
        os: os || device.os,
        ip: ip || device.ip,
        status: 'online',
        lastHeartbeat: new Date(),
      });
    } else {
      // 新设备注册
      device = await Device.create({
        userId,
        deviceName: deviceName || '未命名设备',
        fingerprint,
        os: os || '',
        ip: ip || '',
        status: 'online',
        lastHeartbeat: new Date(),
      });
    }

    return device;
  }

  /**
   * 设备心跳
   * @param {string} fingerprint - 设备指纹
   * @param {string} ip - 当前IP
   * @returns {Promise<object>} 更新后的设备
   */
  async heartbeat(fingerprint, ip) {
    const device = await Device.findOne({ where: { fingerprint } });
    if (!device) {
      const error = new Error('设备未注册');
      error.statusCode = 404;
      throw error;
    }

    if (device.status === 'banned') {
      const error = new Error('设备已被禁用');
      error.statusCode = 403;
      throw error;
    }

    await device.update({
      status: 'online',
      ip: ip || device.ip,
      lastHeartbeat: new Date(),
    });

    return device;
  }

  /**
   * 获取设备列表
   * @param {object} query - { page, pageSize, userId, status }
   * @param {number} userId - 当前用户ID（非管理员只能看自己的）
   * @param {string} role - 当前用户角色
   * @returns {Promise<object>}
   */
  async list(query, userId, role) {
    const { page = 1, pageSize = 20, status } = query;
    const offset = (page - 1) * pageSize;
    const where = {};

    // 非管理员只能查看自己的设备
    if (role !== 'admin') {
      where.userId = userId;
    } else if (query.userId) {
      where.userId = query.userId;
    }

    if (status) {
      where.status = status;
    }

    const { rows, count } = await Device.findAndCountAll({
      where,
      include: [
        {
          model: User,
          as: 'user',
          attributes: ['id', 'phone', 'nickname'],
        },
      ],
      order: [['lastHeartbeat', 'DESC']],
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
   * 删除设备
   * @param {number} deviceId - 设备ID
   * @param {number} userId - 当前用户ID
   * @param {string} role - 当前用户角色
   * @returns {Promise<void>}
   */
  async remove(deviceId, userId, role) {
    const device = await Device.findByPk(deviceId);
    if (!device) {
      const error = new Error('设备不存在');
      error.statusCode = 404;
      throw error;
    }

    // 非管理员只能删除自己的设备
    if (role !== 'admin' && device.userId !== userId) {
      const error = new Error('无权删除此设备');
      error.statusCode = 403;
      throw error;
    }

    await device.destroy();
  }

  /**
   * 将超时未心跳的设备设为离线
   * @param {number} timeoutMs - 超时毫秒数
   * @returns {Promise<number>} 更新的设备数量
   */
  async markOffline(timeoutMs = 60000) {
    const threshold = new Date(Date.now() - timeoutMs);
    const [affectedCount] = await Device.update(
      { status: 'offline' },
      {
        where: {
          status: 'online',
          lastHeartbeat: { [Op.lt]: threshold },
        },
      }
    );
    return affectedCount;
  }
}

module.exports = new DeviceService();
