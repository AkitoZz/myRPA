const { DataTypes } = require('sequelize');

module.exports = (sequelize) => {
  const WechatAccount = sequelize.define(
    'WechatAccount',
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
        comment: '登录设备ID',
      },
      wxid: {
        type: DataTypes.STRING(100),
        allowNull: false,
        comment: '微信ID',
      },
      nickname: {
        type: DataTypes.STRING(100),
        allowNull: true,
        defaultValue: '',
        comment: '微信昵称',
      },
      avatar: {
        type: DataTypes.STRING(500),
        allowNull: true,
        defaultValue: '',
        comment: '微信头像URL',
      },
      status: {
        type: DataTypes.ENUM('online', 'offline', 'banned'),
        allowNull: false,
        defaultValue: 'offline',
        comment: '微信在线状态',
      },
      todayAddFriend: {
        type: DataTypes.INTEGER.UNSIGNED,
        allowNull: false,
        defaultValue: 0,
        comment: '今日添加好友数',
      },
      todayMassMsg: {
        type: DataTypes.INTEGER.UNSIGNED,
        allowNull: false,
        defaultValue: 0,
        comment: '今日群发消息数',
      },
      todayAutoReply: {
        type: DataTypes.INTEGER.UNSIGNED,
        allowNull: false,
        defaultValue: 0,
        comment: '今日自动回复数',
      },
    },
    {
      tableName: 'wechat_accounts',
      timestamps: true,
      indexes: [
        { fields: ['userId'] },
        { fields: ['deviceId'] },
        { fields: ['wxid'] },
        { fields: ['status'] },
      ],
    }
  );

  return WechatAccount;
};
