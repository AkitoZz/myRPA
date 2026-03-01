"""
全局配置管理模块

管理应用程序的所有全局设置，支持从配置文件加载和保存。
"""

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from loguru import logger


def _get_app_data_dir() -> Path:
    """获取应用数据目录"""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    app_dir = base / "MyRPA"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


@dataclass
class ServerConfig:
    """服务器配置"""
    api_url: str = "http://localhost:3000/api"
    ws_url: str = "ws://localhost:3000/ws"
    heartbeat_interval: int = 30
    request_timeout: int = 15
    max_retries: int = 3


@dataclass
class WeChatConfig:
    """微信相关配置"""
    supported_version: str = "3.9.10"
    min_version: str = "3.9.0"
    install_path: str = ""
    max_instances: int = 5
    window_class: str = "WeChatMainWndForPC"
    window_title: str = "微信"


@dataclass
class AntiRiskDefaults:
    """反风控默认配置"""
    min_delay: float = 1.0
    max_delay: float = 3.0
    typing_speed_min: float = 0.05
    typing_speed_max: float = 0.15
    daily_add_friend_limit: int = 30
    daily_mass_message_limit: int = 200
    operations_before_rest: int = 50
    rest_duration_min: int = 60
    rest_duration_max: int = 180
    work_hour_start: int = 8
    work_hour_end: int = 22


@dataclass
class LogConfig:
    """日志配置"""
    level: str = "DEBUG"
    console_level: str = "INFO"
    file_level: str = "DEBUG"
    log_dir: str = ""
    rotation: str = "10 MB"
    retention: str = "7 days"
    format: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} | {message}"

    def __post_init__(self):
        if not self.log_dir:
            self.log_dir = str(_get_app_data_dir() / "logs")


@dataclass
class UIConfig:
    """界面配置"""
    main_window_width: int = 900
    main_window_height: int = 650
    login_window_width: int = 400
    login_window_height: int = 350
    minimize_to_tray: bool = True
    theme: str = "default"


@dataclass
class Settings:
    """全局设置"""
    server: ServerConfig = field(default_factory=ServerConfig)
    wechat: WeChatConfig = field(default_factory=WeChatConfig)
    anti_risk: AntiRiskDefaults = field(default_factory=AntiRiskDefaults)
    log: LogConfig = field(default_factory=LogConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    remember_password: bool = False
    saved_phone: str = ""
    saved_password_hash: str = ""
    config_version: int = 1

    def save(self, path: Optional[str] = None):
        """保存设置到文件"""
        if path is None:
            path = str(_get_app_data_dir() / "settings.json")
        try:
            data = asdict(self)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"设置已保存到: {path}")
        except Exception as e:
            logger.error(f"保存设置失败: {e}")

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Settings":
        """从文件加载设置，不存在则使用默认值"""
        if path is None:
            path = str(_get_app_data_dir() / "settings.json")
        settings = cls()
        if not os.path.exists(path):
            logger.info("配置文件不存在，使用默认配置")
            settings.save(path)
            return settings
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            settings.server = ServerConfig(**data.get("server", {}))
            settings.wechat = WeChatConfig(**data.get("wechat", {}))
            settings.anti_risk = AntiRiskDefaults(**data.get("anti_risk", {}))
            settings.log = LogConfig(**data.get("log", {}))
            settings.ui = UIConfig(**data.get("ui", {}))
            settings.remember_password = data.get("remember_password", False)
            settings.saved_phone = data.get("saved_phone", "")
            settings.saved_password_hash = data.get("saved_password_hash", "")
            settings.config_version = data.get("config_version", 1)
            logger.info(f"已加载配置文件: {path}")
        except Exception as e:
            logger.warning(f"加载配置文件失败，使用默认配置: {e}")
            settings = cls()
        return settings


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局设置单例"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings.load()
    return _settings_instance


def reload_settings(path: Optional[str] = None) -> Settings:
    """重新加载设置"""
    global _settings_instance
    _settings_instance = Settings.load(path)
    return _settings_instance
