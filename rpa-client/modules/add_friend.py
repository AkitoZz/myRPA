"""
加好友模块

提供通过手机号、微信号、群组等方式添加好友的功能，
以及自动接受好友请求的功能。所有操作遵循反风控策略。
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from loguru import logger

from core.wechat_controller import WeChatController
from core.element_locator import ElementConfig
from config.anti_risk import AntiRiskConfig
from utils.delay import smart_delay, random_delay, fatigue_check, is_work_hours, reset_operation_count


@dataclass
class AddFriendResult:
    """加好友结果"""
    target: str
    success: bool
    method: str = ""
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class AddFriendModule:
    """加好友模块"""

    def __init__(self, controller: WeChatController, anti_risk: Optional[AntiRiskConfig] = None):
        """
        初始化加好友模块

        参数:
            controller: 微信控制器
            anti_risk: 反风控配置
        """
        self._controller = controller
        self._anti_risk = anti_risk or AntiRiskConfig()
        self._daily_count = 0
        self._daily_date = date.today()
        self._results: List[AddFriendResult] = []

    def _check_daily_limit(self) -> bool:
        """检查每日限额"""
        today = date.today()
        if self._daily_date != today:
            self._daily_count = 0
            self._daily_date = today

        if self._daily_count >= self._anti_risk.daily_limits.add_friend:
            logger.warning(f"已达每日加好友上限: {self._anti_risk.daily_limits.add_friend}")
            return False
        return True

    def add_by_phone(self, phone_number: str, greeting: str = "你好，请求添加好友") -> bool:
        """
        通过手机号添加好友

        参数:
            phone_number: 手机号码
            greeting: 验证消息
        返回:
            是否发送请求成功
        """
        if not self._check_daily_limit():
            return False

        if not is_work_hours():
            logger.info("当前不在工作时间内，跳过操作")
            return False

        logger.info(f"通过手机号添加好友: {phone_number}")

        try:
            # 1. 搜索联系人
            if not self._controller.search_contact(phone_number):
                self._record_result(phone_number, False, "phone", "搜索失败")
                return False

            smart_delay()

            # 2. 点击搜索结果中的"搜索: xxx"
            import pyautogui
            time.sleep(1.5)
            pyautogui.press("enter")
            time.sleep(1.0)

            # 3. 点击"添加到通讯录"按钮
            result = self._controller._locator.locate_by_name("add_friend_button", retry=3)
            if result.found:
                self._controller._click_at(result.center[0], result.center[1])
                time.sleep(0.8)
            else:
                # 可能已经是好友
                logger.info(f"{phone_number} 可能已经是好友或无法添加")
                pyautogui.press("escape")
                self._record_result(phone_number, False, "phone", "未找到添加按钮")
                return False

            # 4. 填写验证消息
            greeting_result = self._controller._locator.locate_by_name("friend_request_greeting", retry=2)
            if greeting_result.found:
                self._controller._click_at(greeting_result.center[0], greeting_result.center[1])
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.1)
                self._controller._type_text(greeting)
                smart_delay()

            # 5. 点击发送请求
            send_result = self._controller._locator.locate_by_name("send_request_button", retry=2)
            if send_result.found:
                self._controller._click_at(send_result.center[0], send_result.center[1])
                time.sleep(0.5)
            else:
                # 备选：查找"发送"按钮
                import pyautogui
                pyautogui.press("enter")
                time.sleep(0.5)

            self._daily_count += 1
            fatigue_check()
            self._record_result(phone_number, True, "phone")
            logger.info(f"好友请求已发送: {phone_number}")
            return True

        except Exception as e:
            logger.error(f"添加好友失败 ({phone_number}): {e}")
            self._record_result(phone_number, False, "phone", str(e))
            # 恢复状态
            try:
                import pyautogui
                pyautogui.press("escape")
                time.sleep(0.3)
                pyautogui.press("escape")
            except Exception:
                pass
            return False

    def add_by_wxid(self, wxid: str, greeting: str = "你好，请求添加好友") -> bool:
        """
        通过微信号添加好友

        参数:
            wxid: 微信号
            greeting: 验证消息
        返回:
            是否发送请求成功
        """
        if not self._check_daily_limit():
            return False

        if not is_work_hours():
            logger.info("当前不在工作时间内，跳过操作")
            return False

        logger.info(f"通过微信号添加好友: {wxid}")

        try:
            # 流程与手机号添加基本一致
            if not self._controller.search_contact(wxid):
                self._record_result(wxid, False, "wxid", "搜索失败")
                return False

            smart_delay()

            import pyautogui
            time.sleep(1.5)
            pyautogui.press("enter")
            time.sleep(1.0)

            # 点击添加按钮
            result = self._controller._locator.locate_by_name("add_friend_button", retry=3)
            if result.found:
                self._controller._click_at(result.center[0], result.center[1])
                time.sleep(0.8)
            else:
                logger.info(f"{wxid} 可能已经是好友或无法添加")
                pyautogui.press("escape")
                self._record_result(wxid, False, "wxid", "未找到添加按钮")
                return False

            # 填写验证消息
            greeting_result = self._controller._locator.locate_by_name("friend_request_greeting", retry=2)
            if greeting_result.found:
                self._controller._click_at(greeting_result.center[0], greeting_result.center[1])
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.1)
                self._controller._type_text(greeting)
                smart_delay()

            # 发送请求
            send_result = self._controller._locator.locate_by_name("send_request_button", retry=2)
            if send_result.found:
                self._controller._click_at(send_result.center[0], send_result.center[1])
                time.sleep(0.5)
            else:
                pyautogui.press("enter")
                time.sleep(0.5)

            self._daily_count += 1
            fatigue_check()
            self._record_result(wxid, True, "wxid")
            logger.info(f"好友请求已发送: {wxid}")
            return True

        except Exception as e:
            logger.error(f"添加好友失败 ({wxid}): {e}")
            self._record_result(wxid, False, "wxid", str(e))
            try:
                import pyautogui
                pyautogui.press("escape")
                time.sleep(0.3)
                pyautogui.press("escape")
            except Exception:
                pass
            return False

    def add_from_group(self, group_name: str, count: int = 10) -> List[AddFriendResult]:
        """
        从群聊中添加好友

        参数:
            group_name: 群聊名称
            count: 要添加的数量
        返回:
            添加结果列表
        """
        results = []

        if not self._check_daily_limit():
            return results

        logger.info(f"从群 '{group_name}' 添加好友，目标: {count} 人")

        try:
            # 打开群聊
            if not self._controller.open_chat(group_name):
                logger.error(f"无法打开群聊: {group_name}")
                return results

            smart_delay()

            # 打开群成员列表 - 点击群聊标题或群成员图标
            import pyautogui

            # 尝试点击右上角的群成员按钮
            if self._controller._main_window:
                try:
                    rect = self._controller._main_window.rectangle()
                    # 群成员按钮通常在聊天窗口右上角
                    member_btn_x = rect.right - 60
                    member_btn_y = rect.top + 50
                    self._controller._click_at(member_btn_x, member_btn_y)
                    time.sleep(1.0)
                except Exception:
                    pass

            # 获取群成员列表
            members = self._controller.get_chat_list(count=count * 2)

            added = 0
            for member in members:
                if added >= count:
                    break

                if not self._check_daily_limit():
                    break

                if not is_work_hours():
                    logger.info("已到非工作时间，暂停操作")
                    break

                try:
                    # 点击成员头像
                    # 这里简化处理：通过搜索成员名来添加
                    success = self.add_by_wxid(member, "我们同在一个群，请求添加好友")
                    result = AddFriendResult(
                        target=member,
                        success=success,
                        method="group",
                    )
                    results.append(result)
                    if success:
                        added += 1
                    smart_delay()

                except Exception as e:
                    logger.error(f"从群添加成员失败 ({member}): {e}")
                    results.append(AddFriendResult(
                        target=member, success=False, method="group", error=str(e)
                    ))

            # 关闭群成员面板
            pyautogui.press("escape")

        except Exception as e:
            logger.error(f"从群添加好友失败: {e}")

        logger.info(f"从群添加完成: 成功 {sum(1 for r in results if r.success)}/{len(results)}")
        return results

    def auto_accept_requests(self, check_interval: float = 5.0, max_duration: float = 3600.0) -> int:
        """
        自动接受好友请求

        参数:
            check_interval: 检查间隔（秒）
            max_duration: 最大运行时长（秒）
        返回:
            接受的好友请求数
        """
        accepted = 0
        start_time = time.time()

        logger.info(f"开始自动接受好友请求，检查间隔: {check_interval}秒")

        while time.time() - start_time < max_duration:
            try:
                if self._controller.accept_friend_request():
                    accepted += 1
                    logger.info(f"已接受好友请求 (累计: {accepted})")
                    smart_delay()
                else:
                    time.sleep(check_interval)

            except Exception as e:
                logger.error(f"检查好友请求异常: {e}")
                time.sleep(check_interval * 2)

        logger.info(f"自动接受好友请求结束，共接受 {accepted} 个")
        return accepted

    def _record_result(self, target: str, success: bool, method: str, error: str = "") -> None:
        """记录操作结果"""
        result = AddFriendResult(
            target=target,
            success=success,
            method=method,
            error=error,
        )
        self._results.append(result)

    def get_results(self) -> List[AddFriendResult]:
        """获取所有操作结果"""
        return self._results.copy()

    def get_daily_count(self) -> int:
        """获取今日已添加数量"""
        today = date.today()
        if self._daily_date != today:
            self._daily_count = 0
            self._daily_date = today
        return self._daily_count

    def reset_daily_count(self) -> None:
        """重置每日计数"""
        self._daily_count = 0
        self._daily_date = date.today()
        reset_operation_count()
