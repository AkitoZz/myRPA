const { User } = require('../models');
const { Op } = require('sequelize');
const authService = require('./authService');

class UserService {
  /**
   * 获取用户列表（支持分页和搜索）
   * @param {object} query - { page, pageSize, keyword, role, status }
   * @returns {Promise<object>} { rows, count, page, pageSize }
   */
  async list(query) {
    const { page = 1, pageSize = 20, keyword, role, status } = query;
    const offset = (page - 1) * pageSize;
    const where = {};

    if (keyword) {
      where[Op.or] = [
        { phone: { [Op.like]: `%${keyword}%` } },
        { nickname: { [Op.like]: `%${keyword}%` } },
      ];
    }

    if (role) {
      where.role = role;
    }

    if (status) {
      where.status = status;
    }

    const { rows, count } = await User.findAndCountAll({
      where,
      attributes: { exclude: ['password'] },
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
   * 获取单个用户详情
   * @param {number} userId - 用户ID
   * @returns {Promise<object>} 用户信息
   */
  async getById(userId) {
    const user = await User.findByPk(userId, {
      attributes: { exclude: ['password'] },
    });

    if (!user) {
      const error = new Error('用户不存在');
      error.statusCode = 404;
      throw error;
    }

    return user;
  }

  /**
   * 更新用户信息
   * @param {number} userId - 用户ID
   * @param {object} data - 更新数据
   * @param {object} operator - 操作者信息
   * @returns {Promise<object>} 更新后的用户
   */
  async update(userId, data, operator) {
    const user = await User.findByPk(userId);
    if (!user) {
      const error = new Error('用户不存在');
      error.statusCode = 404;
      throw error;
    }

    const updateData = {};

    // 普通用户只能修改自己的昵称和头像
    if (operator.role !== 'admin') {
      if (operator.id !== userId) {
        const error = new Error('无权修改其他用户信息');
        error.statusCode = 403;
        throw error;
      }
      if (data.nickname !== undefined) updateData.nickname = data.nickname;
      if (data.avatar !== undefined) updateData.avatar = data.avatar;
      if (data.password) {
        updateData.password = await authService.hashPassword(data.password);
      }
    } else {
      // 管理员可修改更多字段
      if (data.nickname !== undefined) updateData.nickname = data.nickname;
      if (data.avatar !== undefined) updateData.avatar = data.avatar;
      if (data.role !== undefined) updateData.role = data.role;
      if (data.memberLevel !== undefined) updateData.memberLevel = data.memberLevel;
      if (data.memberExpireAt !== undefined) updateData.memberExpireAt = data.memberExpireAt;
      if (data.status !== undefined) updateData.status = data.status;
      if (data.password) {
        updateData.password = await authService.hashPassword(data.password);
      }
    }

    await user.update(updateData);

    // 返回不含密码的用户信息
    const result = user.toJSON();
    delete result.password;
    return result;
  }

  /**
   * 删除用户（软禁用）
   * @param {number} userId - 用户ID
   * @returns {Promise<void>}
   */
  async delete(userId) {
    const user = await User.findByPk(userId);
    if (!user) {
      const error = new Error('用户不存在');
      error.statusCode = 404;
      throw error;
    }

    if (user.role === 'admin') {
      const error = new Error('不能删除管理员账号');
      error.statusCode = 403;
      throw error;
    }

    // 将状态设为 banned 作为逻辑删除
    await user.update({ status: 'banned' });
  }
}

module.exports = new UserService();
