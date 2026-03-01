"""
UI元素定位器模块

提供三级元素定位策略：UIA控件树 → 图像模板匹配 → OCR文字识别。
"""

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple, List
from functools import lru_cache

import numpy as np
from loguru import logger

from core.screenshot import ScreenshotManager

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    try:
        import pywinauto
        from pywinauto import Desktop
        PYWINAUTO_AVAILABLE = True
    except ImportError:
        PYWINAUTO_AVAILABLE = False
else:
    PYWINAUTO_AVAILABLE = False


@dataclass
class ElementConfig:
    """UI元素配置"""
    name: str = ""
    uia: Dict[str, str] = field(default_factory=dict)
    image: str = ""
    ocr_text: str = ""
    offset_x: int = 0
    offset_y: int = 0
    description: str = ""

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "ElementConfig":
        """从字典创建元素配置"""
        return cls(
            name=name,
            uia=data.get("uia", {}),
            image=data.get("image", ""),
            ocr_text=data.get("ocr_text", ""),
            offset_x=data.get("offset_x", 0),
            offset_y=data.get("offset_y", 0),
            description=data.get("description", ""),
        )


@dataclass
class LocateResult:
    """定位结果"""
    found: bool = False
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    confidence: float = 0.0
    strategy: str = ""
    element: Any = None

    @property
    def center(self) -> Tuple[int, int]:
        """返回元素中心坐标"""
        return (self.x + self.width // 2, self.y + self.height // 2)


class ElementLocator:
    """UI元素定位器"""

    def __init__(self, wechat_window=None):
        """
        初始化定位器

        参数:
            wechat_window: pywinauto窗口对象
        """
        self._window = wechat_window
        self._screenshot_mgr = ScreenshotManager()
        self._element_configs: Dict[str, ElementConfig] = {}
        self._position_cache: Dict[str, Tuple[int, int, float]] = {}
        self._cache_ttl = 5.0  # 缓存有效期（秒）
        self._template_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "resources", "templates"
        )

    def set_window(self, window) -> None:
        """设置目标窗口"""
        self._window = window

    def load_element_configs(self, config_path: str) -> bool:
        """
        从JSON文件加载元素配置

        参数:
            config_path: 配置文件路径
        返回:
            是否加载成功
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            elements = data.get("elements", {})
            self._element_configs.clear()

            for name, config in elements.items():
                self._element_configs[name] = ElementConfig.from_dict(name, config)

            logger.info(f"已加载 {len(self._element_configs)} 个元素配置")
            return True

        except FileNotFoundError:
            logger.error(f"元素配置文件不存在: {config_path}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"元素配置文件格式错误: {e}")
            return False
        except Exception as e:
            logger.error(f"加载元素配置失败: {e}")
            return False

    def get_element_config(self, element_name: str) -> Optional[ElementConfig]:
        """获取元素配置"""
        return self._element_configs.get(element_name)

    def locate(self, element_config: ElementConfig, retry: int = 2, use_cache: bool = True) -> LocateResult:
        """
        定位UI元素（三级策略）

        依次尝试: UIA控件树 → 图像模板匹配 → OCR文字识别

        参数:
            element_config: 元素配置
            retry: 重试次数
            use_cache: 是否使用缓存
        返回:
            定位结果
        """
        element_name = element_config.name

        # 检查缓存
        if use_cache and element_name in self._position_cache:
            cached_x, cached_y, cached_time = self._position_cache[element_name]
            if time.time() - cached_time < self._cache_ttl:
                logger.debug(f"使用缓存位置: {element_name} ({cached_x}, {cached_y})")
                return LocateResult(
                    found=True, x=cached_x, y=cached_y,
                    strategy="cache", confidence=1.0
                )

        for attempt in range(retry + 1):
            if attempt > 0:
                logger.debug(f"第 {attempt + 1} 次尝试定位: {element_name}")
                time.sleep(0.5)

            # 策略1: UIA控件树
            if element_config.uia and PYWINAUTO_AVAILABLE:
                result = self.find_by_uia(
                    control_type=element_config.uia.get("control_type", ""),
                    name=element_config.uia.get("name", ""),
                    auto_id=element_config.uia.get("auto_id", ""),
                )
                if result.found:
                    result.x += element_config.offset_x
                    result.y += element_config.offset_y
                    self._update_cache(element_name, result.x, result.y)
                    return result

            # 策略2: 图像模板匹配
            if element_config.image:
                result = self.find_by_image(
                    template_path=element_config.image,
                    threshold=0.8,
                )
                if result.found:
                    result.x += element_config.offset_x
                    result.y += element_config.offset_y
                    self._update_cache(element_name, result.x, result.y)
                    return result

            # 策略3: OCR文字识别
            if element_config.ocr_text:
                result = self.find_by_ocr(
                    text=element_config.ocr_text,
                )
                if result.found:
                    result.x += element_config.offset_x
                    result.y += element_config.offset_y
                    self._update_cache(element_name, result.x, result.y)
                    return result

        logger.warning(f"无法定位元素: {element_name}")
        return LocateResult(found=False)

    def locate_by_name(self, element_name: str, retry: int = 2) -> LocateResult:
        """
        通过元素名称定位

        参数:
            element_name: 在配置中的元素名称
            retry: 重试次数
        返回:
            定位结果
        """
        config = self._element_configs.get(element_name)
        if config is None:
            logger.error(f"未找到元素配置: {element_name}")
            return LocateResult(found=False)
        return self.locate(config, retry=retry)

    def find_by_uia(
        self,
        control_type: str = "",
        name: str = "",
        auto_id: str = "",
        class_name: str = "",
    ) -> LocateResult:
        """
        通过UIA控件树定位元素

        参数:
            control_type: 控件类型 (Button, Edit, Text等)
            name: 控件名称
            auto_id: 自动化ID
            class_name: 类名
        返回:
            定位结果
        """
        if not PYWINAUTO_AVAILABLE:
            return LocateResult(found=False, strategy="uia")

        if self._window is None:
            logger.warning("窗口对象未设置，无法使用UIA定位")
            return LocateResult(found=False, strategy="uia")

        try:
            # 构建搜索条件
            search_criteria = {}
            if control_type:
                search_criteria["control_type"] = control_type
            if name:
                search_criteria["title"] = name
            if auto_id:
                search_criteria["auto_id"] = auto_id
            if class_name:
                search_criteria["class_name"] = class_name

            if not search_criteria:
                return LocateResult(found=False, strategy="uia")

            # 查找元素
            element = self._window.child_window(**search_criteria)

            if element.exists(timeout=0.5):
                rect = element.rectangle()
                result = LocateResult(
                    found=True,
                    x=rect.left,
                    y=rect.top,
                    width=rect.width(),
                    height=rect.height(),
                    confidence=1.0,
                    strategy="uia",
                    element=element,
                )
                logger.debug(f"UIA定位成功: {search_criteria} -> ({result.x},{result.y})")
                return result
            else:
                logger.debug(f"UIA定位未找到: {search_criteria}")
                return LocateResult(found=False, strategy="uia")

        except Exception as e:
            logger.debug(f"UIA定位异常: {e}")
            return LocateResult(found=False, strategy="uia")

    def find_by_image(
        self,
        template_path: str,
        threshold: float = 0.8,
        hwnd: int = 0,
    ) -> LocateResult:
        """
        通过图像模板匹配定位元素

        参数:
            template_path: 模板图像路径（相对或绝对）
            threshold: 匹配阈值
            hwnd: 窗口句柄
        返回:
            定位结果
        """
        # 处理模板路径
        if not os.path.isabs(template_path):
            template_path = os.path.join(self._template_dir, template_path)

        template = self._screenshot_mgr.load_template(template_path)
        if template is None:
            return LocateResult(found=False, strategy="image")

        # 截图
        screenshot = self._screenshot_mgr.capture_window(hwnd)
        if screenshot is None:
            return LocateResult(found=False, strategy="image")

        # 模板匹配
        match = self._screenshot_mgr.find_template(screenshot, template, threshold)
        if match is not None:
            x, y, confidence = match
            h, w = template.shape[:2]
            result = LocateResult(
                found=True,
                x=x - w // 2,
                y=y - h // 2,
                width=w,
                height=h,
                confidence=confidence,
                strategy="image",
            )
            logger.debug(f"图像匹配成功: {os.path.basename(template_path)} -> ({x},{y}) conf={confidence:.3f}")
            return result

        return LocateResult(found=False, strategy="image")

    def find_by_ocr(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        hwnd: int = 0,
    ) -> LocateResult:
        """
        通过OCR文字识别定位元素

        参数:
            text: 要查找的文本
            region: 搜索区域 (x, y, w, h)
            hwnd: 窗口句柄
        返回:
            定位结果
        """
        # 截图
        screenshot = self._screenshot_mgr.capture_window(hwnd)
        if screenshot is None:
            return LocateResult(found=False, strategy="ocr")

        # OCR识别
        ocr_text = self._screenshot_mgr.ocr_region(screenshot, region)
        if text in ocr_text:
            # 粗略定位 - OCR通常不提供精确坐标
            # 这里返回一个基于区域的近似位置
            if region:
                center_x = region[0] + region[2] // 2
                center_y = region[1] + region[3] // 2
            else:
                center_x = screenshot.shape[1] // 2
                center_y = screenshot.shape[0] // 2

            result = LocateResult(
                found=True,
                x=center_x,
                y=center_y,
                confidence=0.6,
                strategy="ocr",
            )
            logger.debug(f"OCR定位成功: '{text}' -> ({center_x},{center_y})")
            return result

        logger.debug(f"OCR定位未找到: '{text}'")
        return LocateResult(found=False, strategy="ocr")

    def _update_cache(self, element_name: str, x: int, y: int) -> None:
        """更新位置缓存"""
        self._position_cache[element_name] = (x, y, time.time())

    def clear_cache(self) -> None:
        """清除位置缓存"""
        self._position_cache.clear()
        logger.debug("元素位置缓存已清除")

    def wait_for_element(
        self,
        element_config: ElementConfig,
        timeout: float = 10.0,
        interval: float = 0.5,
    ) -> LocateResult:
        """
        等待元素出现

        参数:
            element_config: 元素配置
            timeout: 超时时间（秒）
            interval: 检查间隔（秒）
        返回:
            定位结果
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.locate(element_config, retry=0, use_cache=False)
            if result.found:
                return result
            time.sleep(interval)

        logger.warning(f"等待元素超时: {element_config.name} ({timeout}s)")
        return LocateResult(found=False)

    def wait_for_element_by_name(
        self, element_name: str, timeout: float = 10.0
    ) -> LocateResult:
        """
        通过名称等待元素出现

        参数:
            element_name: 元素名称
            timeout: 超时时间
        返回:
            定位结果
        """
        config = self._element_configs.get(element_name)
        if config is None:
            logger.error(f"未找到元素配置: {element_name}")
            return LocateResult(found=False)
        return self.wait_for_element(config, timeout=timeout)
