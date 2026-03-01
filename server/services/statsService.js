const { User, Device, Task, TaskLog, WechatAccount, License } = require('../models');
const { Op, fn, col, literal } = require('sequelize');

class StatsService {
  /**
   * 获取仪表盘统计数据
   * @param {number} userId - 当前用户ID（非管理员时只统计自己的数据）
   * @param {string} role - 当前用户角色
   * @returns {Promise<object>} 统计数据
   */
  async getDashboard(userId, role) {
    const isAdmin = role === 'admin';
    const userWhere = isAdmin ? {} : { userId };

    // 今天的起止时间
    const todayStart = new Date();
    todayStart.setHours(0, 0, 0, 0);
    const todayEnd = new Date();
    todayEnd.setHours(23, 59, 59, 999);

    // 并行查询所有统计数据
    const [
      totalUsers,
      onlineDevices,
      totalDevices,
      todayTasks,
      runningTasks,
      todayTaskLogs,
      todaySuccessLogs,
      totalWechatAccounts,
      onlineWechatAccounts,
      activeLicenses,
    ] = await Promise.all([
      // 用户总数（仅管理员可见全部）
      isAdmin ? User.count({ where: { status: 'active' } }) : 1,

      // 在线设备数
      Device.count({ where: { ...userWhere, status: 'online' } }),

      // 设备总数
      Device.count({ where: userWhere }),

      // 今日任务数
      Task.count({
        where: {
          ...userWhere,
          createdAt: { [Op.between]: [todayStart, todayEnd] },
        },
      }),

      // 运行中的任务数
      Task.count({ where: { ...userWhere, status: 'running' } }),

      // 今日任务日志总数
      TaskLog.count({
        where: {
          createdAt: { [Op.between]: [todayStart, todayEnd] },
        },
        include: isAdmin
          ? []
          : [{ model: Task, as: 'task', where: { userId }, attributes: [] }],
      }),

      // 今日成功的任务日志数
      TaskLog.count({
        where: {
          result: 'success',
          createdAt: { [Op.between]: [todayStart, todayEnd] },
        },
        include: isAdmin
          ? []
          : [{ model: Task, as: 'task', where: { userId }, attributes: [] }],
      }),

      // 微信账号总数
      WechatAccount.count({ where: userWhere }),

      // 在线微信账号数
      WechatAccount.count({ where: { ...userWhere, status: 'online' } }),

      // 激活中的授权码数
      License.count({
        where: {
          ...(isAdmin ? {} : { userId }),
          status: 'activated',
          expireAt: { [Op.gt]: new Date() },
        },
      }),
    ]);

    // 计算成功率
    const successRate = todayTaskLogs > 0
      ? Math.round((todaySuccessLogs / todayTaskLogs) * 10000) / 100
      : 0;

    return {
      overview: {
        totalUsers,
        onlineDevices,
        totalDevices,
        runningTasks,
        totalWechatAccounts,
        onlineWechatAccounts,
        activeLicenses,
      },
      today: {
        tasks: todayTasks,
        totalLogs: todayTaskLogs,
        successLogs: todaySuccessLogs,
        successRate: `${successRate}%`,
      },
    };
  }
}

module.exports = new StatsService();
