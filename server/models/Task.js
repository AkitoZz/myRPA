const { DataTypes } = require('sequelize');

module.exports = (sequelize) => {
  const Task = sequelize.define(
    'Task',
    {
      id: {
        type: DataTypes.INTEGER.UNSIGNED,
        primaryKey: true,
        autoIncrement: true,
      },
      userId: {
        type: DataTypes.INTEGER.UNSIGNED,
        allowNull: false,
        comment: '所属用户ID',
      },
      deviceId: {
        type: DataTypes.INTEGER.UNSIGNED,
        allowNull: true,
        comment: '执行设备ID',
      },
      wechatAccountId: {
        type: DataTypes.INTEGER.UNSIGNED,
        allowNull: true,
        comment: '关联微信账号ID',
      },
      type: {
        type: DataTypes.ENUM('add_friend', 'mass_message', 'auto_reply', 'group_manage'),
        allowNull: false,
        comment: '任务类型',
      },
      name: {
        type: DataTypes.STRING(200),
        allowNull: false,
        comment: '任务名称',
      },
      config: {
        type: DataTypes.JSON,
        allowNull: true,
        defaultValue: {},
        comment: '任务配置(JSON)',
      },
      status: {
        type: DataTypes.ENUM('pending', 'running', 'paused', 'completed', 'failed'),
        allowNull: false,
        defaultValue: 'pending',
        comment: '任务状态',
      },
      progress: {
        type: DataTypes.INTEGER.UNSIGNED,
        allowNull: false,
        defaultValue: 0,
        comment: '当前进度',
      },
      total: {
        type: DataTypes.INTEGER.UNSIGNED,
        allowNull: false,
        defaultValue: 0,
        comment: '总数',
      },
      scheduleType: {
        type: DataTypes.ENUM('immediate', 'scheduled', 'recurring'),
        allowNull: false,
        defaultValue: 'immediate',
        comment: '调度类型: immediate-立即执行, scheduled-定时执行, recurring-循环执行',
      },
      scheduledAt: {
        type: DataTypes.DATE,
        allowNull: true,
        comment: '定时执行时间',
      },
      cronExpression: {
        type: DataTypes.STRING(100),
        allowNull: true,
        comment: 'Cron表达式(循环执行)',
      },
      result: {
        type: DataTypes.JSON,
        allowNull: true,
        defaultValue: null,
        comment: '任务结果(JSON)',
      },
      errorMsg: {
        type: DataTypes.TEXT,
        allowNull: true,
        comment: '错误信息',
      },
    },
    {
      tableName: 'tasks',
      timestamps: true,
      indexes: [
        { fields: ['userId'] },
        { fields: ['deviceId'] },
        { fields: ['wechatAccountId'] },
        { fields: ['status'] },
        { fields: ['type'] },
        { fields: ['scheduleType'] },
      ],
    }
  );

  return Task;
};
