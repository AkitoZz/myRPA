const winston = require('winston');
const path = require('path');
const fs = require('fs');
const config = require('./index');

// 确保日志目录存在
const logDir = path.resolve(__dirname, '..', config.log.dir);
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

const logger = winston.createLogger({
  level: config.log.level,
  format: winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'myrpa-server' },
  transports: [
    // 错误日志单独存储
    new winston.transports.File({
      filename: path.join(logDir, 'error.log'),
      level: 'error',
      maxsize: 10 * 1024 * 1024, // 10MB
      maxFiles: 5,
    }),
    // 所有日志
    new winston.transports.File({
      filename: path.join(logDir, 'combined.log'),
      maxsize: 10 * 1024 * 1024,
      maxFiles: 10,
    }),
  ],
});

// 开发环境下同时输出到控制台
if (config.server.env !== 'production') {
  logger.add(
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.printf(({ timestamp, level, message, stack, ...meta }) => {
          let log = `${timestamp} [${level}]: ${message}`;
          if (stack) log += `\n${stack}`;
          const metaKeys = Object.keys(meta).filter((k) => k !== 'service');
          if (metaKeys.length > 0) {
            const metaObj = {};
            metaKeys.forEach((k) => (metaObj[k] = meta[k]));
            log += ` ${JSON.stringify(metaObj)}`;
          }
          return log;
        })
      ),
    })
  );
}

module.exports = logger;
