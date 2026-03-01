const { DataTypes } = require('sequelize');

module.exports = (sequelize) => {
  const User = sequelize.define(
    'User',
    {
      id: {
        type: DataTypes.INTEGER.UNSIGNED,
        primaryKey: true,
        autoIncrement: true,
      },
      phone: {
        type: DataTypes.STRING(20),
        allowNull: false,
        unique: true,
        comment: '手机号',
      },
      password: {
        type: DataTypes.STRING(255),
        allowNull: false,
        comment: '密码(bcrypt加密)',
      },
      nickname: {
        type: DataTypes.STRING(50),
        allowNull: true,
        defaultValue: '',
        comment: '昵称',
      },
      avatar: {
        type: DataTypes.STRING(500),
        allowNull: true,
        defaultValue: '',
        comment: '头像URL',
      },
      role: {
        type: DataTypes.ENUM('admin', 'agent', 'user'),
        allowNull: false,
        defaultValue: 'user',
        comment: '角色: admin-管理员, agent-代理, user-普通用户',
      },
      memberLevel: {
        type: DataTypes.ENUM('free', 'basic', 'pro', 'enterprise'),
        allowNull: false,
        defaultValue: 'free',
        comment: '会员等级',
      },
      memberExpireAt: {
        type: DataTypes.DATE,
        allowNull: true,
        comment: '会员过期时间',
      },
      status: {
        type: DataTypes.ENUM('active', 'disabled', 'banned'),
        allowNull: false,
        defaultValue: 'active',
        comment: '账号状态',
      },
      lastLoginAt: {
        type: DataTypes.DATE,
        allowNull: true,
        comment: '最后登录时间',
      },
      lastLoginIp: {
        type: DataTypes.STRING(45),
        allowNull: true,
        comment: '最后登录IP',
      },
    },
    {
      tableName: 'users',
      timestamps: true,
      indexes: [
        { unique: true, fields: ['phone'] },
        { fields: ['role'] },
        { fields: ['status'] },
      ],
    }
  );

  return User;
};
