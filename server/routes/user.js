const { Router } = require('express');
const Joi = require('joi');
const userController = require('../controllers/userController');
const auth = require('../middlewares/auth');
const role = require('../middlewares/role');
const validate = require('../middlewares/validator');

const router = Router();

// ========== 验证 Schema ==========

const updateUserSchema = Joi.object({
  nickname: Joi.string().max(50).optional(),
  avatar: Joi.string().max(500).optional().allow(''),
  password: Joi.string().min(6).max(50).optional(),
  role: Joi.string().valid('admin', 'agent', 'user').optional(),
  memberLevel: Joi.string().valid('free', 'basic', 'pro', 'enterprise').optional(),
  memberExpireAt: Joi.date().optional().allow(null),
  status: Joi.string().valid('active', 'disabled', 'banned').optional(),
}).min(1).messages({
  'object.min': '至少需要提供一个更新字段',
});

const listQuerySchema = Joi.object({
  page: Joi.number().integer().min(1).default(1),
  pageSize: Joi.number().integer().min(1).max(100).default(20),
  keyword: Joi.string().max(50).optional().allow(''),
  role: Joi.string().valid('admin', 'agent', 'user').optional(),
  status: Joi.string().valid('active', 'disabled', 'banned').optional(),
});

// ========== 路由定义 ==========

// 所有路由需要认证
router.use(auth);

// 获取当前用户信息
router.get('/me', userController.getMe);

// 获取用户列表（管理员专用）
router.get('/', role(['admin']), validate(listQuerySchema, 'query'), userController.list);

// 获取指定用户信息（管理员或本人）
router.get('/:id', userController.getById);

// 更新用户信息
router.put('/:id', validate(updateUserSchema), userController.update);

// 删除用户（管理员专用）
router.delete('/:id', role(['admin']), userController.delete);

module.exports = router;
