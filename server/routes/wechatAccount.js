const { Router } = require('express');
const Joi = require('joi');
const wechatAccountController = require('../controllers/wechatAccountController');
const auth = require('../middlewares/auth');
const validate = require('../middlewares/validator');

const router = Router();

// ========== 验证 Schema ==========

const createAccountSchema = Joi.object({
  wxid: Joi.string().max(100).required().messages({
    'any.required': '微信ID不能为空',
  }),
  nickname: Joi.string().max(100).optional().default(''),
  avatar: Joi.string().max(500).optional().default(''),
  deviceId: Joi.number().integer().optional(),
});

const updateAccountSchema = Joi.object({
  nickname: Joi.string().max(100).optional(),
  avatar: Joi.string().max(500).optional().allow(''),
  deviceId: Joi.number().integer().optional().allow(null),
  status: Joi.string().valid('online', 'offline', 'banned').optional(),
  todayAddFriend: Joi.number().integer().min(0).optional(),
  todayMassMsg: Joi.number().integer().min(0).optional(),
  todayAutoReply: Joi.number().integer().min(0).optional(),
}).min(1).messages({
  'object.min': '至少需要提供一个更新字段',
});

const listQuerySchema = Joi.object({
  page: Joi.number().integer().min(1).default(1),
  pageSize: Joi.number().integer().min(1).max(100).default(20),
  status: Joi.string().valid('online', 'offline', 'banned').optional(),
  userId: Joi.number().integer().optional(),
});

// ========== 路由定义 ==========

router.use(auth);

// 创建微信账号
router.post('/', validate(createAccountSchema), wechatAccountController.create);

// 获取微信账号列表
router.get('/', validate(listQuerySchema, 'query'), wechatAccountController.list);

// 获取微信账号详情
router.get('/:id', wechatAccountController.getById);

// 更新微信账号
router.put('/:id', validate(updateAccountSchema), wechatAccountController.update);

// 删除微信账号
router.delete('/:id', wechatAccountController.delete);

module.exports = router;
