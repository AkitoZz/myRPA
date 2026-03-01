require('dotenv').config();

module.exports = {
  server: {
    port: parseInt(process.env.SERVER_PORT, 10) || 3000,
    env: process.env.NODE_ENV || 'development',
  },

  db: {
    host: process.env.DB_HOST || '127.0.0.1',
    port: parseInt(process.env.DB_PORT, 10) || 3306,
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || '',
    database: process.env.DB_DATABASE || 'myrpa',
    dialect: 'mysql',
    pool: {
      max: 10,
      min: 0,
      acquire: 30000,
      idle: 10000,
    },
    logging: process.env.NODE_ENV === 'development' ? console.log : false,
  },

  jwt: {
    secret: process.env.JWT_SECRET || 'default_jwt_secret_do_not_use_in_prod',
    expiresIn: process.env.JWT_EXPIRES_IN || '7d',
    refreshExpiresIn: process.env.JWT_REFRESH_EXPIRES_IN || '30d',
  },

  ws: {
    heartbeatInterval: parseInt(process.env.WS_HEARTBEAT_INTERVAL, 10) || 30000,
    heartbeatTimeout: parseInt(process.env.WS_HEARTBEAT_TIMEOUT, 10) || 35000,
  },

  log: {
    level: process.env.LOG_LEVEL || 'info',
    dir: process.env.LOG_DIR || 'logs',
  },
};
