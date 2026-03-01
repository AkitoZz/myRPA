"""
反风控配置模块

定义各项操作的风控参数，包括延迟、限制和疲劳设置。
"""

from dataclasses import dataclass, field, asdict
from typing import Tuple
from enum import Enum


class DelayDistribution(Enum):
    """延迟分布类型"""
    UNIFORM = "uniform"
    GAUSSIAN = "gaussian"
    EXPONENTIAL = "exponential"


@dataclass
class OperationDelay:
    """操作延迟配置"""
    min_seconds: float = 1.0
    max_seconds: float = 3.0
    distribution: str = "gaussian"
    mean: float = 2.0
    std: float = 0.5

    def get_range(self) -> Tuple[float, float]:
        """获取延迟范围"""
        return (self.min_seconds, self.max_seconds)


@dataclass
class TypingSpeed:
    """打字速度配置"""
    min_interval: float = 0.05
    max_interval: float = 0.15
    mistake_probability: float = 0.02
    pause_after_punctuation: float = 0.3


@dataclass
class DailyLimits:
    """每日操作限制"""
    add_friend: int = 30
    mass_message: int = 200
    group_invite: int = 100
    auto_reply: int = 500
    search_contact: int = 100


@dataclass
class FatigueSettings:
    """疲劳控制设置"""
    operations_before_rest: int = 50
    rest_duration_min: int = 60
    rest_duration_max: int = 180
    long_rest_after_operations: int = 200
    long_rest_duration_min: int = 300
    long_rest_duration_max: int = 600
    enabled: bool = True


@dataclass
class WorkHours:
    """工作时间段配置"""
    start_hour: int = 8
    end_hour: int = 22
    enabled: bool = True
    lunch_break_start: int = 12
    lunch_break_end: int = 13
    lunch_break_enabled: bool = False


@dataclass
class MouseBehavior:
    """鼠标行为配置"""
    move_speed_min: float = 0.3
    move_speed_max: float = 0.8
    use_bezier_curve: bool = True
    click_offset_range: int = 3
    double_click_interval: float = 0.1


@dataclass
class AntiRiskConfig:
    """反风控总配置"""
    operation_delay: OperationDelay = field(default_factory=OperationDelay)
    typing_speed: TypingSpeed = field(default_factory=TypingSpeed)
    daily_limits: DailyLimits = field(default_factory=DailyLimits)
    fatigue: FatigueSettings = field(default_factory=FatigueSettings)
    work_hours: WorkHours = field(default_factory=WorkHours)
    mouse_behavior: MouseBehavior = field(default_factory=MouseBehavior)
    random_window_switch: bool = True
    random_scroll: bool = True
    enabled: bool = True

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AntiRiskConfig":
        """从字典创建"""
        config = cls()
        if "operation_delay" in data:
            config.operation_delay = OperationDelay(**data["operation_delay"])
        if "typing_speed" in data:
            config.typing_speed = TypingSpeed(**data["typing_speed"])
        if "daily_limits" in data:
            config.daily_limits = DailyLimits(**data["daily_limits"])
        if "fatigue" in data:
            config.fatigue = FatigueSettings(**data["fatigue"])
        if "work_hours" in data:
            config.work_hours = WorkHours(**data["work_hours"])
        if "mouse_behavior" in data:
            config.mouse_behavior = MouseBehavior(**data["mouse_behavior"])
        config.random_window_switch = data.get("random_window_switch", True)
        config.random_scroll = data.get("random_scroll", True)
        config.enabled = data.get("enabled", True)
        return config

    @classmethod
    def conservative(cls) -> "AntiRiskConfig":
        """保守模式 - 更安全的配置"""
        config = cls()
        config.operation_delay = OperationDelay(
            min_seconds=2.0, max_seconds=5.0, mean=3.5, std=0.8
        )
        config.typing_speed = TypingSpeed(
            min_interval=0.08, max_interval=0.2, mistake_probability=0.03
        )
        config.daily_limits = DailyLimits(
            add_friend=15, mass_message=100, group_invite=50
        )
        config.fatigue = FatigueSettings(
            operations_before_rest=30, rest_duration_min=120, rest_duration_max=300
        )
        return config

    @classmethod
    def aggressive(cls) -> "AntiRiskConfig":
        """激进模式 - 更快但风险更高"""
        config = cls()
        config.operation_delay = OperationDelay(
            min_seconds=0.5, max_seconds=1.5, mean=1.0, std=0.3
        )
        config.typing_speed = TypingSpeed(
            min_interval=0.03, max_interval=0.08, mistake_probability=0.0
        )
        config.daily_limits = DailyLimits(
            add_friend=50, mass_message=500, group_invite=200
        )
        config.fatigue = FatigueSettings(
            operations_before_rest=100, rest_duration_min=30, rest_duration_max=60
        )
        return config
