const WebSocket = require('ws');
const jwt = require('jsonwebtoken');
const url = require('url');
const config = require('../config');
const logger = require('../config/logger');
const { Device } = require('../models');
const taskService = require('../services/taskService');

// 已连接的客户端 Map: deviceId => { ws, userId, deviceId, fingerprint, lastPong }
const clients = new Map();

/**
 * 初始化 WebSocket 服务
 * @param {import('http').Server} server - HTTP 服务器实例
 */
function initWebSocket(server) {
  const wss = new WebSocket.Server({
    server,
    path: '/ws',
    // 连接时进行身份验证
    verifyClient: async (info, callback) => {
      try {
        const parsedUrl = url.parse(info.req.url, true);
        const token = parsedUrl.query.token;

        if (!token) {
          callback(false, 401, '未提供认证令牌');
          return;
        }

        const decoded = jwt.verify(token, config.jwt.secret);
        // 将用户信息附加到请求对象上
        info.req.userId = decoded.userId;
        info.req.role = decoded.role;
        callback(true);
      } catch (err) {
        logger.warn('WebSocket 认证失败', { error: err.message });
        callback(false, 401, '认证令牌无效');
      }
    },
  });

  wss.on('connection', (ws, req) => {
    const userId = req.userId;
    let deviceId = null;
    let fingerprint = null;

    logger.info('WebSocket 客户端连接', { userId });

    // 标记连接为活跃状态
    ws.isAlive = true;

    ws.on('pong', () => {
      ws.isAlive = true;
    });

    ws.on('message', async (rawData) => {
      try {
        const message = JSON.parse(rawData.toString());
        await handleMessage(ws, userId, message);
      } catch (err) {
        logger.error('WebSocket 消息处理错误', { error: err.message, userId });
        sendToClient(ws, {
          type: 'error',
          data: { message: '消息格式错误或处理失败' },
        });
      }
    });

    ws.on('close', async () => {
      logger.info('WebSocket 客户端断开', { userId, deviceId });

      // 从客户端列表中移除
      if (deviceId) {
        clients.delete(deviceId);
        // 将设备状态设为离线
        try {
          await Device.update({ status: 'offline' }, { where: { id: deviceId } });
        } catch (err) {
          logger.error('更新设备离线状态失败', { error: err.message, deviceId });
        }
      }
    });

    ws.on('error', (err) => {
      logger.error('WebSocket 连接错误', { error: err.message, userId, deviceId });
    });

    /**
     * 处理客户端消息
     */
    async function handleMessage(ws, userId, message) {
      const { type, data } = message;

      switch (type) {
        // 设备注册消息：客户端连接后首先发送此消息绑定设备
        case 'device_register': {
          const device = await Device.findOne({
            where: { fingerprint: data.fingerprint, userId },
          });

          if (!device) {
            sendToClient(ws, {
              type: 'device_register_result',
              data: { success: false, message: '设备未注册' },
            });
            return;
          }

          deviceId = device.id;
          fingerprint = data.fingerprint;

          // 如果该设备已有连接，关闭旧连接
          if (clients.has(deviceId)) {
            const oldClient = clients.get(deviceId);
            if (oldClient.ws.readyState === WebSocket.OPEN) {
              sendToClient(oldClient.ws, {
                type: 'kicked',
                data: { message: '设备在其他位置连接' },
              });
              oldClient.ws.close();
            }
          }

          // 注册到客户端列表
          clients.set(deviceId, { ws, userId, deviceId, fingerprint });

          // 更新设备在线状态
          await device.update({ status: 'online', lastHeartbeat: new Date() });

          sendToClient(ws, {
            type: 'device_register_result',
            data: { success: true, deviceId, message: '设备绑定成功' },
          });

          logger.info('设备已绑定到 WebSocket', { deviceId, fingerprint, userId });
          break;
        }

        // 设备心跳
        case 'heartbeat': {
          if (deviceId) {
            await Device.update(
              { lastHeartbeat: new Date(), status: 'online' },
              { where: { id: deviceId } }
            );
          }
          sendToClient(ws, { type: 'heartbeat_ack', data: { timestamp: Date.now() } });
          break;
        }

        // 任务进度上报
        case 'task_progress': {
          const { taskId, progress, total, result, errorMsg, status } = data;
          if (!taskId) {
            sendToClient(ws, {
              type: 'error',
              data: { message: '缺少 taskId' },
            });
            return;
          }

          await taskService.updateProgress(taskId, { progress, total, result, errorMsg, status });

          // 将进度广播给该用户的所有 Web 端连接（如果有的话）
          broadcastToUser(userId, {
            type: 'task_progress_update',
            data: { taskId, progress, total, status },
          });

          sendToClient(ws, { type: 'task_progress_ack', data: { taskId } });
          break;
        }

        // 任务执行日志
        case 'task_log': {
          const { TaskLog } = require('../models');
          await TaskLog.create({
            taskId: data.taskId,
            action: data.action,
            target: data.target || '',
            result: data.result || 'success',
            detail: data.detail || null,
            screenshot: data.screenshot || null,
          });
          break;
        }

        // 微信账号状态更新
        case 'wechat_status': {
          const { WechatAccount } = require('../models');
          if (data.wxid) {
            await WechatAccount.update(
              { status: data.status },
              { where: { wxid: data.wxid, userId } }
            );
          }
          break;
        }

        default:
          sendToClient(ws, {
            type: 'error',
            data: { message: `未知消息类型: ${type}` },
          });
      }
    }
  });

  // ========== 心跳检测定时器 ==========
  // 每隔 heartbeatInterval 向所有客户端发送 ping
  const heartbeatInterval = setInterval(() => {
    wss.clients.forEach((ws) => {
      if (!ws.isAlive) {
        logger.warn('WebSocket 客户端心跳超时，断开连接');
        ws.terminate();
        return;
      }
      ws.isAlive = false;
      ws.ping();
    });
  }, config.ws.heartbeatInterval);

  wss.on('close', () => {
    clearInterval(heartbeatInterval);
  });

  logger.info('WebSocket 服务已启动', { path: '/ws' });

  return wss;
}

/**
 * 向客户端发送消息
 * @param {WebSocket} ws - WebSocket 连接
 * @param {object} data - 消息数据
 */
function sendToClient(ws, data) {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data));
  }
}

/**
 * 向指定设备发送命令
 * @param {number} deviceId - 设备ID
 * @param {object} command - 命令数据
 * @returns {boolean} 是否发送成功
 */
function sendToDevice(deviceId, command) {
  const client = clients.get(deviceId);
  if (client && client.ws.readyState === WebSocket.OPEN) {
    sendToClient(client.ws, command);
    return true;
  }
  return false;
}

/**
 * 向指定用户的所有设备广播消息
 * @param {number} userId - 用户ID
 * @param {object} data - 消息数据
 */
function broadcastToUser(userId, data) {
  clients.forEach((client) => {
    if (client.userId === userId) {
      sendToClient(client.ws, data);
    }
  });
}

/**
 * 获取在线客户端列表
 * @returns {Map} 客户端 Map
 */
function getClients() {
  return clients;
}

module.exports = {
  initWebSocket,
  sendToDevice,
  sendToClient,
  broadcastToUser,
  getClients,
};
