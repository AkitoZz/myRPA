const { Router } = require('express');
const Joi = require('joi');
const licenseController = require('../controllers/licenseController');
const auth = require('../middlewares/auth');
const role = require('../middlewares/role');
const validate = require('../middlewares/validator');

const router = Router();

// ========== 验证 Schema ==========

const generateSchema = Joi.object({
  type: Joi.string()
    .valid('trial', 'monthly', 'quarterly', 'yearly', 'lifetime')
    .required()
    .messages({
      'any.required': '授权类型不能为空',
      'any.only': '授权类型无效',
    }),
  count: Joi.number().integer().min(1).max(100).default(1).messages({
    'number.min': '生成数量不能小于1',
    'number.max': '单次最多生成100个',
  }),
});

const activateSchema = Joi.object({
  code: Joi.string().required().messages({
    'any.required': '授权码不能为空',
  }),
  deviceId: Joi.number().integer().optional(),
});

const listQuerySchema = Joi.object({
  page: Joi.number().integer().min(1).default(1),
  pageSize: Joi.number().integer().min(1).max(100).default(20),
  status: Joi.string().valid('unused', 'activated', 'expired', 'revoked').optional(),
  type: Joi.string().valid('trial', 'monthly', 'quarterly', 'yearly', 'lifetime').optional(),
  userId: Joi.number().integer().optional(),
});

// ========== 路由定义 ==========

router.use(auth);

// 生成授权码（管理员专用）
router.post('/generate', role(['admin']), validate(generateSchema), licenseController.generate);

// 激活授权码
router.post('/activate', validate(activateSchema), licenseController.activate);

// 获取授权码列表
router.get('/', validate(listQuerySchema, 'query'), licenseController.list);

module.exports = router;
