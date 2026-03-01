const { Router } = require('express');
const Joi = require('joi');
const deviceController = require('../controllers/deviceController');
const auth = require('../middlewares/auth');
const validate = require('../middlewares/validator');

const router = Router();

// ========== 验证 Schema ==========

const registerDeviceSchema = Joi.object({
  deviceName: Joi.string().max(100).optional().default(''),
  fingerprint: Joi.string().max(255).required().messages({
    'any.required': '设备指纹不能为空',
  }),
  os: Joi.string().max(50).optional().default(''),
  ip: Joi.string().max(45).optional().default(''),
});

const heartbeatSchema = Joi.object({
  fingerprint: Joi.string().max(255).required().messages({
    'any.required': '设备指纹不能为空',
  }),
});

const listQuerySchema = Joi.object({
  page: Joi.number().integer().min(1).default(1),
  pageSize: Joi.number().integer().min(1).max(100).default(20),
  userId: Joi.number().integer().optional(),
  status: Joi.string().valid('online', 'offline', 'banned').optional(),
});

// ========== 路由定义 ==========

router.use(auth);

// 注册设备
router.post('/register', validate(registerDeviceSchema), deviceController.register);

// 设备心跳
router.post('/heartbeat', validate(heartbeatSchema), deviceController.heartbeat);

// 获取设备列表
router.get('/', validate(listQuerySchema, 'query'), deviceController.list);

// 删除设备
router.delete('/:id', deviceController.remove);

module.exports = router;
