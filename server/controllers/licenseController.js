const licenseService = require('../services/licenseService');
const { OperationLog } = require('../models');

class LicenseController {
  /**
   * 生成授权码（管理员）
   * POST /api/licenses/generate
   */
  async generate(req, res, next) {
    try {
      const { type, count } = req.body;
      const licenses = await licenseService.generate({ type, count });

      await OperationLog.create({
        userId: req.userId,
        action: 'generate_license',
        module: 'license',
        detail: { type, count, codes: licenses.map((l) => l.code) },
        ip: req.ip,
      });

      res.status(201).json({
        success: true,
        data: licenses,
        message: `成功生成${licenses.length}个授权码`,
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 激活授权码
   * POST /api/licenses/activate
   */
  async activate(req, res, next) {
    try {
      const { code, deviceId } = req.body;
      const license = await licenseService.activate({ code, deviceId }, req.userId);

      await OperationLog.create({
        userId: req.userId,
        action: 'activate_license',
        module: 'license',
        detail: { code, deviceId },
        ip: req.ip,
      });

      res.json({
        success: true,
        data: license,
        message: '授权码激活成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 获取授权码列表
   * GET /api/licenses
   */
  async list(req, res, next) {
    try {
      const result = await licenseService.list(req.query, req.userId, req.user.role);

      res.json({
        success: true,
        data: result,
        message: '获取授权码列表成功',
      });
    } catch (error) {
      next(error);
    }
  }
}

module.exports = new LicenseController();
