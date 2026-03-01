const { DataTypes } = require('sequelize');

module.exports = (sequelize) => {
  const TaskLog = sequelize.define(
    'TaskLog',
    {
      id: {
        type: DataTypes.INTEGER.UNSIGNED,
        primaryKey: true,
        autoIncrement: true,
      },
      taskId: {
        type: DataTypes.INTEGER.UNSIGNED,
        allowNull: false,
        comment: '关联任务ID',
      },
      action: {
        type: DataTypes.STRING(100),
        allowNull: false,
        comment: '操作动作',
      },
      target: {
        type: DataTypes.STRING(255),
        allowNull: true,
        defaultValue: '',
        comment: '操作目标(如微信号、群名等)',
      },
      result: {
        type: DataTypes.ENUM('success', 'fail', 'skip'),
        allowNull: false,
        defaultValue: 'success',
        comment: '执行结果',
      },
      detail: {
        type: DataTypes.JSON,
        allowNull: true,
        defaultValue: null,
        comment: '详细信息(JSON)',
      },
      screenshot: {
        type: DataTypes.STRING(500),
        allowNull: true,
        comment: '截图URL',
      },
    },
    {
      tableName: 'task_logs',
      timestamps: true,
      updatedAt: false, // 日志只有创建时间，无需更新时间
      indexes: [
        { fields: ['taskId'] },
        { fields: ['result'] },
        { fields: ['createdAt'] },
      ],
    }
  );

  return TaskLog;
};
