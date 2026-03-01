const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const config = require('../config');
const { User } = require('../models');

const SALT_ROUNDS = 10;

class AuthService {
  /**
   * 密码哈希
   * @param {string} password - 明文密码
   * @returns {Promise<string>} 哈希后的密码
   */
  async hashPassword(password) {
    return bcrypt.hash(password, SALT_ROUNDS);
  }

  /**
   * 密码比对
   * @param {string} password - 明文密码
   * @param {string} hash - 哈希密码
   * @returns {Promise<boolean>}
   */
  async comparePassword(password, hash) {
    return bcrypt.compare(password, hash);
  }

  /**
   * 生成 JWT Token
   * @param {object} payload - Token 载荷
   * @param {string} expiresIn - 过期时间
   * @returns {string} JWT Token
   */
  generateToken(payload, expiresIn) {
    return jwt.sign(payload, config.jwt.secret, {
      expiresIn: expiresIn || config.jwt.expiresIn,
    });
  }

  /**
   * 用户注册
   * @param {object} data - { phone, password, nickname }
   * @returns {Promise<object>} 注册结果 { user, token }
   */
  async register(data) {
    const { phone, password, nickname } = data;

    // 检查手机号是否已注册
    const existing = await User.findOne({ where: { phone } });
    if (existing) {
      const error = new Error('该手机号已注册');
      error.statusCode = 409;
      throw error;
    }

    // 加密密码
    const hashedPassword = await this.hashPassword(password);

    // 创建用户
    const user = await User.create({
      phone,
      password: hashedPassword,
      nickname: nickname || `用户${phone.slice(-4)}`,
      role: 'user',
      memberLevel: 'free',
      status: 'active',
    });

    // 生成 token
    const token = this.generateToken({ userId: user.id, role: user.role });
    const refreshToken = this.generateToken(
      { userId: user.id, type: 'refresh' },
      config.jwt.refreshExpiresIn
    );

    // 返回时排除密码
    const userInfo = user.toJSON();
    delete userInfo.password;

    return { user: userInfo, token, refreshToken };
  }

  /**
   * 用户登录
   * @param {object} data - { phone, password }
   * @param {string} ip - 登录IP
   * @returns {Promise<object>} 登录结果 { user, token }
   */
  async login(data, ip) {
    const { phone, password } = data;

    // 查找用户
    const user = await User.findOne({ where: { phone } });
    if (!user) {
      const error = new Error('手机号或密码错误');
      error.statusCode = 401;
      throw error;
    }

    // 检查账号状态
    if (user.status !== 'active') {
      const error = new Error('账号已被禁用');
      error.statusCode = 403;
      throw error;
    }

    // 验证密码
    const isMatch = await this.comparePassword(password, user.password);
    if (!isMatch) {
      const error = new Error('手机号或密码错误');
      error.statusCode = 401;
      throw error;
    }

    // 更新登录信息
    await user.update({
      lastLoginAt: new Date(),
      lastLoginIp: ip || null,
    });

    // 生成 token
    const token = this.generateToken({ userId: user.id, role: user.role });
    const refreshToken = this.generateToken(
      { userId: user.id, type: 'refresh' },
      config.jwt.refreshExpiresIn
    );

    const userInfo = user.toJSON();
    delete userInfo.password;

    return { user: userInfo, token, refreshToken };
  }

  /**
   * 刷新 Token
   * @param {string} refreshToken - 刷新令牌
   * @returns {Promise<object>} { token, refreshToken }
   */
  async refreshToken(refreshToken) {
    if (!refreshToken) {
      const error = new Error('未提供刷新令牌');
      error.statusCode = 400;
      throw error;
    }

    let decoded;
    try {
      decoded = jwt.verify(refreshToken, config.jwt.secret);
    } catch (err) {
      const error = new Error('刷新令牌无效或已过期');
      error.statusCode = 401;
      throw error;
    }

    if (decoded.type !== 'refresh') {
      const error = new Error('无效的刷新令牌');
      error.statusCode = 401;
      throw error;
    }

    // 验证用户仍然存在且状态正常
    const user = await User.findByPk(decoded.userId);
    if (!user || user.status !== 'active') {
      const error = new Error('用户不存在或已被禁用');
      error.statusCode = 401;
      throw error;
    }

    // 生成新的 token
    const newToken = this.generateToken({ userId: user.id, role: user.role });
    const newRefreshToken = this.generateToken(
      { userId: user.id, type: 'refresh' },
      config.jwt.refreshExpiresIn
    );

    return { token: newToken, refreshToken: newRefreshToken };
  }
}

module.exports = new AuthService();
