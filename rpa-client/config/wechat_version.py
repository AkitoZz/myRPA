"""
微信版本检测与兼容性管理模块

检测系统中安装的微信版本，验证与RPA系统的兼容性。
"""

import os
import sys
import re
from dataclasses import dataclass
from typing import Optional, Tuple
from pathlib import Path

from loguru import logger


@dataclass
class VersionInfo:
    """版本信息"""
    major: int
    minor: int
    patch: int
    build: int = 0

    def __str__(self) -> str:
        if self.build > 0:
            return f"{self.major}.{self.minor}.{self.patch}.{self.build}"
        return f"{self.major}.{self.minor}.{self.patch}"

    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (self.major, self.minor, self.patch, self.build)

    def __ge__(self, other: "VersionInfo") -> bool:
        return self.as_tuple() >= other.as_tuple()

    def __le__(self, other: "VersionInfo") -> bool:
        return self.as_tuple() <= other.as_tuple()

    def __gt__(self, other: "VersionInfo") -> bool:
        return self.as_tuple() > other.as_tuple()

    def __lt__(self, other: "VersionInfo") -> bool:
        return self.as_tuple() < other.as_tuple()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return self.as_tuple() == other.as_tuple()


def parse_version(version_str: str) -> VersionInfo:
    """解析版本号字符串为VersionInfo对象"""
    parts = version_str.strip().split(".")
    if len(parts) < 3:
        raise ValueError(f"无效的版本号格式: {version_str}")
    major = int(parts[0])
    minor = int(parts[1])
    patch = int(parts[2])
    build = int(parts[3]) if len(parts) > 3 else 0
    return VersionInfo(major=major, minor=minor, patch=patch, build=build)


class WeChatVersionManager:
    """微信版本管理器"""

    MIN_SUPPORTED_VERSION = "3.9.0"
    MAX_TESTED_VERSION = "3.9.10"
    RECOMMENDED_VERSION = "3.9.10"

    # 微信常见安装路径
    DEFAULT_INSTALL_PATHS = [
        r"C:\Program Files (x86)\Tencent\WeChat",
        r"C:\Program Files\Tencent\WeChat",
        r"D:\Program Files (x86)\Tencent\WeChat",
        r"D:\Program Files\Tencent\WeChat",
        r"D:\Tencent\WeChat",
        r"C:\Tencent\WeChat",
    ]

    def __init__(self):
        self._detected_version: Optional[VersionInfo] = None
        self._install_path: Optional[str] = None

    def detect_install_path(self) -> Optional[str]:
        """检测微信安装路径"""
        if sys.platform != "win32":
            logger.warning("非Windows平台，无法检测微信安装路径")
            return None

        # 尝试从注册表读取
        try:
            import winreg
            key_paths = [
                r"SOFTWARE\Tencent\WeChat",
                r"SOFTWARE\WOW6432Node\Tencent\WeChat",
            ]
            for key_path in key_paths:
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path)
                    install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                    winreg.CloseKey(key)
                    if os.path.exists(install_path):
                        self._install_path = install_path
                        logger.info(f"从注册表检测到微信安装路径: {install_path}")
                        return install_path
                except FileNotFoundError:
                    continue
                except Exception as e:
                    logger.debug(f"读取注册表失败: {e}")
                    continue
        except ImportError:
            logger.debug("winreg模块不可用")

        # 尝试常见路径
        for path in self.DEFAULT_INSTALL_PATHS:
            wechat_exe = os.path.join(path, "WeChat.exe")
            if os.path.exists(wechat_exe):
                self._install_path = path
                logger.info(f"从默认路径检测到微信: {path}")
                return path

        logger.warning("未检测到微信安装路径")
        return None

    def detect_version(self) -> Optional[VersionInfo]:
        """检测已安装微信的版本"""
        if sys.platform != "win32":
            logger.warning("非Windows平台，返回模拟版本")
            self._detected_version = parse_version(self.RECOMMENDED_VERSION)
            return self._detected_version

        install_path = self._install_path or self.detect_install_path()
        if not install_path:
            return None

        # 方法1: 读取WeChat.exe文件版本信息
        try:
            import win32api
            wechat_exe = os.path.join(install_path, "WeChat.exe")
            if os.path.exists(wechat_exe):
                info = win32api.GetFileVersionInfo(wechat_exe, "\\")
                ms = info["FileVersionMS"]
                ls = info["FileVersionLS"]
                version = VersionInfo(
                    major=ms >> 16,
                    minor=ms & 0xFFFF,
                    patch=ls >> 16,
                    build=ls & 0xFFFF,
                )
                self._detected_version = version
                logger.info(f"检测到微信版本: {version}")
                return version
        except ImportError:
            logger.debug("win32api不可用，尝试其他方法")
        except Exception as e:
            logger.debug(f"通过win32api获取版本失败: {e}")

        # 方法2: 从目录结构判断版本
        try:
            version_dirs = []
            for item in os.listdir(install_path):
                item_path = os.path.join(install_path, item)
                if os.path.isdir(item_path) and re.match(r"\[\d+\.\d+\.\d+", item):
                    match = re.search(r"(\d+\.\d+\.\d+(?:\.\d+)?)", item)
                    if match:
                        version_dirs.append(match.group(1))
            if version_dirs:
                version_dirs.sort(key=lambda v: tuple(int(x) for x in v.split(".")), reverse=True)
                version = parse_version(version_dirs[0])
                self._detected_version = version
                logger.info(f"从目录结构检测到微信版本: {version}")
                return version
        except Exception as e:
            logger.debug(f"从目录结构获取版本失败: {e}")

        logger.warning("无法检测微信版本")
        return None

    def check_compatibility(self, version: Optional[VersionInfo] = None) -> Tuple[bool, str]:
        """
        检查版本兼容性

        返回:
            (是否兼容, 说明信息)
        """
        if version is None:
            version = self._detected_version or self.detect_version()

        if version is None:
            return False, "无法检测微信版本，请确认微信已安装"

        min_ver = parse_version(self.MIN_SUPPORTED_VERSION)
        max_ver = parse_version(self.MAX_TESTED_VERSION)

        if version < min_ver:
            return False, f"微信版本 {version} 过低，最低支持版本为 {self.MIN_SUPPORTED_VERSION}"

        if version > max_ver:
            return True, f"微信版本 {version} 高于已测试版本 {self.MAX_TESTED_VERSION}，可能存在兼容性问题"

        return True, f"微信版本 {version} 兼容"

    def get_element_config_path(self, version: Optional[VersionInfo] = None) -> Optional[str]:
        """获取对应版本的元素配置文件路径"""
        if version is None:
            version = self._detected_version

        if version is None:
            version = parse_version(self.RECOMMENDED_VERSION)

        # 查找最匹配的版本配置
        base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "wechat_elements")

        # 精确匹配
        exact_path = os.path.join(base_dir, f"v{version.major}.{version.minor}.{version.patch}.json")
        if os.path.exists(exact_path):
            return exact_path

        # 查找最接近的低版本配置
        best_match = None
        best_version = None
        if os.path.exists(base_dir):
            for filename in os.listdir(base_dir):
                if filename.endswith(".json") and filename.startswith("v"):
                    try:
                        ver_str = filename[1:-5]  # 去掉 v 和 .json
                        ver = parse_version(ver_str)
                        if ver <= version and (best_version is None or ver > best_version):
                            best_version = ver
                            best_match = os.path.join(base_dir, filename)
                    except ValueError:
                        continue

        if best_match:
            logger.info(f"使用版本配置文件: {best_match}")
            return best_match

        logger.warning("未找到匹配的版本配置文件")
        return None

    @property
    def version(self) -> Optional[VersionInfo]:
        """获取检测到的版本"""
        return self._detected_version

    @property
    def install_path(self) -> Optional[str]:
        """获取安装路径"""
        return self._install_path
