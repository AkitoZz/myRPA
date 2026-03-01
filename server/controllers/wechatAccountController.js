const wechatAccountService = require('../services/wechatAccountService');
const { OperationLog } = require('../models');

class WechatAccountController {
  /**
   * 创建微信账号
   * POST /api/wechat-accounts
   */
  async create(req, res, next) {
    try {
      const account = await wechatAccountService.create(req.body, req.userId);

      await OperationLog.create({
        userId: req.userId,
        action: 'create_wechat_account',
        module: 'wechat_account',
        detail: { wxid: req.body.wxid },
        ip: req.ip,
      });

      res.status(201).json({
        success: true,
        data: account,
        message: '微信账号添加成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 获取微信账号列表
   * GET /api/wechat-accounts
   */
  async list(req, res, next) {
    try {
      const result = await wechatAccountService.list(req.query, req.userId, req.user.role);

      res.json({
        success: true,
        data: result,
        message: '获取微信账号列表成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 获取微信账号详情
   * GET /api/wechat-accounts/:id
   */
  async getById(req, res, next) {
    try {
      const accountId = parseInt(req.params.id, 10);
      const account = await wechatAccountService.getById(accountId, req.userId, req.user.role);

      res.json({
        success: true,
        data: account,
        message: '获取微信账号详情成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 更新微信账号
   * PUT /api/wechat-accounts/:id
   */
  async update(req, res, next) {
    try {
      const accountId = parseInt(req.params.id, 10);
      const account = await wechatAccountService.update(accountId, req.body, req.userId, req.user.role);

      await OperationLog.create({
        userId: req.userId,
        action: 'update_wechat_account',
        module: 'wechat_account',
        detail: { accountId, fields: Object.keys(req.body) },
        ip: req.ip,
      });

      res.json({
        success: true,
        data: account,
        message: '微信账号更新成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 删除微信账号
   * DELETE /api/wechat-accounts/:id
   */
  async delete(req, res, next) {
    try {
      const accountId = parseInt(req.params.id, 10);
      await wechatAccountService.delete(accountId, req.userId, req.user.role);

      await OperationLog.create({
        userId: req.userId,
        action: 'delete_wechat_account',
        module: 'wechat_account',
        detail: { accountId },
        ip: req.ip,
      });

      res.json({
        success: true,
        data: null,
        message: '微信账号删除成功',
      });
    } catch (error) {
      next(error);
    }
  }
}

module.exports = new WechatAccountController();
