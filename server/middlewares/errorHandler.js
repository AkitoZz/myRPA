const logger = require('../config/logger');

/**
 * 全局错误处理中间件
 * 捕获所有未处理的错误，记录日志并返回统一格式的错误响应
 */
const errorHandler = (err, req, res, _next) => {
  // 记录错误日志
  logger.error('Unhandled error', {
    error: err.message,
    stack: err.stack,
    method: req.method,
    url: req.originalUrl,
    ip: req.ip,
    userId: req.userId || null,
  });

  // Sequelize 校验错误
  if (err.name === 'SequelizeValidationError') {
    const messages = err.errors.map((e) => e.message);
    return res.status(400).json({
      success: false,
      data: null,
      message: '数据验证失败: ' + messages.join(', '),
    });
  }

  // Sequelize 唯一约束错误
  if (err.name === 'SequelizeUniqueConstraintError') {
    const fields = err.errors.map((e) => e.path);
    return res.status(409).json({
      success: false,
      data: null,
      message: '数据已存在: ' + fields.join(', '),
    });
  }

  // Sequelize 外键约束错误
  if (err.name === 'SequelizeForeignKeyConstraintError') {
    return res.status(400).json({
      success: false,
      data: null,
      message: '关联数据不存在或无法删除',
    });
  }

  // JWT 错误
  if (err.name === 'JsonWebTokenError') {
    return res.status(401).json({
      success: false,
      data: null,
      message: '认证令牌无效',
    });
  }

  if (err.name === 'TokenExpiredError') {
    return res.status(401).json({
      success: false,
      data: null,
      message: '认证令牌已过期',
    });
  }

  // 自定义业务错误（带有 statusCode 的错误）
  if (err.statusCode) {
    return res.status(err.statusCode).json({
      success: false,
      data: null,
      message: err.message,
    });
  }

  // 未知错误 - 生产环境不暴露错误细节
  const statusCode = err.statusCode || 500;
  const message =
    process.env.NODE_ENV === 'production' ? '服务器内部错误' : err.message || '服务器内部错误';

  res.status(statusCode).json({
    success: false,
    data: null,
    message,
  });
};

module.exports = errorHandler;
