"""
自动回复/托管模块

监控微信新消息，根据关键词规则自动回复，
支持半自动（通知用户）和全自动模式。
"""

import re
import time
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Callable, Any

from loguru import logger

from core.wechat_controller import WeChatController
from config.anti_risk import AntiRiskConfig
from utils.delay import smart_delay, random_delay


class ReplyMode(Enum):
    """回复模式"""
    SEMI_AUTO = "semi_auto"
    FULL_AUTO = "full_auto"


@dataclass
class MessageInfo:
    """消息信息"""
    contact: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    is_group: bool = False
    processed: bool = False
    replied: bool = False
    reply_content: str = ""


@dataclass
class KeywordRule:
    """关键词回复规则"""
    keyword: str
    reply: str
    is_regex: bool = False
    match_mode: str = "contains"  # contains, exact, startswith, regex
    enabled: bool = True
    priority: int = 0


class AutoReplyModule:
    """自动回复模块"""

    def __init__(self, controller: WeChatController, anti_risk: Optional[AntiRiskConfig] = None):
        """
        初始化自动回复模块

        参数:
            controller: 微信控制器
            anti_risk: 反风控配置
        """
        self._controller = controller
        self._anti_risk = anti_risk or AntiRiskConfig()
        self._mode = ReplyMode.FULL_AUTO
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._keyword_rules: List[KeywordRule] = []
        self._message_queue: deque = deque(maxlen=1000)
        self._processed_messages: List[MessageInfo] = []
        self._default_reply: str = ""
        self._check_interval: float = 3.0
        self._on_new_message: Optional[Callable] = None
        self._on_reply_sent: Optional[Callable] = None
        self._daily_reply_count = 0
        self._lock = threading.Lock()

    def set_mode(self, mode: str) -> None:
        """
        设置回复模式

        参数:
            mode: 'semi_auto' 或 'full_auto'
        """
        if mode == "semi_auto":
            self._mode = ReplyMode.SEMI_AUTO
        else:
            self._mode = ReplyMode.FULL_AUTO
        logger.info(f"自动回复模式已设置为: {self._mode.value}")

    def set_keywords(self, keyword_reply_map: Dict[str, str]) -> None:
        """
        设置关键词回复映射

        参数:
            keyword_reply_map: {关键词: 回复内容} 字典
        """
        self._keyword_rules.clear()
        for keyword, reply in keyword_reply_map.items():
            rule = KeywordRule(keyword=keyword, reply=reply)
            self._keyword_rules.append(rule)
        logger.info(f"已设置 {len(self._keyword_rules)} 条关键词规则")

    def add_keyword_rule(self, keyword: str, reply: str, match_mode: str = "contains",
                         is_regex: bool = False, priority: int = 0) -> None:
        """
        添加关键词回复规则

        参数:
            keyword: 关键词
            reply: 回复内容
            match_mode: 匹配模式
            is_regex: 是否使用正则表达式
            priority: 优先级（数字越大优先级越高）
        """
        rule = KeywordRule(
            keyword=keyword,
            reply=reply,
            is_regex=is_regex,
            match_mode=match_mode,
            priority=priority,
        )
        self._keyword_rules.append(rule)
        # 按优先级排序
        self._keyword_rules.sort(key=lambda r: r.priority, reverse=True)
        logger.debug(f"已添加关键词规则: '{keyword}' -> '{reply[:30]}...'")

    def remove_keyword_rule(self, keyword: str) -> bool:
        """移除关键词规则"""
        original_len = len(self._keyword_rules)
        self._keyword_rules = [r for r in self._keyword_rules if r.keyword != keyword]
        removed = original_len - len(self._keyword_rules)
        if removed > 0:
            logger.debug(f"已移除关键词规则: '{keyword}'")
            return True
        return False

    def set_default_reply(self, reply: str) -> None:
        """设置默认回复（无匹配关键词时使用）"""
        self._default_reply = reply

    def set_check_interval(self, interval: float) -> None:
        """设置检查间隔（秒）"""
        self._check_interval = max(1.0, interval)

    def set_message_callback(self, callback: Callable) -> None:
        """设置新消息回调"""
        self._on_new_message = callback

    def set_reply_callback(self, callback: Callable) -> None:
        """设置回复发送回调"""
        self._on_reply_sent = callback

    def start_monitoring(self) -> bool:
        """
        开始监控新消息

        返回:
            是否成功启动
        """
        if self._monitoring:
            logger.warning("消息监控已在运行中")
            return False

        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="auto-reply-monitor",
            daemon=True,
        )
        self._monitor_thread.start()
        logger.info("自动回复监控已启动")
        return True

    def stop_monitoring(self) -> None:
        """停止监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)
            self._monitor_thread = None
        logger.info("自动回复监控已停止")

    @property
    def is_monitoring(self) -> bool:
        """是否正在监控"""
        return self._monitoring

    def check_new_messages(self) -> List[str]:
        """
        检查新消息指示器

        返回:
            有新消息的联系人列表
        """
        contacts_with_new = []

        try:
            # 通过UIA查找有未读消息的聊天项
            if self._controller._main_window:
                try:
                    from core.wechat_controller import PYWINAUTO_AVAILABLE
                    if PYWINAUTO_AVAILABLE:
                        list_items = self._controller._main_window.descendants(
                            control_type="ListItem"
                        )
                        for item in list_items:
                            try:
                                name = item.window_text()
                                # 检查是否有未读消息标记
                                # 微信中未读消息通常有红色数字角标
                                children = item.children()
                                for child in children:
                                    child_text = child.window_text()
                                    if child_text and child_text.isdigit() and int(child_text) > 0:
                                        if name and name.strip():
                                            contacts_with_new.append(name.strip())
                                        break
                            except Exception:
                                continue
                except ImportError:
                    pass

            # 备选：检查新消息指示器元素
            if not contacts_with_new:
                result = self._controller._locator.locate_by_name("new_message_indicator", retry=1)
                if result.found:
                    contacts_with_new.append("_unknown_")

        except Exception as e:
            logger.debug(f"检查新消息失败: {e}")

        return contacts_with_new

    def process_message(self, contact: str, message: str) -> Optional[str]:
        """
        处理消息，匹配关键词并生成回复

        参数:
            contact: 联系人名称
            message: 消息内容
        返回:
            匹配到的回复内容，无匹配返回None
        """
        msg_info = MessageInfo(contact=contact, content=message)

        # 按优先级匹配关键词
        for rule in self._keyword_rules:
            if not rule.enabled:
                continue

            matched = False

            if rule.is_regex or rule.match_mode == "regex":
                try:
                    if re.search(rule.keyword, message, re.IGNORECASE):
                        matched = True
                except re.error:
                    logger.warning(f"无效的正则表达式: {rule.keyword}")
            elif rule.match_mode == "exact":
                matched = message.strip() == rule.keyword
            elif rule.match_mode == "startswith":
                matched = message.strip().startswith(rule.keyword)
            else:  # contains
                matched = rule.keyword in message

            if matched:
                msg_info.processed = True
                reply = rule.reply

                # 支持变量替换
                reply = reply.replace("{contact}", contact)
                reply = reply.replace("{message}", message)
                reply = reply.replace("{time}", datetime.now().strftime("%H:%M"))

                logger.info(f"关键词匹配: '{rule.keyword}' -> 回复: '{reply[:50]}...'")
                return reply

        # 使用默认回复
        if self._default_reply:
            return self._default_reply

        return None

    def _monitor_loop(self) -> None:
        """消息监控主循环"""
        logger.info("消息监控循环已启动")

        while self._monitoring:
            try:
                # 检查新消息
                contacts = self.check_new_messages()

                for contact in contacts:
                    if not self._monitoring:
                        break

                    if contact == "_unknown_":
                        # 需要打开聊天查看
                        continue

                    # 通知回调
                    if self._on_new_message:
                        try:
                            self._on_new_message(contact)
                        except Exception as e:
                            logger.error(f"新消息回调异常: {e}")

                    if self._mode == ReplyMode.FULL_AUTO:
                        self._auto_process_contact(contact)
                    elif self._mode == ReplyMode.SEMI_AUTO:
                        # 半自动模式：只记录，不自动回复
                        msg_info = MessageInfo(contact=contact, content="")
                        with self._lock:
                            self._message_queue.append(msg_info)

                time.sleep(self._check_interval)

            except Exception as e:
                logger.error(f"消息监控异常: {e}")
                time.sleep(self._check_interval * 2)

        logger.info("消息监控循环已退出")

    def _auto_process_contact(self, contact: str) -> None:
        """全自动处理联系人的新消息"""
        try:
            # 检查每日回复限额
            if self._daily_reply_count >= self._anti_risk.daily_limits.auto_reply:
                logger.warning("已达每日自动回复上限")
                return

            # 打开聊天
            if not self._controller.open_chat(contact):
                return

            smart_delay()

            # 读取最新消息（简化处理：从聊天窗口获取）
            latest_message = self._get_latest_message()
            if not latest_message:
                return

            # 处理消息
            reply = self.process_message(contact, latest_message)
            if reply:
                # 发送回复
                smart_delay()
                if self._controller.send_text_message(reply):
                    self._daily_reply_count += 1
                    msg_info = MessageInfo(
                        contact=contact,
                        content=latest_message,
                        processed=True,
                        replied=True,
                        reply_content=reply,
                    )
                    with self._lock:
                        self._processed_messages.append(msg_info)

                    if self._on_reply_sent:
                        try:
                            self._on_reply_sent(contact, reply)
                        except Exception:
                            pass

                    logger.info(f"自动回复: {contact} -> {reply[:50]}")

        except Exception as e:
            logger.error(f"自动处理联系人消息失败 ({contact}): {e}")

    def _get_latest_message(self) -> str:
        """获取当前聊天窗口的最新消息"""
        try:
            if self._controller._main_window:
                from core.wechat_controller import PYWINAUTO_AVAILABLE
                if PYWINAUTO_AVAILABLE:
                    # 尝试获取聊天记录列表中的最后一条
                    texts = self._controller._main_window.descendants(control_type="Text")
                    if texts:
                        # 获取最后几条文本
                        recent_texts = []
                        for t in texts[-10:]:
                            try:
                                text = t.window_text()
                                if text and text.strip() and len(text) > 1:
                                    recent_texts.append(text.strip())
                            except Exception:
                                continue
                        if recent_texts:
                            return recent_texts[-1]
        except Exception as e:
            logger.debug(f"获取最新消息失败: {e}")

        return ""

    def get_pending_messages(self) -> List[MessageInfo]:
        """获取待处理的消息队列（半自动模式）"""
        with self._lock:
            return list(self._message_queue)

    def get_processed_messages(self) -> List[MessageInfo]:
        """获取已处理的消息列表"""
        with self._lock:
            return self._processed_messages.copy()

    def manual_reply(self, contact: str, reply: str) -> bool:
        """
        手动回复（半自动模式使用）

        参数:
            contact: 联系人
            reply: 回复内容
        返回:
            是否发送成功
        """
        try:
            if not self._controller.open_chat(contact):
                return False
            smart_delay()
            return self._controller.send_text_message(reply)
        except Exception as e:
            logger.error(f"手动回复失败 ({contact}): {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "monitoring": self._monitoring,
                "mode": self._mode.value,
                "rules_count": len(self._keyword_rules),
                "pending_count": len(self._message_queue),
                "processed_count": len(self._processed_messages),
                "daily_reply_count": self._daily_reply_count,
            }
