/**
 * Joi 验证中间件工厂
 * 根据传入的 Joi schema 对请求数据进行验证
 *
 * @param {import('joi').Schema} schema - Joi 验证 schema
 * @param {'body'|'query'|'params'} source - 验证数据来源，默认 'body'
 * @returns {Function} Express 中间件
 */
const validate = (schema, source = 'body') => {
  return (req, res, next) => {
    const data = req[source];

    const { error, value } = schema.validate(data, {
      abortEarly: false, // 返回所有错误而非遇到第一个就停止
      stripUnknown: true, // 移除未定义的字段
      allowUnknown: false,
    });

    if (error) {
      const messages = error.details.map((detail) => detail.message);
      return res.status(400).json({
        success: false,
        data: null,
        message: '参数验证失败: ' + messages.join('; '),
      });
    }

    // 将验证后的数据回写（已经过 stripUnknown 清理）
    req[source] = value;
    next();
  };
};

module.exports = validate;
