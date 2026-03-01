const { Router } = require('express');
const statsController = require('../controllers/statsController');
const auth = require('../middlewares/auth');

const router = Router();

router.use(auth);

// 获取仪表盘统计数据
router.get('/dashboard', statsController.dashboard);

module.exports = router;
