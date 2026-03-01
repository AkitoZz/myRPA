const { WechatAccount, User, Device } = require('../models');
const { Op } = require('sequelize');

class WechatAccountService {
  /**
   * 创建微信账号
   * @param {object} data - { wxid, nickname, avatar, deviceId }
   * @param {number} userId - 用户ID
   * @returns {Promise<object>}
   */
  async create(data, userId) {
    const { wxid, nickname, avatar, deviceId } = data;

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

    // 检查微信号是否已被当前用户添加过
    const existing = await WechatAccount.findOne({
      where: { userId, wxid },
    });
    if (existing) {
      const error = new Error('该微信账号已存在');
      error.statusCode = 409;
      throw error;
    }

    const account = await WechatAccount.create({
      userId,
      deviceId: deviceId || null,
      wxid,
      nickname: nickname || '',
      avatar: avatar || '',
      status: 'offline',
      todayAddFriend: 0,
      todayMassMsg: 0,
      todayAutoReply: 0,
    });

    return account;
  }

  /**
   * 获取微信账号列表
   * @param {object} query - { page, pageSize, status }
   * @param {number} userId - 当前用户ID
   * @param {string} role - 当前用户角色
   * @returns {Promise<object>}
   */
  async list(query, userId, role) {
    const { page = 1, pageSize = 20, status } = query;
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

    const { rows, count } = await WechatAccount.findAndCountAll({
      where,
      include: [
        { model: User, as: 'user', attributes: ['id', 'phone', 'nickname'] },
        { model: Device, as: 'device', attributes: ['id', 'deviceName'] },
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
   * 获取微信账号详情
   * @param {number} accountId - 账号ID
   * @param {number} userId - 当前用户ID
   * @param {string} role - 当前用户角色
   * @returns {Promise<object>}
   */
  async getById(accountId, userId, role) {
    const account = await WechatAccount.findByPk(accountId, {
      include: [
        { model: User, as: 'user', attributes: ['id', 'phone', 'nickname'] },
        { model: Device, as: 'device', attributes: ['id', 'deviceName'] },
      ],
    });

    if (!account) {
      const error = new Error('微信账号不存在');
      error.statusCode = 404;
      throw error;
    }

    if (role !== 'admin' && account.userId !== userId) {
      const error = new Error('无权查看此微信账号');
      error.statusCode = 403;
      throw error;
    }

    return account;
  }

  /**
   * 更新微信账号
   * @param {number} accountId - 账号ID
   * @param {object} data - 更新数据
   * @param {number} userId - 当前用户ID
   * @param {string} role - 当前用户角色
   * @returns {Promise<object>}
   */
  async update(accountId, data, userId, role) {
    const account = await WechatAccount.findByPk(accountId);
    if (!account) {
      const error = new Error('微信账号不存在');
      error.statusCode = 404;
      throw error;
    }

    if (role !== 'admin' && account.userId !== userId) {
      const error = new Error('无权修改此微信账号');
      error.statusCode = 403;
      throw error;
    }

    const updateData = {};
    if (data.nickname !== undefined) updateData.nickname = data.nickname;
    if (data.avatar !== undefined) updateData.avatar = data.avatar;
    if (data.deviceId !== undefined) updateData.deviceId = data.deviceId;
    if (data.status !== undefined) updateData.status = data.status;
    if (data.todayAddFriend !== undefined) updateData.todayAddFriend = data.todayAddFriend;
    if (data.todayMassMsg !== undefined) updateData.todayMassMsg = data.todayMassMsg;
    if (data.todayAutoReply !== undefined) updateData.todayAutoReply = data.todayAutoReply;

    await account.update(updateData);
    return account;
  }

  /**
   * 删除微信账号
   * @param {number} accountId - 账号ID
   * @param {number} userId - 当前用户ID
   * @param {string} role - 当前用户角色
   * @returns {Promise<void>}
   */
  async delete(accountId, userId, role) {
    const account = await WechatAccount.findByPk(accountId);
    if (!account) {
      const error = new Error('微信账号不存在');
      error.statusCode = 404;
      throw error;
    }

    if (role !== 'admin' && account.userId !== userId) {
      const error = new Error('无权删除此微信账号');
      error.statusCode = 403;
      throw error;
    }

    await account.destroy();
  }
}

module.exports = new WechatAccountService();
