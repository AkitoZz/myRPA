const authService = require('../services/authService');
const { OperationLog } = require('../models');

class AuthController {
  /**
   * 用户注册
   * POST /api/auth/register
   */
  async register(req, res, next) {
    try {
      const { phone, password, nickname } = req.body;
      const result = await authService.register({ phone, password, nickname });

      // 记录操作日志
      await OperationLog.create({
        userId: result.user.id,
        action: 'register',
        module: 'auth',
        detail: { phone },
        ip: req.ip,
      });

      res.status(201).json({
        success: true,
        data: result,
        message: '注册成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 用户登录
   * POST /api/auth/login
   */
  async login(req, res, next) {
    try {
      const { phone, password } = req.body;
      const result = await authService.login({ phone, password }, req.ip);

      // 记录操作日志
      await OperationLog.create({
        userId: result.user.id,
        action: 'login',
        module: 'auth',
        detail: { phone },
        ip: req.ip,
      });

      res.json({
        success: true,
        data: result,
        message: '登录成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 刷新令牌
   * POST /api/auth/refresh-token
   */
  async refreshToken(req, res, next) {
    try {
      const { refreshToken } = req.body;
      const result = await authService.refreshToken(refreshToken);

      res.json({
        success: true,
        data: result,
        message: '令牌刷新成功',
      });
    } catch (error) {
      next(error);
    }
  }
}

module.exports = new AuthController();
