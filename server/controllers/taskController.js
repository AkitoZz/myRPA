const taskService = require('../services/taskService');
const { OperationLog } = require('../models');

class TaskController {
  /**
   * 创建任务
   * POST /api/tasks
   */
  async create(req, res, next) {
    try {
      const task = await taskService.create(req.body, req.userId);

      await OperationLog.create({
        userId: req.userId,
        action: 'create_task',
        module: 'task',
        detail: { taskId: task.id, type: task.type, name: task.name },
        ip: req.ip,
      });

      res.status(201).json({
        success: true,
        data: task,
        message: '任务创建成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 获取任务列表
   * GET /api/tasks
   */
  async list(req, res, next) {
    try {
      const result = await taskService.list(req.query, req.userId, req.user.role);

      res.json({
        success: true,
        data: result,
        message: '获取任务列表成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 获取任务详情
   * GET /api/tasks/:id
   */
  async getById(req, res, next) {
    try {
      const taskId = parseInt(req.params.id, 10);
      const task = await taskService.getById(taskId, req.userId, req.user.role);

      res.json({
        success: true,
        data: task,
        message: '获取任务详情成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 更新任务
   * PUT /api/tasks/:id
   */
  async update(req, res, next) {
    try {
      const taskId = parseInt(req.params.id, 10);
      const task = await taskService.update(taskId, req.body, req.userId, req.user.role);

      await OperationLog.create({
        userId: req.userId,
        action: 'update_task',
        module: 'task',
        detail: { taskId, fields: Object.keys(req.body) },
        ip: req.ip,
      });

      res.json({
        success: true,
        data: task,
        message: '任务更新成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 删除任务
   * DELETE /api/tasks/:id
   */
  async delete(req, res, next) {
    try {
      const taskId = parseInt(req.params.id, 10);
      await taskService.delete(taskId, req.userId, req.user.role);

      await OperationLog.create({
        userId: req.userId,
        action: 'delete_task',
        module: 'task',
        detail: { taskId },
        ip: req.ip,
      });

      res.json({
        success: true,
        data: null,
        message: '任务删除成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 启动任务
   * POST /api/tasks/:id/start
   */
  async start(req, res, next) {
    try {
      const taskId = parseInt(req.params.id, 10);
      const task = await taskService.start(taskId, req.userId, req.user.role);

      await OperationLog.create({
        userId: req.userId,
        action: 'start_task',
        module: 'task',
        detail: { taskId },
        ip: req.ip,
      });

      res.json({
        success: true,
        data: task,
        message: '任务已启动',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 暂停任务
   * POST /api/tasks/:id/pause
   */
  async pause(req, res, next) {
    try {
      const taskId = parseInt(req.params.id, 10);
      const task = await taskService.pause(taskId, req.userId, req.user.role);

      await OperationLog.create({
        userId: req.userId,
        action: 'pause_task',
        module: 'task',
        detail: { taskId },
        ip: req.ip,
      });

      res.json({
        success: true,
        data: task,
        message: '任务已暂停',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 停止任务
   * POST /api/tasks/:id/stop
   */
  async stop(req, res, next) {
    try {
      const taskId = parseInt(req.params.id, 10);
      const task = await taskService.stop(taskId, req.userId, req.user.role);

      await OperationLog.create({
        userId: req.userId,
        action: 'stop_task',
        module: 'task',
        detail: { taskId },
        ip: req.ip,
      });

      res.json({
        success: true,
        data: task,
        message: '任务已停止',
      });
    } catch (error) {
      next(error);
    }
  }
}

module.exports = new TaskController();
