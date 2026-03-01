const { DataTypes } = require('sequelize');

module.exports = (sequelize) => {
  const OperationLog = sequelize.define(
    'OperationLog',
    {
      id: {
        type: DataTypes.INTEGER.UNSIGNED,
        primaryKey: true,
        autoIncrement: true,
      },
      userId: {
        type: DataTypes.INTEGER.UNSIGNED,
        allowNull: true,
        comment: '操作用户ID',
      },
      action: {
        type: DataTypes.STRING(100),
        allowNull: false,
        comment: '操作动作',
      },
      module: {
        type: DataTypes.STRING(50),
        allowNull: false,
        comment: '操作模块',
      },
      detail: {
        type: DataTypes.JSON,
        allowNull: true,
        defaultValue: null,
        comment: '操作详情(JSON)',
      },
      ip: {
        type: DataTypes.STRING(45),
        allowNull: true,
        comment: '操作IP',
      },
    },
    {
      tableName: 'operation_logs',
      timestamps: true,
      updatedAt: false,
      indexes: [
        { fields: ['userId'] },
        { fields: ['action'] },
        { fields: ['module'] },
        { fields: ['createdAt'] },
      ],
    }
  );

  return OperationLog;
};
