const { DataTypes } = require('sequelize');

module.exports = (sequelize) => {
  const Device = sequelize.define(
    'Device',
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
      deviceName: {
        type: DataTypes.STRING(100),
        allowNull: false,
        defaultValue: '',
        comment: '设备名称',
      },
      fingerprint: {
        type: DataTypes.STRING(255),
        allowNull: false,
        unique: true,
        comment: '设备指纹(唯一标识)',
      },
      os: {
        type: DataTypes.STRING(50),
        allowNull: true,
        defaultValue: '',
        comment: '操作系统',
      },
      ip: {
        type: DataTypes.STRING(45),
        allowNull: true,
        defaultValue: '',
        comment: '设备IP地址',
      },
      status: {
        type: DataTypes.ENUM('online', 'offline', 'banned'),
        allowNull: false,
        defaultValue: 'offline',
        comment: '设备状态',
      },
      lastHeartbeat: {
        type: DataTypes.DATE,
        allowNull: true,
        comment: '最后心跳时间',
      },
    },
    {
      tableName: 'devices',
      timestamps: true,
      indexes: [
        { unique: true, fields: ['fingerprint'] },
        { fields: ['userId'] },
        { fields: ['status'] },
      ],
    }
  );

  return Device;
};
