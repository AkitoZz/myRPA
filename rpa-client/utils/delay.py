"""
人性化延迟工具模块

模拟人类操作行为的延迟函数，包括随机延迟、打字延迟、鼠标移动等。
"""

import math
import random
import time
from typing import Tuple, Optional

from loguru import logger

from config.anti_risk import AntiRiskConfig


_operation_count = 0
_last_rest_time = time.time()
_anti_risk_config: Optional[AntiRiskConfig] = None


def set_anti_risk_config(config: AntiRiskConfig) -> None:
    """设置反风控配置"""
    global _anti_risk_config
    _anti_risk_config = config


def get_anti_risk_config() -> AntiRiskConfig:
    """获取当前反风控配置"""
    global _anti_risk_config
    if _anti_risk_config is None:
        _anti_risk_config = AntiRiskConfig()
    return _anti_risk_config


def random_delay(min_s: float = 1.0, max_s: float = 3.0) -> float:
    """
    均匀分布随机延迟

    参数:
        min_s: 最小延迟秒数
        max_s: 最大延迟秒数
    返回:
        实际延迟秒数
    """
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)
    return delay


def gaussian_delay(mean: float = 2.0, std: float = 0.5, min_val: float = 0.5, max_val: float = 10.0) -> float:
    """
    高斯分布延迟

    参数:
        mean: 均值
        std: 标准差
        min_val: 最小延迟（截断用）
        max_val: 最大延迟（截断用）
    返回:
        实际延迟秒数
    """
    delay = random.gauss(mean, std)
    delay = max(min_val, min(max_val, delay))
    time.sleep(delay)
    return delay


def typing_delay(text: str, min_interval: float = 0.05, max_interval: float = 0.15,
                 mistake_probability: float = 0.0) -> float:
    """
    模拟打字延迟（仅计算总延迟，实际逐字输入需在调用方实现）

    参数:
        text: 要输入的文本
        min_interval: 每个字符最小间隔
        max_interval: 每个字符最大间隔
        mistake_probability: 打错概率（预留）
    返回:
        预估总打字时间
    """
    config = get_anti_risk_config()
    if min_interval == 0.05 and max_interval == 0.15:
        min_interval = config.typing_speed.min_interval
        max_interval = config.typing_speed.max_interval

    total_delay = 0.0
    for char in text:
        char_delay = random.uniform(min_interval, max_interval)
        # 标点符号后稍长停顿
        if char in "，。！？、；：""''（）,.!?;:":
            char_delay += random.uniform(0.1, config.typing_speed.pause_after_punctuation)
        # 空格后偶尔有短暂思考
        elif char == " " and random.random() < 0.3:
            char_delay += random.uniform(0.1, 0.3)
        total_delay += char_delay

    return total_delay


def bezier_mouse_move(start: Tuple[int, int], end: Tuple[int, int],
                      duration: Optional[float] = None, steps: int = 20) -> list:
    """
    生成贝塞尔曲线鼠标移动路径

    参数:
        start: 起始坐标 (x, y)
        end: 结束坐标 (x, y)
        duration: 移动总时长（秒），None则自动计算
        steps: 路径点数量
    返回:
        路径点列表 [(x, y, sleep_time), ...]
    """
    config = get_anti_risk_config()

    if duration is None:
        distance = math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2)
        duration = random.uniform(
            config.mouse_behavior.move_speed_min,
            config.mouse_behavior.move_speed_max
        )
        duration = max(0.1, duration * (distance / 500.0))

    # 生成1-2个随机控制点
    cx1 = start[0] + (end[0] - start[0]) * random.uniform(0.2, 0.4) + random.randint(-50, 50)
    cy1 = start[1] + (end[1] - start[1]) * random.uniform(0.2, 0.4) + random.randint(-50, 50)
    cx2 = start[0] + (end[0] - start[0]) * random.uniform(0.6, 0.8) + random.randint(-30, 30)
    cy2 = start[1] + (end[1] - start[1]) * random.uniform(0.6, 0.8) + random.randint(-30, 30)

    path = []
    step_duration = duration / steps

    for i in range(steps + 1):
        t = i / steps
        # 三阶贝塞尔曲线
        u = 1 - t
        x = (u ** 3 * start[0] +
             3 * u ** 2 * t * cx1 +
             3 * u * t ** 2 * cx2 +
             t ** 3 * end[0])
        y = (u ** 3 * start[1] +
             3 * u ** 2 * t * cy1 +
             3 * u * t ** 2 * cy2 +
             t ** 3 * end[1])

        # 添加微小抖动模拟手部不稳定
        if 0 < i < steps:
            x += random.uniform(-1, 1)
            y += random.uniform(-1, 1)

        # 非均匀时间分布（开头和结尾慢，中间快）
        speed_factor = 1.0 - 0.5 * math.cos(2 * math.pi * t)
        sleep_time = step_duration * speed_factor

        path.append((int(x), int(y), sleep_time))

    return path


def execute_mouse_move(path: list) -> None:
    """
    执行鼠标移动路径

    参数:
        path: bezier_mouse_move 返回的路径列表
    """
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        for x, y, sleep_time in path:
            pyautogui.moveTo(x, y, _pause=False)
            time.sleep(sleep_time)
    except ImportError:
        logger.warning("pyautogui不可用，跳过鼠标移动")
    except Exception as e:
        logger.error(f"鼠标移动失败: {e}")


def fatigue_check(operation_count: Optional[int] = None) -> bool:
    """
    疲劳检查，判断是否需要休息

    参数:
        operation_count: 当前操作计数，None则使用内部计数
    返回:
        是否执行了休息
    """
    global _operation_count, _last_rest_time

    config = get_anti_risk_config()
    if not config.fatigue.enabled:
        return False

    if operation_count is not None:
        _operation_count = operation_count
    else:
        _operation_count += 1

    # 检查是否需要长休息
    if _operation_count >= config.fatigue.long_rest_after_operations:
        rest_time = random.randint(
            config.fatigue.long_rest_duration_min,
            config.fatigue.long_rest_duration_max
        )
        logger.info(f"已执行 {_operation_count} 次操作，进入长休息 {rest_time} 秒")
        time.sleep(rest_time)
        _operation_count = 0
        _last_rest_time = time.time()
        return True

    # 检查是否需要短休息
    if _operation_count >= config.fatigue.operations_before_rest:
        rest_time = random.randint(
            config.fatigue.rest_duration_min,
            config.fatigue.rest_duration_max
        )
        logger.info(f"已执行 {_operation_count} 次操作，休息 {rest_time} 秒")
        time.sleep(rest_time)
        _operation_count = 0
        _last_rest_time = time.time()
        return True

    return False


def is_work_hours() -> bool:
    """检查当前是否在工作时间内"""
    config = get_anti_risk_config()
    if not config.work_hours.enabled:
        return True

    import datetime
    now = datetime.datetime.now()
    hour = now.hour

    if hour < config.work_hours.start_hour or hour >= config.work_hours.end_hour:
        return False

    if config.work_hours.lunch_break_enabled:
        if config.work_hours.lunch_break_start <= hour < config.work_hours.lunch_break_end:
            return False

    return True


def smart_delay() -> float:
    """根据反风控配置执行智能延迟"""
    config = get_anti_risk_config()
    delay_config = config.operation_delay

    if delay_config.distribution == "gaussian":
        return gaussian_delay(
            mean=delay_config.mean,
            std=delay_config.std,
            min_val=delay_config.min_seconds,
            max_val=delay_config.max_seconds
        )
    else:
        return random_delay(delay_config.min_seconds, delay_config.max_seconds)


def reset_operation_count() -> None:
    """重置操作计数"""
    global _operation_count
    _operation_count = 0
