"""
登录窗口模块

提供用户登录/注册界面，包含服务器地址设置和记住密码功能。
"""

import sys
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QMessageBox, QDialog, QFormLayout,
    QGroupBox, QApplication,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QIcon

from loguru import logger

from config.settings import get_settings, Settings
from network.api_client import APIClient, APIError
from network.auth import AuthManager
from utils.crypto import hash_password


class LoginWorker(QThread):
    """登录工作线程"""
    login_success = pyqtSignal(dict)
    login_failed = pyqtSignal(str)

    def __init__(self, api_client: APIClient, phone: str, password: str):
        super().__init__()
        self._api_client = api_client
        self._phone = phone
        self._password = password

    def run(self):
        try:
            result = self._api_client.login(self._phone, self._password)
            self.login_success.emit(result)
        except APIError as e:
            self.login_failed.emit(str(e))
        except Exception as e:
            self.login_failed.emit(f"登录失败: {e}")


class RegisterWorker(QThread):
    """注册工作线程"""
    register_success = pyqtSignal(dict)
    register_failed = pyqtSignal(str)

    def __init__(self, api_client: APIClient, phone: str, password: str):
        super().__init__()
        self._api_client = api_client
        self._phone = phone
        self._password = password

    def run(self):
        try:
            result = self._api_client.register(self._phone, self._password)
            self.register_success.emit(result)
        except APIError as e:
            self.register_failed.emit(str(e))
        except Exception as e:
            self.register_failed.emit(f"注册失败: {e}")


class LoginWindow(QWidget):
    """登录窗口"""

    login_successful = pyqtSignal(str, str)  # token, phone

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = get_settings()
        self._api_client = APIClient()
        self._auth_manager = AuthManager()
        self._login_worker: Optional[LoginWorker] = None
        self._register_worker: Optional[RegisterWorker] = None

        self._init_ui()
        self._load_saved_credentials()

    def _init_ui(self):
        """初始化界面"""
        self.setWindowTitle("MyRPA - 登录")
        self.setFixedSize(
            self._settings.ui.login_window_width,
            self._settings.ui.login_window_height,
        )
        self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(15)

        # 标题
        title_label = QLabel("MyRPA 微信自动化")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        subtitle_label = QLabel("智能微信RPA管理系统")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #666; font-size: 12px;")
        main_layout.addWidget(subtitle_label)

        main_layout.addSpacing(10)

        # 手机号输入
        phone_label = QLabel("手机号")
        self._phone_input = QLineEdit()
        self._phone_input.setPlaceholderText("请输入手机号")
        self._phone_input.setMaxLength(11)
        self._phone_input.setMinimumHeight(35)
        main_layout.addWidget(phone_label)
        main_layout.addWidget(self._phone_input)

        # 密码输入
        password_label = QLabel("密码")
        self._password_input = QLineEdit()
        self._password_input.setPlaceholderText("请输入密码")
        self._password_input.setEchoMode(QLineEdit.Password)
        self._password_input.setMinimumHeight(35)
        main_layout.addWidget(password_label)
        main_layout.addWidget(self._password_input)

        # 记住密码
        options_layout = QHBoxLayout()
        self._remember_cb = QCheckBox("记住密码")
        self._remember_cb.setChecked(self._settings.remember_password)
        options_layout.addWidget(self._remember_cb)

        server_btn = QPushButton("服务器设置")
        server_btn.setFlat(True)
        server_btn.setStyleSheet("color: #0078d7; border: none; text-decoration: underline;")
        server_btn.clicked.connect(self._show_server_settings)
        options_layout.addStretch()
        options_layout.addWidget(server_btn)
        main_layout.addLayout(options_layout)

        main_layout.addSpacing(5)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self._login_btn = QPushButton("登 录")
        self._login_btn.setMinimumHeight(40)
        self._login_btn.setStyleSheet("""
            QPushButton {
                background-color: #07c160;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #06ad56;
            }
            QPushButton:pressed {
                background-color: #059a4c;
            }
            QPushButton:disabled {
                background-color: #a0d4b4;
            }
        """)
        self._login_btn.clicked.connect(self._on_login)

        self._register_btn = QPushButton("注 册")
        self._register_btn.setMinimumHeight(40)
        self._register_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
            QPushButton:pressed {
                background-color: #ddd;
            }
            QPushButton:disabled {
                color: #aaa;
            }
        """)
        self._register_btn.clicked.connect(self._on_register)

        btn_layout.addWidget(self._login_btn)
        btn_layout.addWidget(self._register_btn)
        main_layout.addLayout(btn_layout)

        # 状态标签
        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setStyleSheet("color: #999; font-size: 11px;")
        main_layout.addWidget(self._status_label)

        # 版本信息
        main_layout.addStretch()
        version_label = QLabel("v1.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #ccc; font-size: 10px;")
        main_layout.addWidget(version_label)

        self.setLayout(main_layout)

        # 回车触发登录
        self._password_input.returnPressed.connect(self._on_login)
        self._phone_input.returnPressed.connect(lambda: self._password_input.setFocus())

        # 居中显示
        self._center_window()

    def _center_window(self):
        """居中显示窗口"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            x = (screen_geo.width() - self.width()) // 2
            y = (screen_geo.height() - self.height()) // 2
            self.move(x, y)

    def _load_saved_credentials(self):
        """加载已保存的凭据"""
        if self._settings.remember_password and self._settings.saved_phone:
            self._phone_input.setText(self._settings.saved_phone)

        # 检查是否有有效的令牌
        token = self._auth_manager.load_token()
        if token:
            self._status_label.setText("检测到已保存的登录状态")

    def _on_login(self):
        """处理登录"""
        phone = self._phone_input.text().strip()
        password = self._password_input.text()

        if not phone:
            QMessageBox.warning(self, "提示", "请输入手机号")
            self._phone_input.setFocus()
            return

        if not password:
            QMessageBox.warning(self, "提示", "请输入密码")
            self._password_input.setFocus()
            return

        # 禁用按钮
        self._login_btn.setEnabled(False)
        self._register_btn.setEnabled(False)
        self._status_label.setText("正在登录...")
        self._status_label.setStyleSheet("color: #0078d7; font-size: 11px;")

        # 启动登录线程
        self._login_worker = LoginWorker(self._api_client, phone, password)
        self._login_worker.login_success.connect(self._on_login_success)
        self._login_worker.login_failed.connect(self._on_login_failed)
        self._login_worker.start()

    def _on_login_success(self, result: dict):
        """登录成功处理"""
        token = result.get("token", "")
        phone = self._phone_input.text().strip()

        # 保存令牌
        self._auth_manager.save_token(token)

        # 保存凭据
        if self._remember_cb.isChecked():
            self._settings.remember_password = True
            self._settings.saved_phone = phone
            self._settings.saved_password_hash = hash_password(self._password_input.text())
        else:
            self._settings.remember_password = False
            self._settings.saved_phone = ""
            self._settings.saved_password_hash = ""
        self._settings.save()

        self._status_label.setText("登录成功！")
        self._status_label.setStyleSheet("color: #07c160; font-size: 11px;")
        logger.info(f"用户登录成功: {phone}")

        # 发射登录成功信号
        self.login_successful.emit(token, phone)

    def _on_login_failed(self, error: str):
        """登录失败处理"""
        self._login_btn.setEnabled(True)
        self._register_btn.setEnabled(True)
        self._status_label.setText(error)
        self._status_label.setStyleSheet("color: #e74c3c; font-size: 11px;")
        logger.warning(f"登录失败: {error}")

    def _on_register(self):
        """处理注册"""
        phone = self._phone_input.text().strip()
        password = self._password_input.text()

        if not phone:
            QMessageBox.warning(self, "提示", "请输入手机号")
            self._phone_input.setFocus()
            return

        if not password:
            QMessageBox.warning(self, "提示", "请输入密码")
            self._password_input.setFocus()
            return

        if len(password) < 6:
            QMessageBox.warning(self, "提示", "密码长度至少6位")
            return

        reply = QMessageBox.question(
            self, "确认注册",
            f"确定使用手机号 {phone} 进行注册？",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        self._login_btn.setEnabled(False)
        self._register_btn.setEnabled(False)
        self._status_label.setText("正在注册...")
        self._status_label.setStyleSheet("color: #0078d7; font-size: 11px;")

        self._register_worker = RegisterWorker(self._api_client, phone, password)
        self._register_worker.register_success.connect(self._on_register_success)
        self._register_worker.register_failed.connect(self._on_register_failed)
        self._register_worker.start()

    def _on_register_success(self, result: dict):
        """注册成功处理"""
        self._login_btn.setEnabled(True)
        self._register_btn.setEnabled(True)
        self._status_label.setText("注册成功，请登录")
        self._status_label.setStyleSheet("color: #07c160; font-size: 11px;")
        QMessageBox.information(self, "注册成功", "账号注册成功，请使用手机号和密码登录。")

    def _on_register_failed(self, error: str):
        """注册失败处理"""
        self._login_btn.setEnabled(True)
        self._register_btn.setEnabled(True)
        self._status_label.setText(error)
        self._status_label.setStyleSheet("color: #e74c3c; font-size: 11px;")

    def _show_server_settings(self):
        """显示服务器设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("服务器设置")
        dialog.setFixedSize(350, 200)

        layout = QVBoxLayout()

        form_layout = QFormLayout()

        api_input = QLineEdit(self._settings.server.api_url)
        api_input.setMinimumHeight(30)
        form_layout.addRow("API地址:", api_input)

        ws_input = QLineEdit(self._settings.server.ws_url)
        ws_input.setMinimumHeight(30)
        form_layout.addRow("WS地址:", ws_input)

        layout.addLayout(form_layout)
        layout.addSpacing(10)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.setMinimumHeight(35)
        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumHeight(35)

        def save_settings():
            self._settings.server.api_url = api_input.text().strip()
            self._settings.server.ws_url = ws_input.text().strip()
            self._settings.save()
            self._api_client.set_base_url(self._settings.server.api_url)
            dialog.accept()
            QMessageBox.information(self, "提示", "服务器地址已保存")

        save_btn.clicked.connect(save_settings)
        cancel_btn.clicked.connect(dialog.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        dialog.setLayout(layout)
        dialog.exec_()

    def get_api_client(self) -> APIClient:
        """获取API客户端"""
        return self._api_client

    def get_auth_manager(self) -> AuthManager:
        """获取认证管理器"""
        return self._auth_manager
