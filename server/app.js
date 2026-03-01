const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const routes = require('./routes');
const errorHandler = require('./middlewares/errorHandler');
const logger = require('./config/logger');

const app = express();

// ========== 安全中间件 ==========
app.use(helmet());

// ========== CORS 跨域配置 ==========
app.use(
  cors({
    origin: process.env.CORS_ORIGIN || '*',
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
    credentials: true,
    maxAge: 86400,
  })
);

// ========== 请求体解析 ==========
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// ========== 请求日志 ==========
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    logger.info(`${req.method} ${req.originalUrl}`, {
      status: res.statusCode,
      duration: `${duration}ms`,
      ip: req.ip,
    });
  });
  next();
});

// ========== 健康检查接口 ==========
app.get('/health', (req, res) => {
  res.json({
    success: true,
    data: {
      status: 'ok',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
    },
    message: '服务运行正常',
  });
});

// ========== API 路由 ==========
app.use('/api', routes);

// ========== 404 处理 ==========
app.use((req, res) => {
  res.status(404).json({
    success: false,
    data: null,
    message: `接口不存在: ${req.method} ${req.originalUrl}`,
  });
});

// ========== 全局错误处理 ==========
app.use(errorHandler);

module.exports = app;
