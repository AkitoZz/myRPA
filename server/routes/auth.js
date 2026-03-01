const { Router } = require('express');
const Joi = require('joi');
const authController = require('../controllers/authController');
const validate = require('../middlewares/validator');
const { authLimiter } = require('../middlewares/rateLimiter');

const router = Router();

// ========== 验证 Schema ==========

const registerSchema = Joi.object({
  phone: Joi.string()
    .pattern(/^1[3-9]\d{9}$/)
    .required()
    .messages({
      'string.pattern.base': '手机号格式不正确',
      'any.required': '手机号不能为空',
    }),
  password: Joi.string().min(6).max(50).required().messages({
    'string.min': '密码长度不能少于6位',
    'string.max': '密码长度不能超过50位',
    'any.required': '密码不能为空',
  }),
  nickname: Joi.string().max(50).optional().allow(''),
});

const loginSchema = Joi.object({
  phone: Joi.string()
    .pattern(/^1[3-9]\d{9}$/)
    .required()
    .messages({
      'string.pattern.base': '手机号格式不正确',
      'any.required': '手机号不能为空',
    }),
  password: Joi.string().required().messages({
    'any.required': '密码不能为空',
  }),
});

const refreshTokenSchema = Joi.object({
  refreshToken: Joi.string().required().messages({
    'any.required': '刷新令牌不能为空',
  }),
});

// ========== 路由定义 ==========

// 注册
router.post('/register', authLimiter, validate(registerSchema), authController.register);

// 登录
router.post('/login', authLimiter, validate(loginSchema), authController.login);

// 刷新令牌
router.post('/refresh-token', validate(refreshTokenSchema), authController.refreshToken);

module.exports = router;
