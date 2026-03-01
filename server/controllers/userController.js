const userService = require('../services/userService');
const { OperationLog } = require('../models');

class UserController {
  /**
   * 获取用户列表（管理员）
   * GET /api/users
   */
  async list(req, res, next) {
    try {
      const result = await userService.list(req.query);

      res.json({
        success: true,
        data: result,
        message: '获取用户列表成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 获取当前用户信息
   * GET /api/users/me
   */
  async getMe(req, res, next) {
    try {
      const user = await userService.getById(req.userId);

      res.json({
        success: true,
        data: user,
        message: '获取用户信息成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 获取指定用户信息
   * GET /api/users/:id
   */
  async getById(req, res, next) {
    try {
      const userId = parseInt(req.params.id, 10);
      const user = await userService.getById(userId);

      res.json({
        success: true,
        data: user,
        message: '获取用户信息成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 更新用户信息
   * PUT /api/users/:id
   */
  async update(req, res, next) {
    try {
      const userId = parseInt(req.params.id, 10);
      const result = await userService.update(userId, req.body, req.user);

      await OperationLog.create({
        userId: req.userId,
        action: 'update_user',
        module: 'user',
        detail: { targetUserId: userId, fields: Object.keys(req.body) },
        ip: req.ip,
      });

      res.json({
        success: true,
        data: result,
        message: '更新用户信息成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 删除用户（管理员）
   * DELETE /api/users/:id
   */
  async delete(req, res, next) {
    try {
      const userId = parseInt(req.params.id, 10);
      await userService.delete(userId);

      await OperationLog.create({
        userId: req.userId,
        action: 'delete_user',
        module: 'user',
        detail: { targetUserId: userId },
        ip: req.ip,
      });

      res.json({
        success: true,
        data: null,
        message: '删除用户成功',
      });
    } catch (error) {
      next(error);
    }
  }
}

module.exports = new UserController();
