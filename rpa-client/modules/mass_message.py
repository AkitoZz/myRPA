"""
群发消息模块

支持向好友列表或群聊列表批量发送文本、图片、文件消息，
包含进度追踪和反风控延迟。
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Callable

from loguru import logger

from core.wechat_controller import WeChatController
from config.anti_risk import AntiRiskConfig
from utils.delay import smart_delay, random_delay, fatigue_check, is_work_hours


@dataclass
class SendResult:
    """发送结果"""
    target: str
    success: bool
    message_type: str = "text"
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class MassMessageModule:
    """群发消息模块"""

    def __init__(self, controller: WeChatController, anti_risk: Optional[AntiRiskConfig] = None):
        """
        初始化群发消息模块

        参数:
            controller: 微信控制器
            anti_risk: 反风控配置
        """
        self._controller = controller
        self._anti_risk = anti_risk or AntiRiskConfig()
        self._daily_count = 0
        self._daily_date = date.today()
        self._results: List[SendResult] = []
        self._paused = False
        self._stopped = False

    def _check_daily_limit(self) -> bool:
        """检查每日限额"""
        today = date.today()
        if self._daily_date != today:
            self._daily_count = 0
            self._daily_date = today

        if self._daily_count >= self._anti_risk.daily_limits.mass_message:
            logger.warning(f"已达每日群发上限: {self._anti_risk.daily_limits.mass_message}")
            return False
        return True

    def send_to_friends(
        self,
        friend_list: List[str],
        message: str,
        message_type: str = "text",
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        向好友列表发送消息

        参数:
            friend_list: 好友名称列表
            message: 消息内容（文本内容或文件路径）
            message_type: 消息类型 (text/image/file)
            progress_callback: 进度回调 (current, total)
        返回:
            发送结果统计
        """
        self._stopped = False
        self._paused = False
        total = len(friend_list)
        success_count = 0
        fail_count = 0
        skip_count = 0

        logger.info(f"开始群发消息: {total} 个好友, 类型={message_type}")

        for i, friend in enumerate(friend_list):
            # 检查停止标志
            if self._stopped:
                logger.info("群发已被停止")
                break

            # 暂停检查
            while self._paused:
                time.sleep(1)
                if self._stopped:
                    break

            # 每日限额检查
            if not self._check_daily_limit():
                skip_count += 1
                continue

            # 工作时间检查
            if not is_work_hours():
                logger.info("已到非工作时间，暂停群发")
                skip_count += total - i
                break

            try:
                # 打开聊天
                if not self._controller.open_chat(friend):
                    logger.warning(f"无法打开聊天: {friend}")
                    self._record_result(friend, False, message_type, "无法打开聊天")
                    fail_count += 1
                    continue

                smart_delay()

                # 发送消息
                sent = self._send_message(message, message_type)

                if sent:
                    success_count += 1
                    self._daily_count += 1
                    self._record_result(friend, True, message_type)
                    logger.info(f"[{i + 1}/{total}] 发送成功: {friend}")
                else:
                    fail_count += 1
                    self._record_result(friend, False, message_type, "发送失败")
                    logger.warning(f"[{i + 1}/{total}] 发送失败: {friend}")

                # 疲劳检查
                fatigue_check()

                # 进度回调
                if progress_callback:
                    progress_callback(i + 1, total)

                # 操作间延迟
                smart_delay()

            except Exception as e:
                logger.error(f"发送消息异常 ({friend}): {e}")
                self._record_result(friend, False, message_type, str(e))
                fail_count += 1
                # 出错后稍长延迟
                random_delay(2.0, 5.0)

        result = {
            "total": total,
            "success": success_count,
            "failed": fail_count,
            "skipped": skip_count,
            "results": [
                {"target": r.target, "success": r.success, "error": r.error}
                for r in self._results[-total:]
            ],
        }

        logger.info(f"群发完成: 成功={success_count}, 失败={fail_count}, 跳过={skip_count}")
        return result

    def send_to_groups(
        self,
        group_list: List[str],
        message: str,
        message_type: str = "text",
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        向群聊列表发送消息

        参数:
            group_list: 群聊名称列表
            message: 消息内容
            message_type: 消息类型
            progress_callback: 进度回调
        返回:
            发送结果统计
        """
        self._stopped = False
        self._paused = False
        total = len(group_list)
        success_count = 0
        fail_count = 0
        skip_count = 0

        logger.info(f"开始群发消息到群聊: {total} 个群, 类型={message_type}")

        for i, group in enumerate(group_list):
            if self._stopped:
                logger.info("群发已被停止")
                break

            while self._paused:
                time.sleep(1)
                if self._stopped:
                    break

            if not self._check_daily_limit():
                skip_count += 1
                continue

            if not is_work_hours():
                logger.info("已到非工作时间，暂停群发")
                skip_count += total - i
                break

            try:
                if not self._controller.open_chat(group):
                    logger.warning(f"无法打开群聊: {group}")
                    self._record_result(group, False, message_type, "无法打开群聊")
                    fail_count += 1
                    continue

                smart_delay()

                sent = self._send_message(message, message_type)

                if sent:
                    success_count += 1
                    self._daily_count += 1
                    self._record_result(group, True, message_type)
                    logger.info(f"[{i + 1}/{total}] 群消息发送成功: {group}")
                else:
                    fail_count += 1
                    self._record_result(group, False, message_type, "发送失败")
                    logger.warning(f"[{i + 1}/{total}] 群消息发送失败: {group}")

                fatigue_check()

                if progress_callback:
                    progress_callback(i + 1, total)

                smart_delay()

            except Exception as e:
                logger.error(f"群发消息异常 ({group}): {e}")
                self._record_result(group, False, message_type, str(e))
                fail_count += 1
                random_delay(2.0, 5.0)

        result = {
            "total": total,
            "success": success_count,
            "failed": fail_count,
            "skipped": skip_count,
            "results": [
                {"target": r.target, "success": r.success, "error": r.error}
                for r in self._results[-total:]
            ],
        }

        logger.info(f"群聊群发完成: 成功={success_count}, 失败={fail_count}, 跳过={skip_count}")
        return result

    def _send_message(self, message: str, message_type: str) -> bool:
        """
        发送单条消息

        参数:
            message: 消息内容或文件路径
            message_type: 消息类型
        返回:
            是否发送成功
        """
        if message_type == "text":
            return self._controller.send_text_message(message)
        elif message_type == "image":
            return self._controller.send_image(message)
        elif message_type == "file":
            return self._controller.send_file(message)
        else:
            logger.error(f"不支持的消息类型: {message_type}")
            return False

    def pause(self) -> None:
        """暂停群发"""
        self._paused = True
        logger.info("群发已暂停")

    def resume(self) -> None:
        """恢复群发"""
        self._paused = False
        logger.info("群发已恢复")

    def stop(self) -> None:
        """停止群发"""
        self._stopped = True
        self._paused = False
        logger.info("群发已停止")

    def _record_result(self, target: str, success: bool, message_type: str, error: str = "") -> None:
        """记录发送结果"""
        result = SendResult(
            target=target,
            success=success,
            message_type=message_type,
            error=error,
        )
        self._results.append(result)

    def get_results(self) -> List[SendResult]:
        """获取所有发送结果"""
        return self._results.copy()

    def get_daily_count(self) -> int:
        """获取今日已发送数量"""
        today = date.today()
        if self._daily_date != today:
            self._daily_count = 0
            self._daily_date = today
        return self._daily_count

    def clear_results(self) -> None:
        """清除发送记录"""
        self._results.clear()
