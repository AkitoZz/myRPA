const jwt = require('jsonwebtoken');
const config = require('../config');
const { User } = require('../models');

/**
 * JWT 认证中间件
 * 从 Authorization header 中提取并验证 JWT token
 * 验证通过后将用户信息挂载到 req.user
 */
const auth = async (req, res, next) => {
  try {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({
        success: false,
        data: null,
        message: '未提供认证令牌',
      });
    }

    const token = authHeader.split(' ')[1];
    if (!token) {
      return res.status(401).json({
        success: false,
        data: null,
        message: '认证令牌格式错误',
      });
    }

    let decoded;
    try {
      decoded = jwt.verify(token, config.jwt.secret);
    } catch (err) {
      if (err.name === 'TokenExpiredError') {
        return res.status(401).json({
          success: false,
          data: null,
          message: '认证令牌已过期',
        });
      }
      return res.status(401).json({
        success: false,
        data: null,
        message: '认证令牌无效',
      });
    }

    // 查询用户是否存在且状态正常
    const user = await User.findByPk(decoded.userId, {
      attributes: { exclude: ['password'] },
    });

    if (!user) {
      return res.status(401).json({
        success: false,
        data: null,
        message: '用户不存在',
      });
    }

    if (user.status !== 'active') {
      return res.status(403).json({
        success: false,
        data: null,
        message: '账号已被禁用',
      });
    }

    // 将用户信息挂载到请求对象
    req.user = user;
    req.userId = user.id;

    next();
  } catch (error) {
    next(error);
  }
};

module.exports = auth;
