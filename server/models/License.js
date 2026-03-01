const { DataTypes } = require('sequelize');

module.exports = (sequelize) => {
  const License = sequelize.define(
    'License',
    {
      id: {
        type: DataTypes.INTEGER.UNSIGNED,
        primaryKey: true,
        autoIncrement: true,
      },
      code: {
        type: DataTypes.STRING(64),
        allowNull: false,
        unique: true,
        comment: '授权码',
      },
      type: {
        type: DataTypes.ENUM('trial', 'monthly', 'quarterly', 'yearly', 'lifetime'),
        allowNull: false,
        defaultValue: 'trial',
        comment: '授权类型',
      },
      durationDays: {
        type: DataTypes.INTEGER.UNSIGNED,
        allowNull: false,
        defaultValue: 0,
        comment: '有效天数',
      },
      userId: {
        type: DataTypes.INTEGER.UNSIGNED,
        allowNull: true,
        comment: '使用者用户ID',
      },
      deviceId: {
        type: DataTypes.INTEGER.UNSIGNED,
        allowNull: true,
        comment: '绑定设备ID',
      },
      status: {
        type: DataTypes.ENUM('unused', 'activated', 'expired', 'revoked'),
        allowNull: false,
        defaultValue: 'unused',
        comment: '授权状态',
      },
      activatedAt: {
        type: DataTypes.DATE,
        allowNull: true,
        comment: '激活时间',
      },
      expireAt: {
        type: DataTypes.DATE,
        allowNull: true,
        comment: '过期时间',
      },
    },
    {
      tableName: 'licenses',
      timestamps: true,
      indexes: [
        { unique: true, fields: ['code'] },
        { fields: ['userId'] },
        { fields: ['deviceId'] },
        { fields: ['status'] },
        { fields: ['type'] },
      ],
    }
  );

  return License;
};
