const statsService = require('../services/statsService');

class StatsController {
  /**
   * 获取仪表盘统计数据
   * GET /api/stats/dashboard
   */
  async dashboard(req, res, next) {
    try {
      const data = await statsService.getDashboard(req.userId, req.user.role);

      res.json({
        success: true,
        data,
        message: '获取统计数据成功',
      });
    } catch (error) {
      next(error);
    }
  }
}

module.exports = new StatsController();
