"""
微信多开管理模块

支持启动多个微信实例、管理互斥体、进程监控等功能。
"""

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict

from loguru import logger

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    try:
        import ctypes
        from ctypes import wintypes
        import win32api
        import win32con
        import win32process
        import win32gui
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
        logger.warning("pywin32不可用，多开功能将受限")
else:
    WIN32_AVAILABLE = False


@dataclass
class WeChatInstance:
    """微信实例信息"""
    pid: int
    hwnd: int = 0
    title: str = ""
    account: str = ""
    status: str = "unknown"
    install_path: str = ""
    version: str = ""
    connected: bool = False


class MultiInstanceManager:
    """微信多开管理器"""

    WECHAT_MUTEX_NAME = "_WeChat_App_Instance_Identity_Mutex_Name"
    WECHAT_CLASS_NAME = "WeChatMainWndForPC"
    WECHAT_LOGIN_CLASS = "WeChatLoginWndForPC"
    MAX_INSTANCES = 5

    def __init__(self, wechat_path: str = "", max_instances: int = 5):
        """
        初始化多开管理器

        参数:
            wechat_path: 微信安装路径
            max_instances: 最大实例数
        """
        self._wechat_path = wechat_path
        self.MAX_INSTANCES = max_instances
        self._instances: Dict[int, WeChatInstance] = {}

    def set_wechat_path(self, path: str) -> None:
        """设置微信安装路径"""
        self._wechat_path = path

    def _find_wechat_exe(self) -> Optional[str]:
        """查找微信可执行文件路径"""
        if self._wechat_path:
            exe_path = os.path.join(self._wechat_path, "WeChat.exe")
            if os.path.exists(exe_path):
                return exe_path

        # 常见路径搜索
        common_paths = [
            r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
            r"C:\Program Files\Tencent\WeChat\WeChat.exe",
            r"D:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
            r"D:\Program Files\Tencent\WeChat\WeChat.exe",
            r"D:\Tencent\WeChat\WeChat.exe",
            r"C:\Tencent\WeChat\WeChat.exe",
        ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        # 尝试从注册表获取
        if IS_WINDOWS:
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Tencent\WeChat")
                install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                winreg.CloseKey(key)
                exe_path = os.path.join(install_path, "WeChat.exe")
                if os.path.exists(exe_path):
                    return exe_path
            except Exception:
                pass

        logger.error("未找到微信可执行文件")
        return None

    def kill_mutex(self) -> bool:
        """
        关闭微信互斥体以允许多开

        返回:
            是否成功关闭互斥体
        """
        if not IS_WINDOWS or not WIN32_AVAILABLE:
            logger.warning("仅Windows平台支持关闭互斥体")
            return False

        try:
            # 使用 ctypes 调用 Windows API
            kernel32 = ctypes.windll.kernel32

            # 遍历所有微信进程，关闭其互斥体
            pids = self._get_wechat_pids()
            if not pids:
                logger.info("未发现运行中的微信进程")
                return True

            success = False
            for pid in pids:
                try:
                    # 打开进程
                    process_handle = kernel32.OpenProcess(
                        0x0400 | 0x0010,  # PROCESS_QUERY_INFORMATION | PROCESS_DUP_HANDLE
                        False,
                        pid
                    )
                    if not process_handle:
                        continue

                    # 枚举进程句柄，查找并关闭互斥体
                    # 使用NtQuerySystemInformation获取句柄列表
                    closed = self._close_mutex_for_process(pid, process_handle)
                    kernel32.CloseHandle(process_handle)

                    if closed:
                        success = True
                        logger.info(f"已关闭微信进程 {pid} 的互斥体")

                except Exception as e:
                    logger.debug(f"处理进程 {pid} 互斥体失败: {e}")

            return success

        except Exception as e:
            logger.error(f"关闭互斥体失败: {e}")
            return False

    def _close_mutex_for_process(self, pid: int, process_handle: int) -> bool:
        """关闭指定进程的互斥体"""
        if not WIN32_AVAILABLE:
            return False

        try:
            ntdll = ctypes.windll.ntdll
            kernel32 = ctypes.windll.kernel32

            # 定义 SYSTEM_HANDLE_INFORMATION 结构
            class SYSTEM_HANDLE_TABLE_ENTRY_INFO(ctypes.Structure):
                _fields_ = [
                    ("UniqueProcessId", wintypes.USHORT),
                    ("CreatorBackTraceIndex", wintypes.USHORT),
                    ("ObjectTypeIndex", ctypes.c_ubyte),
                    ("HandleAttributes", ctypes.c_ubyte),
                    ("HandleValue", wintypes.USHORT),
                    ("Object", ctypes.c_void_p),
                    ("GrantedAccess", wintypes.ULONG),
                ]

            # 查询系统句柄信息
            buf_size = 0x10000
            while True:
                buf = ctypes.create_string_buffer(buf_size)
                status = ntdll.NtQuerySystemInformation(16, buf, buf_size, None)
                if status == 0:
                    break
                elif status == 0xC0000004:  # STATUS_INFO_LENGTH_MISMATCH
                    buf_size *= 2
                    if buf_size > 0x4000000:  # 64MB上限
                        return False
                else:
                    return False

            # 解析句柄数量
            handle_count = ctypes.cast(buf, ctypes.POINTER(wintypes.ULONG)).contents.value
            handle_array_offset = ctypes.sizeof(wintypes.ULONG)

            # 遍历句柄
            for i in range(min(handle_count, 100000)):
                offset = handle_array_offset + i * ctypes.sizeof(SYSTEM_HANDLE_TABLE_ENTRY_INFO)
                if offset + ctypes.sizeof(SYSTEM_HANDLE_TABLE_ENTRY_INFO) > buf_size:
                    break

                entry = SYSTEM_HANDLE_TABLE_ENTRY_INFO.from_buffer_copy(buf, offset)

                if entry.UniqueProcessId != pid:
                    continue

                # 尝试复制句柄到当前进程
                try:
                    dup_handle = wintypes.HANDLE()
                    result = kernel32.DuplicateHandle(
                        process_handle,
                        entry.HandleValue,
                        kernel32.GetCurrentProcess(),
                        ctypes.byref(dup_handle),
                        0,
                        False,
                        0x00000002,  # DUPLICATE_SAME_ACCESS
                    )

                    if result and dup_handle.value:
                        # 查询对象名称
                        buf2 = ctypes.create_string_buffer(1024)
                        ret_len = wintypes.ULONG()
                        status = ntdll.NtQueryObject(
                            dup_handle, 1, buf2, 1024, ctypes.byref(ret_len)
                        )

                        if status == 0:
                            # 检查是否是微信互斥体
                            name_data = buf2.raw[:ret_len.value]
                            if self.WECHAT_MUTEX_NAME.encode("utf-16-le") in name_data:
                                # 关闭原始句柄
                                kernel32.DuplicateHandle(
                                    process_handle,
                                    entry.HandleValue,
                                    0,
                                    None,
                                    0,
                                    False,
                                    0x00000001,  # DUPLICATE_CLOSE_SOURCE
                                )
                                kernel32.CloseHandle(dup_handle)
                                return True

                        kernel32.CloseHandle(dup_handle)
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.debug(f"关闭互斥体详细操作失败: {e}")
            return False

    def launch_wechat(self, kill_mutex_first: bool = True) -> Optional[int]:
        """
        启动新的微信实例

        参数:
            kill_mutex_first: 是否先关闭互斥体
        返回:
            新进程PID，失败返回None
        """
        if not IS_WINDOWS:
            logger.warning("仅Windows平台支持启动微信")
            return None

        # 检查实例数量限制
        current_count = len(self.get_all_instances())
        if current_count >= self.MAX_INSTANCES:
            logger.warning(f"已达最大实例数限制: {self.MAX_INSTANCES}")
            return None

        # 先关闭互斥体
        if kill_mutex_first and current_count > 0:
            self.kill_mutex()
            time.sleep(0.5)

        # 查找微信路径
        exe_path = self._find_wechat_exe()
        if exe_path is None:
            return None

        try:
            import subprocess
            process = subprocess.Popen(
                [exe_path],
                cwd=os.path.dirname(exe_path),
            )
            pid = process.pid
            time.sleep(2)  # 等待微信启动

            logger.info(f"已启动微信实例: PID={pid}")

            # 记录实例
            instance = WeChatInstance(
                pid=pid,
                install_path=os.path.dirname(exe_path),
                status="starting",
            )
            self._instances[pid] = instance

            return pid

        except Exception as e:
            logger.error(f"启动微信失败: {e}")
            return None

    def get_all_instances(self) -> List[WeChatInstance]:
        """
        获取所有运行中的微信实例

        返回:
            微信实例列表
        """
        instances = []
        pids = self._get_wechat_pids()

        for pid in pids:
            if pid in self._instances:
                instance = self._instances[pid]
                instance.status = "running"
            else:
                instance = WeChatInstance(pid=pid, status="running")

            # 获取窗口句柄
            hwnd = self._get_hwnd_by_pid(pid)
            if hwnd:
                instance.hwnd = hwnd
                if IS_WINDOWS and WIN32_AVAILABLE:
                    try:
                        instance.title = win32gui.GetWindowText(hwnd)
                    except Exception:
                        pass

            instances.append(instance)
            self._instances[pid] = instance

        # 清理已退出的实例
        active_pids = set(pids)
        dead_pids = [p for p in self._instances if p not in active_pids]
        for p in dead_pids:
            del self._instances[p]

        return instances

    def get_instance_by_pid(self, pid: int) -> Optional[WeChatInstance]:
        """
        获取指定PID的微信实例

        参数:
            pid: 进程ID
        返回:
            微信实例信息
        """
        instances = self.get_all_instances()
        for inst in instances:
            if inst.pid == pid:
                return inst
        return None

    def close_instance(self, pid: int) -> bool:
        """
        关闭指定的微信实例

        参数:
            pid: 进程ID
        返回:
            是否成功关闭
        """
        if not IS_WINDOWS:
            return False

        try:
            import subprocess
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, timeout=10,
            )

            # 从记录中移除
            self._instances.pop(pid, None)
            logger.info(f"已关闭微信实例: PID={pid}")
            return True

        except Exception as e:
            logger.error(f"关闭微信实例失败: PID={pid} - {e}")
            return False

    def close_all_instances(self) -> int:
        """
        关闭所有微信实例

        返回:
            成功关闭的数量
        """
        count = 0
        for pid in list(self._get_wechat_pids()):
            if self.close_instance(pid):
                count += 1
        return count

    def _get_wechat_pids(self) -> List[int]:
        """获取所有微信进程PID"""
        pids = []

        if not IS_WINDOWS:
            return pids

        try:
            import subprocess
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq WeChat.exe", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10,
            )

            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.strip().strip('"').split('","')
                    if len(parts) >= 2:
                        try:
                            pid = int(parts[1].strip('"'))
                            pids.append(pid)
                        except ValueError:
                            continue

        except Exception as e:
            logger.error(f"获取微信进程列表失败: {e}")

        return pids

    def _get_hwnd_by_pid(self, pid: int) -> int:
        """通过PID获取主窗口句柄"""
        if not IS_WINDOWS or not WIN32_AVAILABLE:
            return 0

        result_hwnd = 0

        def enum_callback(hwnd, _):
            nonlocal result_hwnd
            try:
                _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                if window_pid == pid:
                    class_name = win32gui.GetClassName(hwnd)
                    if class_name == self.WECHAT_CLASS_NAME:
                        result_hwnd = hwnd
                        return False
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception:
            pass

        return result_hwnd

    @property
    def instance_count(self) -> int:
        """当前运行的实例数"""
        return len(self._get_wechat_pids())
