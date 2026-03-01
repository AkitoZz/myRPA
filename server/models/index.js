const { Sequelize } = require('sequelize');
const config = require('../config');
const logger = require('../config/logger');

// 创建 Sequelize 实例
const sequelize = new Sequelize(config.db.database, config.db.user, config.db.password, {
  host: config.db.host,
  port: config.db.port,
  dialect: config.db.dialect,
  pool: config.db.pool,
  logging: config.db.logging ? (msg) => logger.debug(msg) : false,
  timezone: '+08:00', // 中国时区
  define: {
    charset: 'utf8mb4',
    collate: 'utf8mb4_unicode_ci',
    underscored: false,
  },
});

// 加载所有模型
const User = require('./User')(sequelize);
const Device = require('./Device')(sequelize);
const License = require('./License')(sequelize);
const WechatAccount = require('./WechatAccount')(sequelize);
const Task = require('./Task')(sequelize);
const TaskLog = require('./TaskLog')(sequelize);
const OperationLog = require('./OperationLog')(sequelize);

// ========== 定义模型关联 ==========

// User 一对多 Device
User.hasMany(Device, { foreignKey: 'userId', as: 'devices' });
Device.belongsTo(User, { foreignKey: 'userId', as: 'user' });

// User 一对多 License
User.hasMany(License, { foreignKey: 'userId', as: 'licenses' });
License.belongsTo(User, { foreignKey: 'userId', as: 'user' });

// User 一对多 WechatAccount
User.hasMany(WechatAccount, { foreignKey: 'userId', as: 'wechatAccounts' });
WechatAccount.belongsTo(User, { foreignKey: 'userId', as: 'user' });

// User 一对多 Task
User.hasMany(Task, { foreignKey: 'userId', as: 'tasks' });
Task.belongsTo(User, { foreignKey: 'userId', as: 'user' });

// Device 一对多 WechatAccount
Device.hasMany(WechatAccount, { foreignKey: 'deviceId', as: 'wechatAccounts' });
WechatAccount.belongsTo(Device, { foreignKey: 'deviceId', as: 'device' });

// Device 一对多 License
Device.hasMany(License, { foreignKey: 'deviceId', as: 'licenses' });
License.belongsTo(Device, { foreignKey: 'deviceId', as: 'device' });

// Task 关联
Task.belongsTo(Device, { foreignKey: 'deviceId', as: 'device' });
Device.hasMany(Task, { foreignKey: 'deviceId', as: 'tasks' });

Task.belongsTo(WechatAccount, { foreignKey: 'wechatAccountId', as: 'wechatAccount' });
WechatAccount.hasMany(Task, { foreignKey: 'wechatAccountId', as: 'tasks' });

// Task 一对多 TaskLog
Task.hasMany(TaskLog, { foreignKey: 'taskId', as: 'logs' });
TaskLog.belongsTo(Task, { foreignKey: 'taskId', as: 'task' });

// User 一对多 OperationLog
User.hasMany(OperationLog, { foreignKey: 'userId', as: 'operationLogs' });
OperationLog.belongsTo(User, { foreignKey: 'userId', as: 'user' });

module.exports = {
  sequelize,
  Sequelize,
  User,
  Device,
  License,
  WechatAccount,
  Task,
  TaskLog,
  OperationLog,
};
