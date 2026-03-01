/**
 * 角色权限校验中间件
 * 需要在 auth 中间件之后使用，依赖 req.user
 * @param {string[]} allowedRoles - 允许的角色数组，如 ['admin', 'agent']
 * @returns {Function} Express 中间件
 */
const role = (allowedRoles) => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        data: null,
        message: '请先登录',
      });
    }

    if (!allowedRoles.includes(req.user.role)) {
      return res.status(403).json({
        success: false,
        data: null,
        message: '权限不足，无法执行此操作',
      });
    }

    next();
  };
};

module.exports = role;
