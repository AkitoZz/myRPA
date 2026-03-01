"""
日志管理模块

基于loguru提供统一的日志管理，支持控制台和文件输出、日志轮转。
"""

import os
import sys
from pathlib import Path
from typing import Optional

from loguru import logger


_initialized = False


def setup_logger(
    log_dir: Optional[str] = None,
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    rotation: str = "10 MB",
    retention: str = "7 days",
    log_format: Optional[str] = None,
) -> None:
    """
    配置全局日志系统

    参数:
        log_dir: 日志文件目录，默认为用户数据目录下的logs
        console_level: 控制台日志级别
        file_level: 文件日志级别
        rotation: 日志文件轮转大小
        retention: 日志保留时间
        log_format: 日志格式字符串
    """
    global _initialized
    if _initialized:
        return

    # 移除默认handler
    logger.remove()

    if log_format is None:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level:<8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    # 控制台输出
    logger.add(
        sys.stderr,
        format=log_format,
        level=console_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # 文件输出
    if log_dir is None:
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path.home() / ".config"
        log_dir = str(base / "MyRPA" / "logs")

    os.makedirs(log_dir, exist_ok=True)

    # 通用日志文件
    logger.add(
        os.path.join(log_dir, "rpa_{time:YYYY-MM-DD}.log"),
        format=file_format,
        level=file_level,
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
        enqueue=True,
    )

    # 错误日志单独输出
    logger.add(
        os.path.join(log_dir, "error_{time:YYYY-MM-DD}.log"),
        format=file_format,
        level="ERROR",
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
        enqueue=True,
    )

    # 任务日志
    logger.add(
        os.path.join(log_dir, "task_{time:YYYY-MM-DD}.log"),
        format=file_format,
        level="INFO",
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
        enqueue=True,
        filter=lambda record: "task" in record["extra"],
    )

    _initialized = True
    logger.info("日志系统初始化完成")
    logger.info(f"日志目录: {log_dir}")


def get_logger(name: str = "rpa"):
    """
    获取带名称的日志记录器

    参数:
        name: 日志记录器名称
    返回:
        绑定了名称的logger实例
    """
    return logger.bind(module=name)


def get_task_logger(task_id: str):
    """
    获取任务专用日志记录器

    参数:
        task_id: 任务ID
    返回:
        绑定了任务ID的logger实例
    """
    return logger.bind(task=task_id)
