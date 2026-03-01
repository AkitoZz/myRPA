require('dotenv').config();

const http = require('http');
const app = require('./app');
const config = require('./config');
const logger = require('./config/logger');
const { sequelize } = require('./models');
const { initWebSocket } = require('./websocket');

const PORT = config.server.port;

async function start() {
  try {
    // 1. 测试数据库连接
    await sequelize.authenticate();
    logger.info('数据库连接成功', {
      host: config.db.host,
      port: config.db.port,
      database: config.db.database,
    });

    // 2. 同步数据库模型（自动创建不存在的表，不会修改已有表结构）
    await sequelize.sync({ alter: false });
    logger.info('数据库模型同步完成');

    // 3. 创建 HTTP 服务器
    const server = http.createServer(app);

    // 4. 初始化 WebSocket 服务
    initWebSocket(server);

    // 5. 启动服务器
    server.listen(PORT, () => {
      logger.info(`服务器已启动`, {
        port: PORT,
        env: config.server.env,
        url: `http://localhost:${PORT}`,
        ws: `ws://localhost:${PORT}/ws`,
      });
    });

    // ========== 优雅关闭 ==========
    const gracefulShutdown = async (signal) => {
      logger.info(`收到 ${signal} 信号，开始优雅关闭...`);

      server.close(async () => {
        logger.info('HTTP 服务器已关闭');

        try {
          await sequelize.close();
          logger.info('数据库连接已关闭');
        } catch (err) {
          logger.error('关闭数据库连接失败', { error: err.message });
        }

        process.exit(0);
      });

      // 如果 10 秒内无法完成关闭，强制退出
      setTimeout(() => {
        logger.error('无法在规定时间内完成关闭，强制退出');
        process.exit(1);
      }, 10000);
    };

    process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
    process.on('SIGINT', () => gracefulShutdown('SIGINT'));

    // 未捕获的异常处理
    process.on('uncaughtException', (err) => {
      logger.error('未捕获的异常', { error: err.message, stack: err.stack });
      process.exit(1);
    });

    process.on('unhandledRejection', (reason, promise) => {
      logger.error('未处理的 Promise 拒绝', {
        reason: reason instanceof Error ? reason.message : reason,
        stack: reason instanceof Error ? reason.stack : undefined,
      });
    });
  } catch (error) {
    logger.error('服务器启动失败', { error: error.message, stack: error.stack });
    process.exit(1);
  }
}

start();
