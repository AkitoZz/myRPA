"""
群管理模块

提供群成员邀请、群成员列表获取、群公告发送、移除群成员等功能。
"""

import time
from typing import Optional, List, Dict, Any

import pyautogui
from loguru import logger

from core.wechat_controller import WeChatController, IS_WINDOWS, PYWINAUTO_AVAILABLE
from config.anti_risk import AntiRiskConfig
from utils.delay import smart_delay, random_delay, fatigue_check


class GroupManagerModule:
    """群管理模块"""

    def __init__(self, controller: WeChatController, anti_risk: Optional[AntiRiskConfig] = None):
        """
        初始化群管理模块

        参数:
            controller: 微信控制器
            anti_risk: 反风控配置
        """
        self._controller = controller
        self._anti_risk = anti_risk or AntiRiskConfig()

    def invite_to_group(self, group_name: str, contacts: List[str]) -> Dict[str, Any]:
        """
        邀请联系人加入群聊

        参数:
            group_name: 群聊名称
            contacts: 要邀请的联系人列表
        返回:
            邀请结果统计
        """
        results = {
            "total": len(contacts),
            "success": 0,
            "failed": 0,
            "details": [],
        }

        logger.info(f"开始邀请 {len(contacts)} 人加入群 '{group_name}'")

        try:
            # 1. 打开群聊
            if not self._controller.open_chat(group_name):
                logger.error(f"无法打开群聊: {group_name}")
                results["failed"] = len(contacts)
                return results

            smart_delay()

            # 2. 打开群设置（点击右上角群聊头像区域）
            if self._controller._main_window and PYWINAUTO_AVAILABLE:
                try:
                    rect = self._controller._main_window.rectangle()
                    # 群成员区域通常在右上角
                    settings_x = rect.right - 50
                    settings_y = rect.top + 50
                    self._controller._click_at(settings_x, settings_y)
                    time.sleep(1.0)
                except Exception as e:
                    logger.error(f"打开群设置失败: {e}")

            # 3. 点击"邀请成员"按钮（通常是"+"按钮）
            invite_result = self._controller._locator.locate_by_name("group_invite_button", retry=2)
            if invite_result.found:
                self._controller._click_at(invite_result.center[0], invite_result.center[1])
                time.sleep(1.0)

            # 4. 逐个搜索并选择联系人
            for contact in contacts:
                try:
                    # 在邀请对话框中搜索联系人
                    # 查找搜索框
                    search_result = self._controller._locator.locate_by_name("invite_search_box", retry=1)
                    if search_result.found:
                        self._controller._click_at(search_result.center[0], search_result.center[1])
                    else:
                        # 备用：直接输入
                        pyautogui.hotkey("ctrl", "f")

                    time.sleep(0.3)
                    pyautogui.hotkey("ctrl", "a")
                    self._controller._type_text(contact)
                    time.sleep(0.8)

                    # 选择搜索结果（点击第一个匹配项）
                    pyautogui.press("enter")
                    time.sleep(0.3)

                    results["success"] += 1
                    results["details"].append({"contact": contact, "success": True})
                    logger.debug(f"已选择联系人: {contact}")

                    smart_delay()

                except Exception as e:
                    results["failed"] += 1
                    results["details"].append({"contact": contact, "success": False, "error": str(e)})
                    logger.warning(f"选择联系人失败 ({contact}): {e}")

            # 5. 确认邀请
            time.sleep(0.5)
            confirm_result = self._controller._locator.locate_by_name("confirm_invite_button", retry=2)
            if confirm_result.found:
                self._controller._click_at(confirm_result.center[0], confirm_result.center[1])
            else:
                # 备用：按确定
                pyautogui.press("enter")

            time.sleep(1.0)

            # 关闭面板
            pyautogui.press("escape")

        except Exception as e:
            logger.error(f"邀请入群失败: {e}")
            results["failed"] = len(contacts) - results["success"]

        logger.info(f"邀请完成: 成功={results['success']}, 失败={results['failed']}")
        return results

    def get_group_members(self, group_name: str) -> List[str]:
        """
        获取群成员列表

        参数:
            group_name: 群聊名称
        返回:
            群成员名称列表
        """
        members = []

        logger.info(f"获取群 '{group_name}' 的成员列表")

        try:
            # 打开群聊
            if not self._controller.open_chat(group_name):
                logger.error(f"无法打开群聊: {group_name}")
                return members

            smart_delay()

            # 打开群成员面板
            if self._controller._main_window and PYWINAUTO_AVAILABLE:
                try:
                    rect = self._controller._main_window.rectangle()
                    # 点击群聊标题区域显示成员
                    title_x = rect.left + (rect.width() * 3 // 4)
                    title_y = rect.top + 30
                    self._controller._click_at(title_x, title_y)
                    time.sleep(1.0)

                    # 查看全部成员
                    view_all = self._controller._locator.locate_by_name("view_all_members", retry=1)
                    if view_all.found:
                        self._controller._click_at(view_all.center[0], view_all.center[1])
                        time.sleep(1.0)

                    # 通过UIA获取成员列表
                    list_items = self._controller._main_window.descendants(
                        control_type="ListItem"
                    )
                    for item in list_items:
                        try:
                            name = item.window_text()
                            if name and name.strip():
                                # 过滤掉非成员项
                                if name not in ["邀请", "+", "-"]:
                                    members.append(name.strip())
                        except Exception:
                            continue

                except Exception as e:
                    logger.error(f"获取群成员失败: {e}")

            # 关闭面板
            pyautogui.press("escape")
            time.sleep(0.3)

        except Exception as e:
            logger.error(f"获取群成员列表异常: {e}")

        logger.info(f"获取到 {len(members)} 个群成员")
        return members

    def send_group_notice(self, group_name: str, message: str) -> bool:
        """
        发送群公告

        参数:
            group_name: 群聊名称
            message: 公告内容
        返回:
            是否发送成功
        """
        logger.info(f"发送群公告到 '{group_name}'")

        try:
            # 打开群聊
            if not self._controller.open_chat(group_name):
                logger.error(f"无法打开群聊: {group_name}")
                return False

            smart_delay()

            # 打开群设置
            if self._controller._main_window and PYWINAUTO_AVAILABLE:
                try:
                    rect = self._controller._main_window.rectangle()
                    settings_x = rect.right - 50
                    settings_y = rect.top + 50
                    self._controller._click_at(settings_x, settings_y)
                    time.sleep(1.0)
                except Exception:
                    pass

            # 查找群公告入口
            notice_result = self._controller._locator.locate_by_name("group_notice", retry=2)
            if notice_result.found:
                self._controller._click_at(notice_result.center[0], notice_result.center[1])
                time.sleep(1.0)

                # 输入公告内容
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.1)
                self._controller._type_text(message)
                smart_delay()

                # 发布公告
                publish_result = self._controller._locator.locate_by_name("publish_notice_button", retry=1)
                if publish_result.found:
                    self._controller._click_at(publish_result.center[0], publish_result.center[1])
                else:
                    pyautogui.press("enter")

                time.sleep(0.5)

                # 确认发布
                pyautogui.press("enter")
                time.sleep(0.5)

                logger.info(f"群公告已发送到 '{group_name}'")
                pyautogui.press("escape")
                return True
            else:
                logger.warning("未找到群公告入口")
                # 备选：直接发送@all消息
                self._controller.send_text_message(f"[公告] {message}")
                return True

        except Exception as e:
            logger.error(f"发送群公告失败: {e}")
            try:
                pyautogui.press("escape")
            except Exception:
                pass
            return False

    def remove_member(self, group_name: str, member: str) -> bool:
        """
        从群聊中移除成员

        参数:
            group_name: 群聊名称
            member: 要移除的成员名称
        返回:
            是否成功移除
        """
        logger.info(f"从群 '{group_name}' 移除成员: {member}")

        try:
            # 打开群聊
            if not self._controller.open_chat(group_name):
                logger.error(f"无法打开群聊: {group_name}")
                return False

            smart_delay()

            # 打开群设置
            if self._controller._main_window and PYWINAUTO_AVAILABLE:
                try:
                    rect = self._controller._main_window.rectangle()
                    settings_x = rect.right - 50
                    settings_y = rect.top + 50
                    self._controller._click_at(settings_x, settings_y)
                    time.sleep(1.0)
                except Exception:
                    pass

            # 点击"-"（删除成员）按钮
            remove_btn = self._controller._locator.locate_by_name("remove_member_button", retry=2)
            if remove_btn.found:
                self._controller._click_at(remove_btn.center[0], remove_btn.center[1])
                time.sleep(1.0)

                # 搜索要移除的成员
                self._controller._type_text(member)
                time.sleep(0.8)

                # 选择成员
                pyautogui.press("enter")
                time.sleep(0.3)

                # 确认移除
                confirm_result = self._controller._locator.locate_by_name("confirm_remove_button", retry=1)
                if confirm_result.found:
                    self._controller._click_at(confirm_result.center[0], confirm_result.center[1])
                else:
                    pyautogui.press("enter")

                time.sleep(0.5)

                # 二次确认
                pyautogui.press("enter")
                time.sleep(0.5)

                logger.info(f"已从群 '{group_name}' 移除: {member}")
                pyautogui.press("escape")
                return True
            else:
                logger.warning("未找到移除成员按钮（可能没有群管理权限）")
                pyautogui.press("escape")
                return False

        except Exception as e:
            logger.error(f"移除群成员失败: {e}")
            try:
                pyautogui.press("escape")
            except Exception:
                pass
            return False
