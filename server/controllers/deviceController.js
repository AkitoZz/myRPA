const deviceService = require('../services/deviceService');
const { OperationLog } = require('../models');

class DeviceController {
  /**
   * 注册设备
   * POST /api/devices/register
   */
  async register(req, res, next) {
    try {
      const device = await deviceService.register(req.body, req.userId);

      await OperationLog.create({
        userId: req.userId,
        action: 'register_device',
        module: 'device',
        detail: { fingerprint: req.body.fingerprint, deviceName: req.body.deviceName },
        ip: req.ip,
      });

      res.status(201).json({
        success: true,
        data: device,
        message: '设备注册成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 设备心跳
   * POST /api/devices/heartbeat
   */
  async heartbeat(req, res, next) {
    try {
      const { fingerprint } = req.body;
      const device = await deviceService.heartbeat(fingerprint, req.ip);

      res.json({
        success: true,
        data: { deviceId: device.id, status: device.status },
        message: '心跳更新成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 获取设备列表
   * GET /api/devices
   */
  async list(req, res, next) {
    try {
      const result = await deviceService.list(req.query, req.userId, req.user.role);

      res.json({
        success: true,
        data: result,
        message: '获取设备列表成功',
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 删除设备
   * DELETE /api/devices/:id
   */
  async remove(req, res, next) {
    try {
      const deviceId = parseInt(req.params.id, 10);
      await deviceService.remove(deviceId, req.userId, req.user.role);

      await OperationLog.create({
        userId: req.userId,
        action: 'remove_device',
        module: 'device',
        detail: { deviceId },
        ip: req.ip,
      });

      res.json({
        success: true,
        data: null,
        message: '删除设备成功',
      });
    } catch (error) {
      next(error);
    }
  }
}

module.exports = new DeviceController();
