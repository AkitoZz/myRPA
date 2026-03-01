const { Router } = require('express');
const Joi = require('joi');
const taskController = require('../controllers/taskController');
const auth = require('../middlewares/auth');
const validate = require('../middlewares/validator');

const router = Router();

// ========== 验证 Schema ==========

const createTaskSchema = Joi.object({
  type: Joi.string()
    .valid('add_friend', 'mass_message', 'auto_reply', 'group_manage')
    .required()
    .messages({
      'any.required': '任务类型不能为空',
      'any.only': '任务类型无效',
    }),
  name: Joi.string().max(200).required().messages({
    'any.required': '任务名称不能为空',
  }),
  deviceId: Joi.number().integer().optional(),
  wechatAccountId: Joi.number().integer().optional(),
  config: Joi.object().optional().default({}),
  total: Joi.number().integer().min(0).optional().default(0),
  scheduleType: Joi.string()
    .valid('immediate', 'scheduled', 'recurring')
    .optional()
    .default('immediate'),
  scheduledAt: Joi.date().optional().allow(null),
  cronExpression: Joi.string().max(100).optional().allow(null, ''),
});

const updateTaskSchema = Joi.object({
  name: Joi.string().max(200).optional(),
  deviceId: Joi.number().integer().optional().allow(null),
  wechatAccountId: Joi.number().integer().optional().allow(null),
  config: Joi.object().optional(),
  total: Joi.number().integer().min(0).optional(),
  scheduleType: Joi.string().valid('immediate', 'scheduled', 'recurring').optional(),
  scheduledAt: Joi.date().optional().allow(null),
  cronExpression: Joi.string().max(100).optional().allow(null, ''),
}).min(1).messages({
  'object.min': '至少需要提供一个更新字段',
});

const listQuerySchema = Joi.object({
  page: Joi.number().integer().min(1).default(1),
  pageSize: Joi.number().integer().min(1).max(100).default(20),
  status: Joi.string().valid('pending', 'running', 'paused', 'completed', 'failed').optional(),
  type: Joi.string().valid('add_friend', 'mass_message', 'auto_reply', 'group_manage').optional(),
  userId: Joi.number().integer().optional(),
});

// ========== 路由定义 ==========

router.use(auth);

// 创建任务
router.post('/', validate(createTaskSchema), taskController.create);

// 获取任务列表
router.get('/', validate(listQuerySchema, 'query'), taskController.list);

// 获取任务详情
router.get('/:id', taskController.getById);

// 更新任务
router.put('/:id', validate(updateTaskSchema), taskController.update);

// 删除任务
router.delete('/:id', taskController.delete);

// 启动任务
router.post('/:id/start', taskController.start);

// 暂停任务
router.post('/:id/pause', taskController.pause);

// 停止任务
router.post('/:id/stop', taskController.stop);

module.exports = router;
