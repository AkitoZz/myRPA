const { v4: uuidv4 } = require('uuid');
const { License, User, Device } = require('../models');
const { Op } = require('sequelize');

// 各授权类型对应的天数
const LICENSE_DURATION = {
  trial: 7,
  monthly: 30,
  quarterly: 90,
  yearly: 365,
  lifetime: 36500, // ~100年
};

class LicenseService {
  /**
   * 批量生成授权码
   * @param {object} data - { type, count }
   * @returns {Promise<object[]>} 生成的授权码列表
   */
  async generate(data) {
    const { type, count = 1 } = data;
    const durationDays = LICENSE_DURATION[type] || 30;

    const licenses = [];
    for (let i = 0; i < count; i++) {
      // 生成格式化的授权码：XXXX-XXXX-XXXX-XXXX
      const raw = uuidv4().replace(/-/g, '').toUpperCase();
      const code = `${raw.slice(0, 4)}-${raw.slice(4, 8)}-${raw.slice(8, 12)}-${raw.slice(12, 16)}`;

      licenses.push({
        code,
        type,
        durationDays,
        status: 'unused',
      });
    }

    const created = await License.bulkCreate(licenses);
    return created;
  }

  /**
   * 激活授权码
   * @param {object} data - { code, deviceId }
   * @param {number} userId - 用户ID
   * @returns {Promise<object>} 激活结果
   */
  async activate(data, userId) {
    const { code, deviceId } = data;

    // 查找授权码
    const license = await License.findOne({ where: { code } });
    if (!license) {
      const error = new Error('授权码不存在');
      error.statusCode = 404;
      throw error;
    }

    if (license.status !== 'unused') {
      const statusMsg = {
        activated: '该授权码已被使用',
        expired: '该授权码已过期',
        revoked: '该授权码已被撤销',
      };
      const error = new Error(statusMsg[license.status] || '授权码状态异常');
      error.statusCode = 400;
      throw error;
    }

    // 验证设备存在且属于当前用户
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

    // 计算过期时间
    const now = new Date();
    const expireAt = new Date(now.getTime() + license.durationDays * 24 * 60 * 60 * 1000);

    // 激活授权码
    await license.update({
      userId,
      deviceId: deviceId || null,
      status: 'activated',
      activatedAt: now,
      expireAt,
    });

    // 根据授权类型升级用户会员等级
    const levelMap = {
      trial: 'basic',
      monthly: 'basic',
      quarterly: 'pro',
      yearly: 'pro',
      lifetime: 'enterprise',
    };

    const user = await User.findByPk(userId);
    const newLevel = levelMap[license.type] || 'basic';

    // 仅在新等级高于当前等级时升级
    const levelOrder = ['free', 'basic', 'pro', 'enterprise'];
    if (levelOrder.indexOf(newLevel) > levelOrder.indexOf(user.memberLevel)) {
      await user.update({
        memberLevel: newLevel,
        memberExpireAt: expireAt,
      });
    } else if (user.memberLevel === newLevel) {
      // 同等级续期：取较晚的过期时间
      const currentExpire = user.memberExpireAt ? new Date(user.memberExpireAt) : now;
      const newExpire = currentExpire > now
        ? new Date(currentExpire.getTime() + license.durationDays * 24 * 60 * 60 * 1000)
        : expireAt;
      await user.update({ memberExpireAt: newExpire });
    }

    return license;
  }

  /**
   * 验证授权码是否有效
   * @param {string} code - 授权码
   * @returns {Promise<object>} 验证结果
   */
  async validate(code) {
    const license = await License.findOne({
      where: { code },
      include: [
        { model: User, as: 'user', attributes: ['id', 'phone', 'nickname'] },
        { model: Device, as: 'device', attributes: ['id', 'deviceName', 'fingerprint'] },
      ],
    });

    if (!license) {
      const error = new Error('授权码不存在');
      error.statusCode = 404;
      throw error;
    }

    // 检查是否过期
    if (license.status === 'activated' && license.expireAt && new Date(license.expireAt) < new Date()) {
      await license.update({ status: 'expired' });
      license.status = 'expired';
    }

    return {
      valid: license.status === 'activated' && (!license.expireAt || new Date(license.expireAt) > new Date()),
      license,
    };
  }

  /**
   * 获取授权码列表
   * @param {object} query - { page, pageSize, status, type, userId }
   * @param {number} userId - 当前用户ID
   * @param {string} role - 当前用户角色
   * @returns {Promise<object>}
   */
  async list(query, userId, role) {
    const { page = 1, pageSize = 20, status, type } = query;
    const offset = (page - 1) * pageSize;
    const where = {};

    // 非管理员只能看自己的已激活授权码
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

    const { rows, count } = await License.findAndCountAll({
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
}

module.exports = new LicenseService();
