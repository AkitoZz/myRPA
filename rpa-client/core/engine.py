"""
RPA引擎核心模块

单例模式的主控制器，整合所有子系统，提供统一的启动/停止/状态管理接口。
"""

import sys
import threading
import time
from typing import Optional, Dict, Any, Callable, List

from loguru import logger

from config.settings import Settings, get_settings
from config.anti_risk import AntiRiskConfig
from config.wechat_version import WeChatVersionManager
from core.task_scheduler import TaskScheduler, TaskState, TaskPriority, ScheduleType, TaskInfo
from core.wechat_controller import WeChatController
from core.multi_instance import MultiInstanceManager
from core.element_locator import ElementLocator
from utils.delay import set_anti_risk_config


class RPAEngine:
    """
    RPA引擎主控制器

    单例模式，负责协调所有子系统的初始化、运行和关闭。
    """

    _instance: Optional["RPAEngine"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "RPAEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._settings: Settings = get_settings()
        self._anti_risk = AntiRiskConfig()
        self._version_mgr = WeChatVersionManager()
        self._task_scheduler = TaskScheduler(max_workers=3)
        self._multi_instance = MultiInstanceManager(
            wechat_path=self._settings.wechat.install_path,
            max_instances=self._settings.wechat.max_instances,
        )
        self._controllers: Dict[int, WeChatController] = {}
        self._active_controller: Optional[WeChatController] = None

        self._running = False
        self._status = "stopped"
        self._error_count = 0
        self._max_errors = 10
        self._status_callbacks: List[Callable] = []

        # 注册任务处理器
        self._register_task_handlers()

        self._initialized = True
        logger.info("RPA引擎已创建")

    def _register_task_handlers(self) -> None:
        """注册所有任务类型的处理器"""
        self._task_scheduler.register_handler("add_friend", self._handle_add_friend)
        self._task_scheduler.register_handler("mass_message", self._handle_mass_message)
        self._task_scheduler.register_handler("auto_reply", self._handle_auto_reply)
        self._task_scheduler.register_handler("group_invite", self._handle_group_invite)

    def initialize(self) -> bool:
        """
        初始化所有子系统

        返回:
            是否初始化成功
        """
        logger.info("正在初始化RPA引擎...")

        # 加载反风控配置
        set_anti_risk_config(self._anti_risk)

        # 检测微信版本
        if sys.platform == "win32":
            self._version_mgr.detect_install_path()
            self._version_mgr.detect_version()
            compatible, msg = self._version_mgr.check_compatibility()
            logger.info(f"微信版本检查: {msg}")

            if self._version_mgr.install_path:
                self._multi_instance.set_wechat_path(self._version_mgr.install_path)

        # 启动任务调度器
        self._task_scheduler.start()
        self._task_scheduler.set_status_callback(self._on_task_status_change)

        self._status = "initialized"
        self._running = True
        logger.info("RPA引擎初始化完成")
        return True

    def shutdown(self) -> None:
        """关闭所有子系统"""
        logger.info("正在关闭RPA引擎...")
        self._running = False

        # 停止任务调度器
        self._task_scheduler.stop()

        # 断开所有微信控制器
        for pid, controller in self._controllers.items():
            try:
                controller.disconnect()
            except Exception as e:
                logger.error(f"断开控制器失败 PID={pid}: {e}")

        self._controllers.clear()
        self._active_controller = None
        self._status = "stopped"

        logger.info("RPA引擎已关闭")

    def connect_wechat(self, pid: Optional[int] = None) -> bool:
        """
        连接微信实例

        参数:
            pid: 微信进程ID，为空则自动查找
        返回:
            是否连接成功
        """
        controller = WeChatController()

        # 加载元素配置
        config_path = self._version_mgr.get_element_config_path()
        if config_path:
            controller.load_element_configs(config_path)

        if controller.connect(pid):
            actual_pid = controller.pid
            self._controllers[actual_pid] = controller
            self._active_controller = controller
            logger.info(f"已连接微信实例: PID={actual_pid}")
            return True

        logger.error("连接微信失败")
        return False

    def disconnect_wechat(self, pid: Optional[int] = None) -> None:
        """断开微信连接"""
        if pid is not None:
            controller = self._controllers.pop(pid, None)
            if controller:
                controller.disconnect()
                if self._active_controller is controller:
                    self._active_controller = None
        elif self._active_controller:
            pid = self._active_controller.pid
            self._active_controller.disconnect()
            self._controllers.pop(pid, None)
            self._active_controller = None

    def get_active_controller(self) -> Optional[WeChatController]:
        """获取当前活动的微信控制器"""
        return self._active_controller

    def set_active_controller(self, pid: int) -> bool:
        """设置活动的微信控制器"""
        controller = self._controllers.get(pid)
        if controller:
            self._active_controller = controller
            return True
        return False

    # ---- 任务管理方法 ----

    def add_task(
        self,
        name: str,
        task_type: str,
        params: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        schedule_type: ScheduleType = ScheduleType.IMMEDIATE,
        **kwargs,
    ) -> str:
        """添加任务"""
        return self._task_scheduler.add_task(
            name=name,
            task_type=task_type,
            params=params,
            priority=priority,
            schedule_type=schedule_type,
            **kwargs,
        )

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        return self._task_scheduler.cancel_task(task_id)

    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        return self._task_scheduler.pause_task(task_id)

    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        return self._task_scheduler.resume_task(task_id)

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        return self._task_scheduler.get_task(task_id)

    def get_all_tasks(self) -> List[TaskInfo]:
        """获取所有任务"""
        return self._task_scheduler.get_all_tasks()

    # ---- 微信操作快捷方法 ----

    def launch_wechat(self) -> Optional[int]:
        """启动新微信实例"""
        return self._multi_instance.launch_wechat()

    def get_wechat_instances(self):
        """获取所有微信实例"""
        return self._multi_instance.get_all_instances()

    # ---- 状态与错误处理 ----

    @property
    def status(self) -> str:
        """获取引擎状态"""
        return self._status

    @property
    def is_running(self) -> bool:
        """引擎是否在运行"""
        return self._running

    def get_status_report(self) -> Dict[str, Any]:
        """获取完整状态报告"""
        return {
            "status": self._status,
            "running": self._running,
            "connected_instances": len(self._controllers),
            "active_pid": self._active_controller.pid if self._active_controller else None,
            "running_tasks": self._task_scheduler.get_running_count(),
            "total_tasks": len(self._task_scheduler.get_all_tasks()),
            "error_count": self._error_count,
            "wechat_version": str(self._version_mgr.version) if self._version_mgr.version else "未检测",
        }

    def add_status_callback(self, callback: Callable) -> None:
        """添加状态变更回调"""
        self._status_callbacks.append(callback)

    def _on_task_status_change(self, task: TaskInfo) -> None:
        """任务状态变更处理"""
        if task.state == TaskState.FAILED:
            self._error_count += 1
            if self._error_count >= self._max_errors:
                logger.warning(f"错误次数过多 ({self._error_count})，考虑暂停操作")

        for cb in self._status_callbacks:
            try:
                cb(task)
            except Exception as e:
                logger.error(f"状态回调异常: {e}")

    def _recover_from_error(self) -> bool:
        """尝试从错误中恢复"""
        logger.info("尝试从错误中恢复...")

        # 重新连接微信
        if self._active_controller and not self._active_controller.is_connected:
            pid = self._active_controller.pid
            if pid:
                return self.connect_wechat(pid)

        return False

    # ---- 任务处理器 ----

    def _handle_add_friend(self, task: TaskInfo) -> Dict[str, Any]:
        """处理加好友任务"""
        from modules.add_friend import AddFriendModule

        controller = self._active_controller
        if not controller or not controller.is_connected:
            raise RuntimeError("微信未连接")

        module = AddFriendModule(controller)
        params = task.params

        method = params.get("method", "phone")
        results = []

        if method == "phone":
            targets = params.get("targets", [])
            greeting = params.get("greeting", "你好，请求添加好友")
            total = len(targets)
            for i, phone in enumerate(targets):
                task.update_progress(i + 1, total)
                success = module.add_by_phone(phone, greeting)
                results.append({"phone": phone, "success": success})
        elif method == "wxid":
            targets = params.get("targets", [])
            greeting = params.get("greeting", "你好，请求添加好友")
            total = len(targets)
            for i, wxid in enumerate(targets):
                task.update_progress(i + 1, total)
                success = module.add_by_wxid(wxid, greeting)
                results.append({"wxid": wxid, "success": success})

        return {"results": results, "total": len(results)}

    def _handle_mass_message(self, task: TaskInfo) -> Dict[str, Any]:
        """处理群发消息任务"""
        from modules.mass_message import MassMessageModule

        controller = self._active_controller
        if not controller or not controller.is_connected:
            raise RuntimeError("微信未连接")

        module = MassMessageModule(controller)
        params = task.params

        targets = params.get("targets", [])
        message = params.get("message", "")
        msg_type = params.get("message_type", "text")
        target_type = params.get("target_type", "friend")

        def progress_cb(current, total):
            task.update_progress(current, total)

        if target_type == "friend":
            results = module.send_to_friends(targets, message, msg_type, progress_callback=progress_cb)
        else:
            results = module.send_to_groups(targets, message, msg_type, progress_callback=progress_cb)

        return results

    def _handle_auto_reply(self, task: TaskInfo) -> Dict[str, Any]:
        """处理自动回复任务"""
        from modules.auto_reply import AutoReplyModule

        controller = self._active_controller
        if not controller or not controller.is_connected:
            raise RuntimeError("微信未连接")

        module = AutoReplyModule(controller)
        params = task.params

        keywords = params.get("keywords", {})
        mode = params.get("mode", "full_auto")

        module.set_keywords(keywords)
        module.set_mode(mode)
        module.start_monitoring()

        # 持续运行直到任务被取消
        while task.state == TaskState.RUNNING:
            time.sleep(1)

        module.stop_monitoring()
        return {"status": "stopped"}

    def _handle_group_invite(self, task: TaskInfo) -> Dict[str, Any]:
        """处理群邀请任务"""
        from modules.group_manager import GroupManagerModule

        controller = self._active_controller
        if not controller or not controller.is_connected:
            raise RuntimeError("微信未连接")

        module = GroupManagerModule(controller)
        params = task.params

        group_name = params.get("group_name", "")
        contacts = params.get("contacts", [])

        results = module.invite_to_group(group_name, contacts)
        return results

    @classmethod
    def reset(cls) -> None:
        """重置单例（仅用于测试）"""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.shutdown()
                cls._instance = None
