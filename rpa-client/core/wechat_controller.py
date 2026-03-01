"""
微信窗口控制器模块

核心模块，通过pywinauto操控微信PC客户端，提供搜索联系人、发送消息等功能。
"""

import os
import sys
import time
from typing import Optional, List, Dict, Any

import pyautogui
from loguru import logger

from core.element_locator import ElementLocator, ElementConfig, LocateResult
from core.screenshot import ScreenshotManager
from utils.delay import random_delay, gaussian_delay, smart_delay, bezier_mouse_move, execute_mouse_move

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    try:
        import pywinauto
        from pywinauto import Application, Desktop
        from pywinauto.findwindows import find_windows, ElementNotFoundError
        import win32gui
        import win32con
        import win32process
        import win32api
        PYWINAUTO_AVAILABLE = True
    except ImportError:
        PYWINAUTO_AVAILABLE = False
        logger.warning("pywinauto或pywin32不可用，微信控制功能将被禁用")
else:
    PYWINAUTO_AVAILABLE = False
    logger.info("非Windows平台，微信控制功能仅为模拟模式")


pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


class WeChatController:
    """微信窗口控制器"""

    WECHAT_CLASS_NAME = "WeChatMainWndForPC"
    WECHAT_CLASS_NAME_QT = "Qt51514QWindowIcon"
    WECHAT_TITLE = "微信"

    def __init__(self):
        self._app: Optional[Any] = None
        self._main_window: Optional[Any] = None
        self._hwnd: int = 0
        self._pid: int = 0
        self._connected: bool = False
        self._locator = ElementLocator()
        self._screenshot_mgr = ScreenshotManager()

    @property
    def is_connected(self) -> bool:
        """是否已连接微信"""
        return self._connected and self._main_window is not None

    @property
    def hwnd(self) -> int:
        """获取窗口句柄"""
        return self._hwnd

    @property
    def pid(self) -> int:
        """获取进程ID"""
        return self._pid

    def find_wechat_window(self) -> Optional[int]:
        """
        查找微信主窗口

        返回:
            窗口句柄，未找到返回None
        """
        if not IS_WINDOWS:
            logger.warning("非Windows平台，无法查找微信窗口")
            return None

        if not PYWINAUTO_AVAILABLE:
            logger.error("pywinauto不可用")
            return None

        try:
            # 方案1：经典类名
            hwnds = find_windows(class_name=self.WECHAT_CLASS_NAME)
            if hwnds:
                self._hwnd = hwnds[0]
                logger.info(f"找到微信窗口(经典): hwnd={self._hwnd}")
                return self._hwnd

            # 方案2：新版微信 Qt 类名 + 标题匹配
            hwnds = find_windows(class_name=self.WECHAT_CLASS_NAME_QT)
            for hwnd in hwnds:
                title = win32gui.GetWindowText(hwnd)
                if title == self.WECHAT_TITLE:
                    self._hwnd = hwnd
                    logger.info(f"找到微信窗口(Qt): hwnd={self._hwnd}, title={title}")
                    return self._hwnd

            # 方案3：通过窗口标题兜底
            hwnds = find_windows(title=self.WECHAT_TITLE)
            for hwnd in hwnds:
                class_name = win32gui.GetClassName(hwnd)
                if "WeChat" in class_name or "Qt" in class_name:
                    self._hwnd = hwnd
                    logger.info(f"通过标题找到微信窗口: hwnd={self._hwnd}, class={class_name}")
                    return self._hwnd

            logger.warning("未找到微信窗口")
            return None

        except Exception as e:
            logger.error(f"查找微信窗口失败: {e}")
            return None

    def connect(self, pid: Optional[int] = None) -> bool:
        """
        连接到微信实例

        参数:
            pid: 微信进程ID，为空则自动查找
        返回:
            是否连接成功
        """
        if not IS_WINDOWS or not PYWINAUTO_AVAILABLE:
            logger.warning("当前平台不支持连接微信")
            return False

        try:
            if pid is not None:
                # 通过PID连接
                self._app = Application(backend="uia").connect(process=pid)
                self._pid = pid
            else:
                # 自动查找
                hwnd = self.find_wechat_window()
                if hwnd is None:
                    return False
                _, pid_found = win32process.GetWindowThreadProcessId(hwnd)
                self._app = Application(backend="uia").connect(process=pid_found)
                self._pid = pid_found

            # 获取主窗口（兼容经典和Qt新版）
            self._main_window = self._app.window(class_name=self.WECHAT_CLASS_NAME)
            if not self._main_window.exists(timeout=3):
                self._main_window = self._app.window(class_name=self.WECHAT_CLASS_NAME_QT, title=self.WECHAT_TITLE)

            if not self._main_window.exists(timeout=5):
                logger.error("微信主窗口不存在或无法访问")
                return False

            self._hwnd = self._main_window.handle
            self._locator.set_window(self._main_window)
            self._connected = True

            logger.info(f"已连接到微信: PID={self._pid}, HWND={self._hwnd}")
            return True

        except Exception as e:
            logger.error(f"连接微信失败: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """断开与微信的连接"""
        self._app = None
        self._main_window = None
        self._hwnd = 0
        self._pid = 0
        self._connected = False
        self._locator.set_window(None)
        logger.info("已断开微信连接")

    def load_element_configs(self, config_path: str) -> bool:
        """
        加载UI元素配置

        参数:
            config_path: 元素配置文件路径
        返回:
            是否加载成功
        """
        return self._locator.load_element_configs(config_path)

    def _ensure_foreground(self) -> bool:
        """确保微信窗口在前台"""
        if not self._connected or self._main_window is None:
            return False

        try:
            if IS_WINDOWS:
                # 如果窗口最小化，先恢复
                if win32gui.IsIconic(self._hwnd):
                    win32gui.ShowWindow(self._hwnd, win32con.SW_RESTORE)
                    time.sleep(0.3)

                # 置前
                win32gui.SetForegroundWindow(self._hwnd)
                time.sleep(0.2)
            return True
        except Exception as e:
            logger.error(f"无法将微信窗口置前: {e}")
            return False

    def search_contact(self, keyword: str, max_retry: int = 3) -> bool:
        """
        使用搜索框搜索联系人

        参数:
            keyword: 搜索关键词（手机号/微信号/昵称）
            max_retry: 最大重试次数
        返回:
            是否搜索成功
        """
        if not self._ensure_connected():
            return False

        for attempt in range(max_retry):
            try:
                self._ensure_foreground()
                smart_delay()

                # 点击搜索框 - 使用 Ctrl+F 快捷键更可靠
                if IS_WINDOWS:
                    pyautogui.hotkey("ctrl", "f")
                else:
                    pyautogui.hotkey("command", "f")
                time.sleep(0.5)

                # 清除已有内容
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.1)

                # 输入搜索关键词
                self._type_text(keyword)
                time.sleep(1.0)

                logger.info(f"搜索联系人: {keyword}")
                return True

            except Exception as e:
                logger.error(f"搜索联系人失败 (第{attempt + 1}次): {e}")
                if attempt < max_retry - 1:
                    time.sleep(1)

        return False

    def open_chat(self, contact_name: str, max_retry: int = 3) -> bool:
        """
        打开与联系人的聊天窗口

        参数:
            contact_name: 联系人名称
            max_retry: 最大重试次数
        返回:
            是否成功打开
        """
        if not self._ensure_connected():
            return False

        for attempt in range(max_retry):
            try:
                # 先搜索联系人
                if not self.search_contact(contact_name):
                    continue

                time.sleep(1.0)

                # 点击第一个搜索结果
                result = self._locator.locate_by_name("search_result_first", retry=2)
                if result.found:
                    self._click_at(result.x, result.y)
                else:
                    # 备选：按回车选择第一个结果
                    pyautogui.press("enter")

                time.sleep(0.5)

                # 按 Escape 关闭搜索面板
                pyautogui.press("escape")
                time.sleep(0.3)

                logger.info(f"已打开聊天: {contact_name}")
                return True

            except Exception as e:
                logger.error(f"打开聊天失败 (第{attempt + 1}次): {e}")
                if attempt < max_retry - 1:
                    time.sleep(1)
                    pyautogui.press("escape")

        return False

    def send_text_message(self, text: str, max_retry: int = 3) -> bool:
        """
        在当前聊天窗口发送文本消息

        参数:
            text: 消息内容
            max_retry: 最大重试次数
        返回:
            是否发送成功
        """
        if not self._ensure_connected():
            return False

        for attempt in range(max_retry):
            try:
                self._ensure_foreground()
                smart_delay()

                # 点击输入框
                result = self._locator.locate_by_name("chat_input", retry=1)
                if result.found:
                    self._click_at(result.center[0], result.center[1])
                else:
                    # 备选方案：点击窗口下方区域（输入框通常在底部）
                    if self._main_window:
                        rect = self._main_window.rectangle()
                        input_x = rect.left + rect.width() // 2
                        input_y = rect.bottom - 100
                        self._click_at(input_x, input_y)

                time.sleep(0.3)

                # 清除已有内容
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.1)

                # 输入文本
                self._type_text(text)
                smart_delay()

                # 发送：按Enter或点击发送按钮
                result = self._locator.locate_by_name("send_button", retry=1)
                if result.found:
                    self._click_at(result.center[0], result.center[1])
                else:
                    pyautogui.press("enter")

                time.sleep(0.3)
                logger.info(f"消息已发送: {text[:50]}{'...' if len(text) > 50 else ''}")
                return True

            except Exception as e:
                logger.error(f"发送消息失败 (第{attempt + 1}次): {e}")
                if attempt < max_retry - 1:
                    time.sleep(1)

        return False

    def send_image(self, image_path: str, max_retry: int = 3) -> bool:
        """
        在当前聊天窗口发送图片

        参数:
            image_path: 图片文件路径
            max_retry: 最大重试次数
        返回:
            是否发送成功
        """
        if not os.path.exists(image_path):
            logger.error(f"图片文件不存在: {image_path}")
            return False

        if not self._ensure_connected():
            return False

        for attempt in range(max_retry):
            try:
                self._ensure_foreground()
                smart_delay()

                # 方法1: 通过剪贴板发送图片
                if IS_WINDOWS:
                    from PIL import Image
                    import win32clipboard
                    import io

                    # 将图片复制到剪贴板
                    img = Image.open(image_path)
                    output = io.BytesIO()
                    img.convert("RGB").save(output, "BMP")
                    bmp_data = output.getvalue()[14:]  # 去掉BMP文件头
                    output.close()

                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(win32con.CF_DIB, bmp_data)
                    win32clipboard.CloseClipboard()
                else:
                    # 非Windows平台使用pyperclip或其他方式
                    import subprocess
                    subprocess.run(["osascript", "-e",
                                    f'set the clipboard to (read (POSIX file "{image_path}") as TIFF picture)'],
                                   timeout=5)

                # 点击输入框
                result = self._locator.locate_by_name("chat_input", retry=1)
                if result.found:
                    self._click_at(result.center[0], result.center[1])
                time.sleep(0.3)

                # 粘贴图片
                pyautogui.hotkey("ctrl", "v")
                time.sleep(1.0)

                # 按Enter发送
                pyautogui.press("enter")
                time.sleep(0.5)

                logger.info(f"图片已发送: {os.path.basename(image_path)}")
                return True

            except Exception as e:
                logger.error(f"发送图片失败 (第{attempt + 1}次): {e}")
                if attempt < max_retry - 1:
                    time.sleep(1)

        return False

    def send_file(self, file_path: str, max_retry: int = 3) -> bool:
        """
        在当前聊天窗口发送文件

        参数:
            file_path: 文件路径
            max_retry: 最大重试次数
        返回:
            是否发送成功
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return False

        if not self._ensure_connected():
            return False

        for attempt in range(max_retry):
            try:
                self._ensure_foreground()
                smart_delay()

                # 将文件路径复制到剪贴板并拖拽到聊天窗口
                # 使用微信的文件发送对话框
                if IS_WINDOWS:
                    import win32clipboard
                    import struct

                    # 使用CF_HDROP格式把文件放到剪贴板
                    file_path_abs = os.path.abspath(file_path)
                    # 构造 DROPFILES 结构
                    offset = 20
                    file_path_encoded = file_path_abs.encode("utf-16-le") + b"\x00\x00"
                    data = struct.pack("IIIIi", offset, 0, 0, 0, 1) + file_path_encoded + b"\x00\x00"

                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(win32clipboard.CF_HDROP, data)
                    win32clipboard.CloseClipboard()

                # 点击输入框
                result = self._locator.locate_by_name("chat_input", retry=1)
                if result.found:
                    self._click_at(result.center[0], result.center[1])
                time.sleep(0.3)

                # 粘贴文件
                pyautogui.hotkey("ctrl", "v")
                time.sleep(1.5)

                # 确认发送
                pyautogui.press("enter")
                time.sleep(0.5)

                logger.info(f"文件已发送: {os.path.basename(file_path)}")
                return True

            except Exception as e:
                logger.error(f"发送文件失败 (第{attempt + 1}次): {e}")
                if attempt < max_retry - 1:
                    time.sleep(1)

        return False

    def click_element(self, element_config: ElementConfig) -> bool:
        """
        点击UI元素

        参数:
            element_config: 元素配置
        返回:
            是否点击成功
        """
        result = self._locator.locate(element_config)
        if not result.found:
            logger.warning(f"未找到元素: {element_config.name}")
            return False

        if result.element is not None and PYWINAUTO_AVAILABLE:
            try:
                result.element.click_input()
                logger.debug(f"通过UIA点击元素: {element_config.name}")
                return True
            except Exception:
                pass

        # 使用坐标点击
        center = result.center
        self._click_at(center[0], center[1])
        logger.debug(f"通过坐标点击元素: {element_config.name} ({center[0]},{center[1]})")
        return True

    def get_window_info(self) -> Dict[str, Any]:
        """
        获取微信窗口信息

        返回:
            窗口信息字典
        """
        info = {
            "hwnd": self._hwnd,
            "pid": self._pid,
            "connected": self._connected,
            "title": "",
            "position": {"x": 0, "y": 0},
            "size": {"width": 0, "height": 0},
            "visible": False,
            "minimized": False,
        }

        if not self._connected or self._main_window is None:
            return info

        try:
            if IS_WINDOWS:
                rect = win32gui.GetWindowRect(self._hwnd)
                info["position"]["x"] = rect[0]
                info["position"]["y"] = rect[1]
                info["size"]["width"] = rect[2] - rect[0]
                info["size"]["height"] = rect[3] - rect[1]
                info["title"] = win32gui.GetWindowText(self._hwnd)
                info["visible"] = win32gui.IsWindowVisible(self._hwnd)
                info["minimized"] = win32gui.IsIconic(self._hwnd)
            else:
                info["title"] = "微信 (模拟)"
        except Exception as e:
            logger.error(f"获取窗口信息失败: {e}")

        return info

    def is_wechat_running(self) -> bool:
        """
        检查微信进程是否在运行

        返回:
            微信是否在运行
        """
        if not IS_WINDOWS:
            return False

        try:
            import psutil
            for proc in psutil.process_iter(["name"]):
                if proc.info["name"] and "WeChat" in proc.info["name"]:
                    return True
            return False
        except ImportError:
            # 没有psutil，通过查找窗口判断
            try:
                hwnds = find_windows(class_name=self.WECHAT_CLASS_NAME)
                return len(hwnds) > 0
            except Exception:
                return False
        except Exception:
            return False

    def get_chat_list(self, count: int = 20) -> List[str]:
        """
        获取最近聊天列表

        参数:
            count: 获取数量
        返回:
            聊天对象名称列表
        """
        if not self._ensure_connected():
            return []

        chat_list = []
        try:
            self._ensure_foreground()

            # 切换到聊天标签
            result = self._locator.locate_by_name("chat_tab", retry=1)
            if result.found:
                self._click_at(result.center[0], result.center[1])
                time.sleep(0.5)

            # 通过UIA获取聊天列表项
            if self._main_window and PYWINAUTO_AVAILABLE:
                try:
                    # 尝试获取列表控件中的子项
                    list_items = self._main_window.descendants(control_type="ListItem")
                    for item in list_items[:count]:
                        try:
                            name = item.window_text()
                            if name and name.strip():
                                chat_list.append(name.strip())
                        except Exception:
                            continue
                except Exception as e:
                    logger.debug(f"通过UIA获取聊天列表失败: {e}")

            logger.info(f"获取到 {len(chat_list)} 个聊天记录")

        except Exception as e:
            logger.error(f"获取聊天列表失败: {e}")

        return chat_list

    def accept_friend_request(self, max_retry: int = 3) -> bool:
        """
        接受好友请求

        返回:
            是否成功处理
        """
        if not self._ensure_connected():
            return False

        for attempt in range(max_retry):
            try:
                self._ensure_foreground()

                # 点击新好友通知
                result = self._locator.locate_by_name("new_message_indicator", retry=1)
                if not result.found:
                    logger.debug("未发现新好友请求通知")
                    return False

                self._click_at(result.center[0], result.center[1])
                time.sleep(1.0)

                # 点击接受按钮
                result = self._locator.locate_by_name("accept_friend_button", retry=2)
                if result.found:
                    self._click_at(result.center[0], result.center[1])
                    time.sleep(0.5)
                    logger.info("已接受好友请求")
                    return True

                # 备选：通过UIA查找"接受"按钮
                if self._main_window and PYWINAUTO_AVAILABLE:
                    try:
                        accept_btn = self._main_window.child_window(title="接受", control_type="Button")
                        if accept_btn.exists(timeout=2):
                            accept_btn.click_input()
                            logger.info("已接受好友请求(UIA)")
                            return True
                    except Exception:
                        pass

                logger.warning("未找到接受好友请求按钮")

            except Exception as e:
                logger.error(f"接受好友请求失败 (第{attempt + 1}次): {e}")
                if attempt < max_retry - 1:
                    time.sleep(1)

        return False

    def _type_text(self, text: str) -> None:
        """
        输入文本（支持中文）

        参数:
            text: 要输入的文本
        """
        if IS_WINDOWS:
            # Windows下使用剪贴板输入中文
            try:
                import win32clipboard
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.3)
            except ImportError:
                # 没有win32clipboard，直接用pyperclip
                import subprocess
                process = subprocess.Popen(
                    ["clip"], stdin=subprocess.PIPE, shell=True
                )
                process.communicate(text.encode("utf-16-le"))
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.3)
        else:
            # macOS / Linux
            import subprocess
            process = subprocess.Popen(
                ["pbcopy"], stdin=subprocess.PIPE
            )
            process.communicate(text.encode("utf-8"))
            pyautogui.hotkey("command", "v")
            time.sleep(0.3)

    def _click_at(self, x: int, y: int, use_bezier: bool = True) -> None:
        """
        在指定坐标点击

        参数:
            x: x坐标
            y: y坐标
            use_bezier: 是否使用贝塞尔曲线移动鼠标
        """
        try:
            current_pos = pyautogui.position()
            if use_bezier:
                path = bezier_mouse_move(
                    (current_pos[0], current_pos[1]),
                    (x, y)
                )
                execute_mouse_move(path)

            # 添加微小偏移模拟人类行为
            import random
            offset_x = random.randint(-2, 2)
            offset_y = random.randint(-2, 2)
            pyautogui.click(x + offset_x, y + offset_y)

        except Exception as e:
            logger.error(f"点击失败: ({x},{y}) - {e}")
            # 直接点击作为后备
            pyautogui.click(x, y)

    def _ensure_connected(self) -> bool:
        """确保已连接到微信"""
        if not self._connected:
            logger.warning("未连接到微信实例")
            return False

        # 验证窗口是否仍然有效
        if IS_WINDOWS and self._hwnd:
            try:
                if not win32gui.IsWindow(self._hwnd):
                    logger.warning("微信窗口已失效，尝试重新连接")
                    self._connected = False
                    return self.connect(self._pid if self._pid else None)
            except Exception:
                pass

        return True

    def take_screenshot(self) -> Optional[str]:
        """
        截取微信窗口截图并保存

        返回:
            截图文件路径
        """
        img = self._screenshot_mgr.capture_window(self._hwnd)
        if img is not None:
            return self._screenshot_mgr.save_screenshot(img)
        return None
