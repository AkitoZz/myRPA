"""
任务调度器模块

管理RPA任务的创建、调度、执行和状态追踪。
"""

import uuid
import time
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import PriorityQueue
from typing import Optional, Dict, List, Callable, Any

from loguru import logger

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler不可用，定时任务功能将受限")


class TaskState(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


class ScheduleType(Enum):
    """调度类型"""
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    RECURRING = "recurring"


@dataclass(order=True)
class TaskItem:
    """任务队列项（支持优先级排序）"""
    priority: int
    task_id: str = field(compare=False)
    created_at: float = field(compare=False, default_factory=time.time)


@dataclass
class TaskInfo:
    """任务详细信息"""
    task_id: str
    name: str
    task_type: str
    state: TaskState = TaskState.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    schedule_type: ScheduleType = ScheduleType.IMMEDIATE
    schedule_time: Optional[datetime] = None
    cron_expression: Optional[str] = None
    progress: float = 0.0
    total_steps: int = 0
    current_step: int = 0
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    params: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable] = None

    def update_progress(self, current: int, total: int) -> None:
        """更新进度"""
        self.current_step = current
        self.total_steps = total
        self.progress = (current / total * 100) if total > 0 else 0.0


class TaskScheduler:
    """任务调度器"""

    def __init__(self, max_workers: int = 3):
        """
        初始化任务调度器

        参数:
            max_workers: 最大并行工作线程数
        """
        self._task_queue: PriorityQueue = PriorityQueue()
        self._tasks: Dict[str, TaskInfo] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="rpa-task")
        self._futures: Dict[str, Future] = {}
        self._task_handlers: Dict[str, Callable] = {}
        self._running = False
        self._lock = threading.Lock()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._status_callback: Optional[Callable] = None

        # APScheduler 用于定时和周期性任务
        self._ap_scheduler: Optional[Any] = None
        if APSCHEDULER_AVAILABLE:
            self._ap_scheduler = BackgroundScheduler()

        logger.info(f"任务调度器已初始化，最大工作线程: {max_workers}")

    def register_handler(self, task_type: str, handler: Callable) -> None:
        """
        注册任务处理函数

        参数:
            task_type: 任务类型
            handler: 处理函数 (task_info) -> result
        """
        self._task_handlers[task_type] = handler
        logger.debug(f"已注册任务处理器: {task_type}")

    def set_status_callback(self, callback: Callable) -> None:
        """设置状态变更回调"""
        self._status_callback = callback

    def start(self) -> None:
        """启动调度器"""
        if self._running:
            return

        self._running = True

        # 启动调度线程
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="task-scheduler",
            daemon=True,
        )
        self._scheduler_thread.start()

        # 启动APScheduler
        if self._ap_scheduler:
            self._ap_scheduler.start()

        logger.info("任务调度器已启动")

    def stop(self) -> None:
        """停止调度器"""
        self._running = False

        if self._ap_scheduler:
            self._ap_scheduler.shutdown(wait=False)

        self._executor.shutdown(wait=False)
        logger.info("任务调度器已停止")

    def add_task(
        self,
        name: str,
        task_type: str,
        params: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        schedule_type: ScheduleType = ScheduleType.IMMEDIATE,
        schedule_time: Optional[datetime] = None,
        cron_expression: Optional[str] = None,
        callback: Optional[Callable] = None,
    ) -> str:
        """
        添加任务

        参数:
            name: 任务名称
            task_type: 任务类型
            params: 任务参数
            priority: 优先级
            schedule_type: 调度类型
            schedule_time: 定时执行时间
            cron_expression: Cron表达式（周期性任务）
            callback: 完成回调
        返回:
            任务ID
        """
        task_id = str(uuid.uuid4())[:8]

        task_info = TaskInfo(
            task_id=task_id,
            name=name,
            task_type=task_type,
            priority=priority,
            schedule_type=schedule_type,
            schedule_time=schedule_time,
            cron_expression=cron_expression,
            params=params or {},
            callback=callback,
        )

        with self._lock:
            self._tasks[task_id] = task_info

        if schedule_type == ScheduleType.IMMEDIATE:
            # 立即执行 - 加入优先级队列
            task_item = TaskItem(priority=priority.value, task_id=task_id)
            self._task_queue.put(task_item)

        elif schedule_type == ScheduleType.SCHEDULED and schedule_time:
            # 定时执行
            if self._ap_scheduler:
                self._ap_scheduler.add_job(
                    self._enqueue_task,
                    trigger=DateTrigger(run_date=schedule_time),
                    args=[task_id],
                    id=f"scheduled_{task_id}",
                )
            else:
                # 没有APScheduler，使用延迟线程
                delay = (schedule_time - datetime.now()).total_seconds()
                if delay > 0:
                    timer = threading.Timer(delay, self._enqueue_task, args=[task_id])
                    timer.daemon = True
                    timer.start()
                else:
                    self._enqueue_task(task_id)

        elif schedule_type == ScheduleType.RECURRING and cron_expression:
            # 周期性执行
            if self._ap_scheduler:
                self._ap_scheduler.add_job(
                    self._enqueue_task,
                    trigger=CronTrigger.from_crontab(cron_expression),
                    args=[task_id],
                    id=f"recurring_{task_id}",
                )
            else:
                logger.warning("APScheduler不可用，无法创建周期性任务")

        logger.info(f"任务已添加: [{task_id}] {name} ({task_type}), 调度: {schedule_type.value}")
        self._notify_status(task_id)
        return task_id

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        参数:
            task_id: 任务ID
        返回:
            是否取消成功
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                logger.warning(f"任务不存在: {task_id}")
                return False

            if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
                logger.warning(f"任务已结束，无法取消: {task_id}")
                return False

            # 取消正在运行的任务
            if task_id in self._futures:
                self._futures[task_id].cancel()

            task.state = TaskState.CANCELLED
            task.completed_at = datetime.now()

        # 取消APScheduler中的任务
        if self._ap_scheduler:
            for prefix in ["scheduled_", "recurring_"]:
                try:
                    self._ap_scheduler.remove_job(f"{prefix}{task_id}")
                except Exception:
                    pass

        logger.info(f"任务已取消: {task_id}")
        self._notify_status(task_id)
        return True

    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.state == TaskState.RUNNING:
                task.state = TaskState.PAUSED
                logger.info(f"任务已暂停: {task_id}")
                self._notify_status(task_id)
                return True
        return False

    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.state == TaskState.PAUSED:
                task.state = TaskState.RUNNING
                logger.info(f"任务已恢复: {task_id}")
                self._notify_status(task_id)
                return True
        return False

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[TaskInfo]:
        """获取所有任务"""
        return list(self._tasks.values())

    def get_tasks_by_state(self, state: TaskState) -> List[TaskInfo]:
        """按状态获取任务"""
        return [t for t in self._tasks.values() if t.state == state]

    def get_running_count(self) -> int:
        """获取正在运行的任务数"""
        return len([t for t in self._tasks.values() if t.state == TaskState.RUNNING])

    def clear_completed(self) -> int:
        """清除已完成的任务记录，返回清除数量"""
        with self._lock:
            to_remove = [
                tid for tid, t in self._tasks.items()
                if t.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)
            ]
            for tid in to_remove:
                del self._tasks[tid]
                self._futures.pop(tid, None)
            return len(to_remove)

    def _enqueue_task(self, task_id: str) -> None:
        """将任务加入执行队列"""
        task = self._tasks.get(task_id)
        if task and task.state == TaskState.PENDING:
            task_item = TaskItem(priority=task.priority.value, task_id=task_id)
            self._task_queue.put(task_item)

    def _scheduler_loop(self) -> None:
        """调度主循环"""
        while self._running:
            try:
                if self._task_queue.empty():
                    time.sleep(0.5)
                    continue

                task_item = self._task_queue.get(timeout=1)
                task_id = task_item.task_id
                task = self._tasks.get(task_id)

                if task is None or task.state == TaskState.CANCELLED:
                    continue

                # 提交到线程池执行
                future = self._executor.submit(self._execute_task, task_id)
                self._futures[task_id] = future

            except Exception as e:
                if self._running:
                    logger.error(f"调度器异常: {e}")
                    time.sleep(1)

    def _execute_task(self, task_id: str) -> None:
        """执行任务"""
        task = self._tasks.get(task_id)
        if task is None:
            return

        handler = self._task_handlers.get(task.task_type)
        if handler is None:
            logger.error(f"未找到任务处理器: {task.task_type}")
            task.state = TaskState.FAILED
            task.error = f"未注册的任务类型: {task.task_type}"
            self._notify_status(task_id)
            return

        try:
            task.state = TaskState.RUNNING
            task.started_at = datetime.now()
            self._notify_status(task_id)
            logger.info(f"开始执行任务: [{task_id}] {task.name}")

            # 执行任务处理函数
            result = handler(task)

            if task.state == TaskState.CANCELLED:
                return

            task.state = TaskState.COMPLETED
            task.result = result
            task.completed_at = datetime.now()
            task.progress = 100.0
            logger.info(f"任务完成: [{task_id}] {task.name}")

        except Exception as e:
            task.state = TaskState.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            logger.error(f"任务失败: [{task_id}] {task.name} - {e}")

        finally:
            self._notify_status(task_id)

            # 执行回调
            if task.callback:
                try:
                    task.callback(task)
                except Exception as e:
                    logger.error(f"任务回调异常: {e}")

    def _notify_status(self, task_id: str) -> None:
        """通知任务状态变更"""
        if self._status_callback:
            task = self._tasks.get(task_id)
            if task:
                try:
                    self._status_callback(task)
                except Exception as e:
                    logger.error(f"状态通知回调异常: {e}")
