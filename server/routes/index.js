const { Router } = require('express');
const authRoutes = require('./auth');
const userRoutes = require('./user');
const deviceRoutes = require('./device');
const licenseRoutes = require('./license');
const taskRoutes = require('./task');
const statsRoutes = require('./stats');
const wechatAccountRoutes = require('./wechatAccount');
const { apiLimiter } = require('../middlewares/rateLimiter');

const router = Router();

// 所有 API 接口应用通用限流
router.use(apiLimiter);

// 挂载各模块路由
router.use('/auth', authRoutes);
router.use('/users', userRoutes);
router.use('/devices', deviceRoutes);
router.use('/licenses', licenseRoutes);
router.use('/tasks', taskRoutes);
router.use('/stats', statsRoutes);
router.use('/wechat-accounts', wechatAccountRoutes);

module.exports = router;
