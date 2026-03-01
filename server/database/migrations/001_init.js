/**
 * 数据库初始化迁移脚本
 * 创建所有业务表
 *
 * 运行: node database/migrations/001_init.js
 */

const { sequelize } = require('../../models');
const logger = require('../../config/logger');

async function up() {
  const queryInterface = sequelize.getQueryInterface();

  // ========== 1. 创建 users 表 ==========
  await queryInterface.createTable('users', {
    id: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      primaryKey: true,
      autoIncrement: true,
    },
    phone: {
      type: sequelize.Sequelize.STRING(20),
      allowNull: false,
      unique: true,
      comment: '手机号',
    },
    password: {
      type: sequelize.Sequelize.STRING(255),
      allowNull: false,
      comment: '密码(bcrypt加密)',
    },
    nickname: {
      type: sequelize.Sequelize.STRING(50),
      allowNull: true,
      defaultValue: '',
      comment: '昵称',
    },
    avatar: {
      type: sequelize.Sequelize.STRING(500),
      allowNull: true,
      defaultValue: '',
      comment: '头像URL',
    },
    role: {
      type: sequelize.Sequelize.ENUM('admin', 'agent', 'user'),
      allowNull: false,
      defaultValue: 'user',
      comment: '角色',
    },
    memberLevel: {
      type: sequelize.Sequelize.ENUM('free', 'basic', 'pro', 'enterprise'),
      allowNull: false,
      defaultValue: 'free',
      comment: '会员等级',
    },
    memberExpireAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: true,
      comment: '会员过期时间',
    },
    status: {
      type: sequelize.Sequelize.ENUM('active', 'disabled', 'banned'),
      allowNull: false,
      defaultValue: 'active',
      comment: '账号状态',
    },
    lastLoginAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: true,
      comment: '最后登录时间',
    },
    lastLoginIp: {
      type: sequelize.Sequelize.STRING(45),
      allowNull: true,
      comment: '最后登录IP',
    },
    createdAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: false,
      defaultValue: sequelize.Sequelize.literal('CURRENT_TIMESTAMP'),
    },
    updatedAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: false,
      defaultValue: sequelize.Sequelize.literal('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    },
  }, {
    charset: 'utf8mb4',
    collate: 'utf8mb4_unicode_ci',
    comment: '用户表',
  });

  await queryInterface.addIndex('users', ['phone'], { unique: true });
  await queryInterface.addIndex('users', ['role']);
  await queryInterface.addIndex('users', ['status']);

  // ========== 2. 创建 devices 表 ==========
  await queryInterface.createTable('devices', {
    id: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      primaryKey: true,
      autoIncrement: true,
    },
    userId: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: false,
      references: { model: 'users', key: 'id' },
      onUpdate: 'CASCADE',
      onDelete: 'CASCADE',
      comment: '所属用户ID',
    },
    deviceName: {
      type: sequelize.Sequelize.STRING(100),
      allowNull: false,
      defaultValue: '',
      comment: '设备名称',
    },
    fingerprint: {
      type: sequelize.Sequelize.STRING(255),
      allowNull: false,
      unique: true,
      comment: '设备指纹',
    },
    os: {
      type: sequelize.Sequelize.STRING(50),
      allowNull: true,
      defaultValue: '',
      comment: '操作系统',
    },
    ip: {
      type: sequelize.Sequelize.STRING(45),
      allowNull: true,
      defaultValue: '',
      comment: 'IP地址',
    },
    status: {
      type: sequelize.Sequelize.ENUM('online', 'offline', 'banned'),
      allowNull: false,
      defaultValue: 'offline',
      comment: '设备状态',
    },
    lastHeartbeat: {
      type: sequelize.Sequelize.DATE,
      allowNull: true,
      comment: '最后心跳时间',
    },
    createdAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: false,
      defaultValue: sequelize.Sequelize.literal('CURRENT_TIMESTAMP'),
    },
    updatedAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: false,
      defaultValue: sequelize.Sequelize.literal('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    },
  }, {
    charset: 'utf8mb4',
    collate: 'utf8mb4_unicode_ci',
    comment: '设备表',
  });

  await queryInterface.addIndex('devices', ['fingerprint'], { unique: true });
  await queryInterface.addIndex('devices', ['userId']);
  await queryInterface.addIndex('devices', ['status']);

  // ========== 3. 创建 licenses 表 ==========
  await queryInterface.createTable('licenses', {
    id: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      primaryKey: true,
      autoIncrement: true,
    },
    code: {
      type: sequelize.Sequelize.STRING(64),
      allowNull: false,
      unique: true,
      comment: '授权码',
    },
    type: {
      type: sequelize.Sequelize.ENUM('trial', 'monthly', 'quarterly', 'yearly', 'lifetime'),
      allowNull: false,
      defaultValue: 'trial',
      comment: '授权类型',
    },
    durationDays: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: false,
      defaultValue: 0,
      comment: '有效天数',
    },
    userId: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: true,
      references: { model: 'users', key: 'id' },
      onUpdate: 'CASCADE',
      onDelete: 'SET NULL',
      comment: '使用者用户ID',
    },
    deviceId: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: true,
      references: { model: 'devices', key: 'id' },
      onUpdate: 'CASCADE',
      onDelete: 'SET NULL',
      comment: '绑定设备ID',
    },
    status: {
      type: sequelize.Sequelize.ENUM('unused', 'activated', 'expired', 'revoked'),
      allowNull: false,
      defaultValue: 'unused',
      comment: '授权状态',
    },
    activatedAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: true,
      comment: '激活时间',
    },
    expireAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: true,
      comment: '过期时间',
    },
    createdAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: false,
      defaultValue: sequelize.Sequelize.literal('CURRENT_TIMESTAMP'),
    },
    updatedAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: false,
      defaultValue: sequelize.Sequelize.literal('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    },
  }, {
    charset: 'utf8mb4',
    collate: 'utf8mb4_unicode_ci',
    comment: '授权码表',
  });

  await queryInterface.addIndex('licenses', ['code'], { unique: true });
  await queryInterface.addIndex('licenses', ['userId']);
  await queryInterface.addIndex('licenses', ['deviceId']);
  await queryInterface.addIndex('licenses', ['status']);
  await queryInterface.addIndex('licenses', ['type']);

  // ========== 4. 创建 wechat_accounts 表 ==========
  await queryInterface.createTable('wechat_accounts', {
    id: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      primaryKey: true,
      autoIncrement: true,
    },
    userId: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: false,
      references: { model: 'users', key: 'id' },
      onUpdate: 'CASCADE',
      onDelete: 'CASCADE',
      comment: '所属用户ID',
    },
    deviceId: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: true,
      references: { model: 'devices', key: 'id' },
      onUpdate: 'CASCADE',
      onDelete: 'SET NULL',
      comment: '登录设备ID',
    },
    wxid: {
      type: sequelize.Sequelize.STRING(100),
      allowNull: false,
      comment: '微信ID',
    },
    nickname: {
      type: sequelize.Sequelize.STRING(100),
      allowNull: true,
      defaultValue: '',
      comment: '微信昵称',
    },
    avatar: {
      type: sequelize.Sequelize.STRING(500),
      allowNull: true,
      defaultValue: '',
      comment: '微信头像URL',
    },
    status: {
      type: sequelize.Sequelize.ENUM('online', 'offline', 'banned'),
      allowNull: false,
      defaultValue: 'offline',
      comment: '在线状态',
    },
    todayAddFriend: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: false,
      defaultValue: 0,
      comment: '今日添加好友数',
    },
    todayMassMsg: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: false,
      defaultValue: 0,
      comment: '今日群发消息数',
    },
    todayAutoReply: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: false,
      defaultValue: 0,
      comment: '今日自动回复数',
    },
    createdAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: false,
      defaultValue: sequelize.Sequelize.literal('CURRENT_TIMESTAMP'),
    },
    updatedAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: false,
      defaultValue: sequelize.Sequelize.literal('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    },
  }, {
    charset: 'utf8mb4',
    collate: 'utf8mb4_unicode_ci',
    comment: '微信账号表',
  });

  await queryInterface.addIndex('wechat_accounts', ['userId']);
  await queryInterface.addIndex('wechat_accounts', ['deviceId']);
  await queryInterface.addIndex('wechat_accounts', ['wxid']);
  await queryInterface.addIndex('wechat_accounts', ['status']);

  // ========== 5. 创建 tasks 表 ==========
  await queryInterface.createTable('tasks', {
    id: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      primaryKey: true,
      autoIncrement: true,
    },
    userId: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: false,
      references: { model: 'users', key: 'id' },
      onUpdate: 'CASCADE',
      onDelete: 'CASCADE',
      comment: '所属用户ID',
    },
    deviceId: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: true,
      references: { model: 'devices', key: 'id' },
      onUpdate: 'CASCADE',
      onDelete: 'SET NULL',
      comment: '执行设备ID',
    },
    wechatAccountId: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: true,
      references: { model: 'wechat_accounts', key: 'id' },
      onUpdate: 'CASCADE',
      onDelete: 'SET NULL',
      comment: '关联微信账号ID',
    },
    type: {
      type: sequelize.Sequelize.ENUM('add_friend', 'mass_message', 'auto_reply', 'group_manage'),
      allowNull: false,
      comment: '任务类型',
    },
    name: {
      type: sequelize.Sequelize.STRING(200),
      allowNull: false,
      comment: '任务名称',
    },
    config: {
      type: sequelize.Sequelize.JSON,
      allowNull: true,
      comment: '任务配置',
    },
    status: {
      type: sequelize.Sequelize.ENUM('pending', 'running', 'paused', 'completed', 'failed'),
      allowNull: false,
      defaultValue: 'pending',
      comment: '任务状态',
    },
    progress: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: false,
      defaultValue: 0,
      comment: '当前进度',
    },
    total: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: false,
      defaultValue: 0,
      comment: '总数',
    },
    scheduleType: {
      type: sequelize.Sequelize.ENUM('immediate', 'scheduled', 'recurring'),
      allowNull: false,
      defaultValue: 'immediate',
      comment: '调度类型',
    },
    scheduledAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: true,
      comment: '定时执行时间',
    },
    cronExpression: {
      type: sequelize.Sequelize.STRING(100),
      allowNull: true,
      comment: 'Cron表达式',
    },
    result: {
      type: sequelize.Sequelize.JSON,
      allowNull: true,
      comment: '任务结果',
    },
    errorMsg: {
      type: sequelize.Sequelize.TEXT,
      allowNull: true,
      comment: '错误信息',
    },
    createdAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: false,
      defaultValue: sequelize.Sequelize.literal('CURRENT_TIMESTAMP'),
    },
    updatedAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: false,
      defaultValue: sequelize.Sequelize.literal('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    },
  }, {
    charset: 'utf8mb4',
    collate: 'utf8mb4_unicode_ci',
    comment: '任务表',
  });

  await queryInterface.addIndex('tasks', ['userId']);
  await queryInterface.addIndex('tasks', ['deviceId']);
  await queryInterface.addIndex('tasks', ['wechatAccountId']);
  await queryInterface.addIndex('tasks', ['status']);
  await queryInterface.addIndex('tasks', ['type']);
  await queryInterface.addIndex('tasks', ['scheduleType']);

  // ========== 6. 创建 task_logs 表 ==========
  await queryInterface.createTable('task_logs', {
    id: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      primaryKey: true,
      autoIncrement: true,
    },
    taskId: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: false,
      references: { model: 'tasks', key: 'id' },
      onUpdate: 'CASCADE',
      onDelete: 'CASCADE',
      comment: '关联任务ID',
    },
    action: {
      type: sequelize.Sequelize.STRING(100),
      allowNull: false,
      comment: '操作动作',
    },
    target: {
      type: sequelize.Sequelize.STRING(255),
      allowNull: true,
      defaultValue: '',
      comment: '操作目标',
    },
    result: {
      type: sequelize.Sequelize.ENUM('success', 'fail', 'skip'),
      allowNull: false,
      defaultValue: 'success',
      comment: '执行结果',
    },
    detail: {
      type: sequelize.Sequelize.JSON,
      allowNull: true,
      comment: '详细信息',
    },
    screenshot: {
      type: sequelize.Sequelize.STRING(500),
      allowNull: true,
      comment: '截图URL',
    },
    createdAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: false,
      defaultValue: sequelize.Sequelize.literal('CURRENT_TIMESTAMP'),
    },
  }, {
    charset: 'utf8mb4',
    collate: 'utf8mb4_unicode_ci',
    comment: '任务日志表',
  });

  await queryInterface.addIndex('task_logs', ['taskId']);
  await queryInterface.addIndex('task_logs', ['result']);
  await queryInterface.addIndex('task_logs', ['createdAt']);

  // ========== 7. 创建 operation_logs 表 ==========
  await queryInterface.createTable('operation_logs', {
    id: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      primaryKey: true,
      autoIncrement: true,
    },
    userId: {
      type: sequelize.Sequelize.INTEGER.UNSIGNED,
      allowNull: true,
      references: { model: 'users', key: 'id' },
      onUpdate: 'CASCADE',
      onDelete: 'SET NULL',
      comment: '操作用户ID',
    },
    action: {
      type: sequelize.Sequelize.STRING(100),
      allowNull: false,
      comment: '操作动作',
    },
    module: {
      type: sequelize.Sequelize.STRING(50),
      allowNull: false,
      comment: '操作模块',
    },
    detail: {
      type: sequelize.Sequelize.JSON,
      allowNull: true,
      comment: '操作详情',
    },
    ip: {
      type: sequelize.Sequelize.STRING(45),
      allowNull: true,
      comment: '操作IP',
    },
    createdAt: {
      type: sequelize.Sequelize.DATE,
      allowNull: false,
      defaultValue: sequelize.Sequelize.literal('CURRENT_TIMESTAMP'),
    },
  }, {
    charset: 'utf8mb4',
    collate: 'utf8mb4_unicode_ci',
    comment: '操作日志表',
  });

  await queryInterface.addIndex('operation_logs', ['userId']);
  await queryInterface.addIndex('operation_logs', ['action']);
  await queryInterface.addIndex('operation_logs', ['module']);
  await queryInterface.addIndex('operation_logs', ['createdAt']);
}

async function down() {
  const queryInterface = sequelize.getQueryInterface();

  // 按依赖关系的反序删除表
  await queryInterface.dropTable('operation_logs');
  await queryInterface.dropTable('task_logs');
  await queryInterface.dropTable('tasks');
  await queryInterface.dropTable('wechat_accounts');
  await queryInterface.dropTable('licenses');
  await queryInterface.dropTable('devices');
  await queryInterface.dropTable('users');
}

// 如果直接运行此脚本
if (require.main === module) {
  const action = process.argv[2] || 'up';

  (async () => {
    try {
      await sequelize.authenticate();
      logger.info('数据库连接成功');

      if (action === 'up') {
        logger.info('开始执行迁移...');
        await up();
        logger.info('迁移完成：所有表已创建');
      } else if (action === 'down') {
        logger.info('开始回滚迁移...');
        await down();
        logger.info('回滚完成：所有表已删除');
      } else {
        logger.error(`未知操作: ${action}，请使用 up 或 down`);
      }

      process.exit(0);
    } catch (error) {
      logger.error('迁移执行失败', { error: error.message, stack: error.stack });
      process.exit(1);
    }
  })();
}

module.exports = { up, down };
