"""
截图与图像识别模块

提供窗口截图、区域截图、模板匹配和OCR功能。
"""

import os
import sys
import time
from typing import Optional, Tuple, List

import numpy as np
from PIL import Image
from loguru import logger

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV不可用，图像匹配功能将被禁用")

IS_WINDOWS = sys.platform == "win32"


class ScreenshotManager:
    """截图与图像识别管理器"""

    def __init__(self):
        self._screenshot_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "resources", "screenshots"
        )
        os.makedirs(self._screenshot_dir, exist_ok=True)

    def capture_window(self, hwnd: int = 0) -> Optional[np.ndarray]:
        """
        截取指定窗口的图像

        参数:
            hwnd: 窗口句柄，0表示整个屏幕
        返回:
            numpy数组格式的图像，失败返回None
        """
        if IS_WINDOWS and hwnd != 0:
            return self._capture_window_win32(hwnd)
        return self._capture_screen()

    def _capture_window_win32(self, hwnd: int) -> Optional[np.ndarray]:
        """Windows平台窗口截图"""
        try:
            import win32gui
            import win32ui
            import win32con

            # 获取窗口尺寸
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            if width <= 0 or height <= 0:
                logger.error(f"窗口尺寸无效: {width}x{height}")
                return None

            # 创建设备上下文
            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()

            # 创建位图
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)

            # 截图
            save_dc.BitBlt(
                (0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY
            )

            # 转换为numpy数组
            bmp_info = bitmap.GetInfo()
            bmp_data = bitmap.GetBitmapBits(True)
            img = np.frombuffer(bmp_data, dtype=np.uint8)
            img = img.reshape((bmp_info["bmHeight"], bmp_info["bmWidth"], 4))
            img = img[:, :, :3]  # 去掉alpha通道
            img = img[:, :, ::-1]  # BGR -> RGB

            # 清理资源
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)
            win32gui.DeleteObject(bitmap.GetHandle())

            logger.debug(f"窗口截图成功: {width}x{height}")
            return img

        except ImportError:
            logger.warning("win32gui不可用，使用屏幕截图代替")
            return self._capture_screen()
        except Exception as e:
            logger.error(f"窗口截图失败: {e}")
            return None

    def _capture_screen(self) -> Optional[np.ndarray]:
        """屏幕截图（跨平台）"""
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            img = np.array(screenshot)
            logger.debug(f"屏幕截图成功: {img.shape[1]}x{img.shape[0]}")
            return img
        except Exception as e:
            logger.error(f"屏幕截图失败: {e}")
            return None

    def capture_region(self, x: int, y: int, w: int, h: int) -> Optional[np.ndarray]:
        """
        截取屏幕指定区域

        参数:
            x: 左上角x坐标
            y: 左上角y坐标
            w: 宽度
            h: 高度
        返回:
            numpy数组格式的图像
        """
        try:
            import pyautogui
            screenshot = pyautogui.screenshot(region=(x, y, w, h))
            img = np.array(screenshot)
            logger.debug(f"区域截图成功: ({x},{y}) {w}x{h}")
            return img
        except Exception as e:
            logger.error(f"区域截图失败: {e}")
            return None

    def find_template(
        self,
        screenshot: np.ndarray,
        template: np.ndarray,
        threshold: float = 0.8,
    ) -> Optional[Tuple[int, int, float]]:
        """
        模板匹配 - 在截图中查找模板图像

        参数:
            screenshot: 截图图像
            template: 模板图像
            threshold: 匹配阈值（0-1）
        返回:
            (x, y, confidence) 匹配位置和置信度，未找到返回None
        """
        if not CV2_AVAILABLE:
            logger.error("OpenCV不可用，无法执行模板匹配")
            return None

        try:
            # 确保图像格式正确
            if len(screenshot.shape) == 3:
                screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
            else:
                screenshot_gray = screenshot

            if len(template.shape) == 3:
                template_gray = cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)
            else:
                template_gray = template

            # 模板匹配
            result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            if max_val >= threshold:
                # 返回模板中心坐标
                h, w = template_gray.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                logger.debug(f"模板匹配成功: ({center_x},{center_y}) 置信度={max_val:.3f}")
                return (center_x, center_y, max_val)
            else:
                logger.debug(f"模板匹配失败: 最高置信度={max_val:.3f} < 阈值{threshold}")
                return None

        except Exception as e:
            logger.error(f"模板匹配异常: {e}")
            return None

    def find_all_templates(
        self,
        screenshot: np.ndarray,
        template: np.ndarray,
        threshold: float = 0.8,
        max_count: int = 50,
    ) -> List[Tuple[int, int, float]]:
        """
        查找所有匹配位置

        参数:
            screenshot: 截图图像
            template: 模板图像
            threshold: 匹配阈值
            max_count: 最大返回数量
        返回:
            匹配位置列表 [(x, y, confidence), ...]
        """
        if not CV2_AVAILABLE:
            logger.error("OpenCV不可用，无法执行模板匹配")
            return []

        try:
            if len(screenshot.shape) == 3:
                screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
            else:
                screenshot_gray = screenshot

            if len(template.shape) == 3:
                template_gray = cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)
            else:
                template_gray = template

            h, w = template_gray.shape[:2]
            result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)

            locations = np.where(result >= threshold)
            matches = []

            for pt_y, pt_x in zip(*locations):
                center_x = pt_x + w // 2
                center_y = pt_y + h // 2
                confidence = result[pt_y, pt_x]
                matches.append((center_x, center_y, float(confidence)))

            # 非极大值抑制 - 合并相近的匹配点
            if matches:
                matches = self._nms(matches, w, h)

            matches.sort(key=lambda m: m[2], reverse=True)
            matches = matches[:max_count]

            logger.debug(f"找到 {len(matches)} 个匹配位置")
            return matches

        except Exception as e:
            logger.error(f"批量模板匹配异常: {e}")
            return []

    def _nms(
        self, matches: List[Tuple[int, int, float]], w: int, h: int
    ) -> List[Tuple[int, int, float]]:
        """非极大值抑制，去除重叠匹配"""
        if not matches:
            return []

        matches.sort(key=lambda m: m[2], reverse=True)
        result = []
        used = set()

        for i, (x1, y1, c1) in enumerate(matches):
            if i in used:
                continue
            result.append((x1, y1, c1))
            for j, (x2, y2, c2) in enumerate(matches[i + 1:], i + 1):
                if j in used:
                    continue
                if abs(x1 - x2) < w // 2 and abs(y1 - y2) < h // 2:
                    used.add(j)

        return result

    def ocr_region(self, image: np.ndarray, region: Optional[Tuple[int, int, int, int]] = None) -> str:
        """
        OCR文字识别（基础实现）

        参数:
            image: 图像数据
            region: 可选区域 (x, y, w, h)
        返回:
            识别到的文本
        """
        if region is not None:
            x, y, w, h = region
            image = image[y:y + h, x:x + w]

        # 基础OCR实现 - 使用图像预处理
        # 如需高精度OCR，建议集成Tesseract或百度OCR等
        logger.debug("执行OCR识别（基础模式）")

        try:
            # 尝试使用pytesseract
            import pytesseract
            if len(image.shape) == 3:
                pil_image = Image.fromarray(image)
            else:
                pil_image = Image.fromarray(image)
            text = pytesseract.image_to_string(pil_image, lang="chi_sim+eng")
            return text.strip()
        except ImportError:
            logger.warning("pytesseract不可用，OCR功能受限")
            return ""
        except Exception as e:
            logger.error(f"OCR识别失败: {e}")
            return ""

    def save_screenshot(self, image: np.ndarray, filename: Optional[str] = None) -> str:
        """
        保存截图到文件

        参数:
            image: 图像数据
            filename: 文件名，为空则自动生成
        返回:
            保存的文件路径
        """
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"

        filepath = os.path.join(self._screenshot_dir, filename)

        try:
            pil_image = Image.fromarray(image)
            pil_image.save(filepath)
            logger.debug(f"截图已保存: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"保存截图失败: {e}")
            return ""

    def load_template(self, template_path: str) -> Optional[np.ndarray]:
        """
        加载模板图像

        参数:
            template_path: 模板图像路径
        返回:
            numpy数组格式的图像
        """
        if not os.path.exists(template_path):
            logger.error(f"模板图像不存在: {template_path}")
            return None

        try:
            if CV2_AVAILABLE:
                img = cv2.imread(template_path)
                if img is not None:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                return img
            else:
                pil_img = Image.open(template_path)
                return np.array(pil_img)
        except Exception as e:
            logger.error(f"加载模板图像失败: {e}")
            return None
