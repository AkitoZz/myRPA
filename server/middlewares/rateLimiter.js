const rateLimit = require('express-rate-limit');

/**
 * 认证接口限流：每分钟最多5次请求
 * 防止暴力破解密码
 */
const authLimiter = rateLimit({
  windowMs: 60 * 1000, // 1分钟
  max: 5,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    data: null,
    message: '请求过于频繁，请1分钟后再试',
  },
  keyGenerator: (req) => {
    // 使用 IP + 路由 作为限流key
    return req.ip + ':' + req.path;
  },
});

/**
 * 通用API限流：每分钟最多100次请求
 */
const apiLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    data: null,
    message: 'API请求频率超限，请稍后再试',
  },
  keyGenerator: (req) => {
    return req.ip;
  },
});

module.exports = {
  authLimiter,
  apiLimiter,
};
