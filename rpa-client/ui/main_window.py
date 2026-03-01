"""
主窗口模块

应用程序主界面，提供微信管理、加好友、群发消息、自动回复、任务列表等功能标签页。
"""

import sys
import time
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QTextEdit, QLineEdit, QListWidget,
    QListWidgetItem, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QFormLayout, QComboBox, QSpinBox, QCheckBox,
    QMessageBox, QStatusBar, QAction, QMenu, QMenuBar,
    QSplitter, QFrame, QProgressBar, QFileDialog, QApplication,
    QPlainTextEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QIcon

from loguru import logger

from config.settings import get_settings
from core.engine import RPAEngine
from core.task_scheduler import TaskState
from network.api_client import APIClient
from network.ws_client import WebSocketClient
from network.auth import AuthManager
from ui.tray_icon import TrayIcon


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(
        self,
        token: str,
        phone: str,
        api_client: APIClient,
        auth_manager: AuthManager,
        parent=None,
    ):
        super().__init__(parent)
        self._token = token
        self._phone = phone
        self._api_client = api_client
        self._auth_manager = auth_manager
        self._settings = get_settings()

        # 初始化引擎
        self._engine = RPAEngine()
        self._engine.initialize()
        self._engine.add_status_callback(self._on_engine_status_change)

        # WebSocket客户端
        self._ws_client = WebSocketClient(token=token)

        # 系统托盘
        self._tray_icon: Optional[TrayIcon] = None

        # 刷新定时器
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_status)
        self._refresh_timer.start(5000)

        self._init_ui()
        self._init_tray_icon()
        self._connect_websocket()

    def _init_ui(self):
        """初始化界面"""
        self.setWindowTitle(f"MyRPA 微信自动化 - {self._phone}")
        self.resize(
            self._settings.ui.main_window_width,
            self._settings.ui.main_window_height,
        )

        # 菜单栏
        self._init_menu_bar()

        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # 标签页
        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ddd; }
            QTabBar::tab {
                padding: 8px 20px;
                min-width: 80px;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background: #07c160;
                color: white;
                border-radius: 3px 3px 0 0;
            }
        """)

        # 各功能标签页
        self._tab_widget.addTab(self._create_wechat_tab(), "微信管理")
        self._tab_widget.addTab(self._create_add_friend_tab(), "加好友")
        self._tab_widget.addTab(self._create_mass_msg_tab(), "群发消息")
        self._tab_widget.addTab(self._create_auto_reply_tab(), "自动回复")
        self._tab_widget.addTab(self._create_task_tab(), "任务列表")

        main_layout.addWidget(self._tab_widget)

        # 状态栏
        self._init_status_bar()

        # 居中显示
        self._center_window()

    def _init_menu_bar(self):
        """初始化菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        logout_action = QAction("退出登录", self)
        logout_action.triggered.connect(self._logout)
        file_menu.addAction(logout_action)

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self._quit_app)
        file_menu.addAction(exit_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_status_bar(self):
        """初始化状态栏"""
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        # 连接状态
        self._conn_label = QLabel("服务器: 未连接")
        self._conn_label.setStyleSheet("color: #999;")
        self._status_bar.addWidget(self._conn_label)

        # 微信状态
        self._wechat_label = QLabel("微信: 未连接")
        self._wechat_label.setStyleSheet("color: #999;")
        self._status_bar.addWidget(self._wechat_label)

        # 账号信息
        self._account_label = QLabel(f"账号: {self._phone}")
        self._status_bar.addPermanentWidget(self._account_label)

    def _create_wechat_tab(self) -> QWidget:
        """创建微信管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 操作按钮区
        btn_group = QGroupBox("快捷操作")
        btn_layout = QHBoxLayout()

        self._launch_btn = QPushButton("启动微信")
        self._launch_btn.setMinimumHeight(35)
        self._launch_btn.clicked.connect(self._launch_wechat)
        btn_layout.addWidget(self._launch_btn)

        self._connect_btn = QPushButton("连接微信")
        self._connect_btn.setMinimumHeight(35)
        self._connect_btn.clicked.connect(self._connect_wechat)
        btn_layout.addWidget(self._connect_btn)

        self._disconnect_btn = QPushButton("断开连接")
        self._disconnect_btn.setMinimumHeight(35)
        self._disconnect_btn.clicked.connect(self._disconnect_wechat)
        btn_layout.addWidget(self._disconnect_btn)

        self._refresh_btn = QPushButton("刷新列表")
        self._refresh_btn.setMinimumHeight(35)
        self._refresh_btn.clicked.connect(self._refresh_instances)
        btn_layout.addWidget(self._refresh_btn)

        btn_group.setLayout(btn_layout)
        layout.addWidget(btn_group)

        # 实例列表
        instance_group = QGroupBox("微信实例列表")
        instance_layout = QVBoxLayout()

        self._instance_table = QTableWidget()
        self._instance_table.setColumnCount(5)
        self._instance_table.setHorizontalHeaderLabels(["PID", "窗口标题", "状态", "已连接", "操作"])
        self._instance_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._instance_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._instance_table.setEditTriggers(QTableWidget.NoEditTriggers)

        instance_layout.addWidget(self._instance_table)
        instance_group.setLayout(instance_layout)
        layout.addWidget(instance_group)

        # 窗口信息
        info_group = QGroupBox("当前微信窗口信息")
        info_layout = QFormLayout()

        self._info_hwnd = QLabel("--")
        self._info_pid = QLabel("--")
        self._info_title = QLabel("--")
        self._info_size = QLabel("--")

        info_layout.addRow("窗口句柄:", self._info_hwnd)
        info_layout.addRow("进程ID:", self._info_pid)
        info_layout.addRow("窗口标题:", self._info_title)
        info_layout.addRow("窗口尺寸:", self._info_size)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        return widget

    def _create_add_friend_tab(self) -> QWidget:
        """创建加好友标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 搜索添加
        search_group = QGroupBox("搜索添加好友")
        search_layout = QFormLayout()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("输入手机号或微信号")
        self._search_input.setMinimumHeight(30)
        search_layout.addRow("搜索:", self._search_input)

        self._greeting_input = QLineEdit("你好，请求添加好友")
        self._greeting_input.setMinimumHeight(30)
        search_layout.addRow("验证消息:", self._greeting_input)

        search_btn_layout = QHBoxLayout()
        self._add_phone_btn = QPushButton("按手机号添加")
        self._add_phone_btn.setMinimumHeight(35)
        self._add_phone_btn.clicked.connect(self._add_friend_by_phone)

        self._add_wxid_btn = QPushButton("按微信号添加")
        self._add_wxid_btn.setMinimumHeight(35)
        self._add_wxid_btn.clicked.connect(self._add_friend_by_wxid)

        search_btn_layout.addWidget(self._add_phone_btn)
        search_btn_layout.addWidget(self._add_wxid_btn)
        search_layout.addRow("", search_btn_layout)

        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        # 批量添加
        batch_group = QGroupBox("批量添加 (每行一个)")
        batch_layout = QVBoxLayout()

        self._batch_input = QPlainTextEdit()
        self._batch_input.setPlaceholderText("每行输入一个手机号或微信号")
        self._batch_input.setMaximumHeight(150)
        batch_layout.addWidget(self._batch_input)

        batch_btn_layout = QHBoxLayout()
        self._batch_add_btn = QPushButton("开始批量添加")
        self._batch_add_btn.setMinimumHeight(35)
        self._batch_add_btn.clicked.connect(self._batch_add_friends)
        batch_btn_layout.addWidget(self._batch_add_btn)

        self._batch_progress = QProgressBar()
        self._batch_progress.setVisible(False)
        batch_btn_layout.addWidget(self._batch_progress)

        batch_layout.addLayout(batch_btn_layout)
        batch_group.setLayout(batch_layout)
        layout.addWidget(batch_group)

        # 自动接受
        accept_group = QGroupBox("自动接受好友请求")
        accept_layout = QHBoxLayout()

        self._auto_accept_btn = QPushButton("开始自动接受")
        self._auto_accept_btn.setMinimumHeight(35)
        self._auto_accept_btn.setCheckable(True)
        self._auto_accept_btn.clicked.connect(self._toggle_auto_accept)
        accept_layout.addWidget(self._auto_accept_btn)

        self._accept_count_label = QLabel("今日已添加: 0")
        accept_layout.addWidget(self._accept_count_label)

        accept_group.setLayout(accept_layout)
        layout.addWidget(accept_group)

        layout.addStretch()
        return widget

    def _create_mass_msg_tab(self) -> QWidget:
        """创建群发消息标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 消息内容
        msg_group = QGroupBox("消息内容")
        msg_layout = QVBoxLayout()

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("消息类型:"))
        self._msg_type_combo = QComboBox()
        self._msg_type_combo.addItems(["文本", "图片", "文件"])
        self._msg_type_combo.setMinimumHeight(30)
        type_layout.addWidget(self._msg_type_combo)
        type_layout.addStretch()
        msg_layout.addLayout(type_layout)

        self._msg_content = QPlainTextEdit()
        self._msg_content.setPlaceholderText("输入消息内容（图片/文件请输入完整路径）")
        self._msg_content.setMaximumHeight(120)
        msg_layout.addWidget(self._msg_content)

        browse_layout = QHBoxLayout()
        self._browse_btn = QPushButton("选择文件")
        self._browse_btn.clicked.connect(self._browse_file)
        browse_layout.addWidget(self._browse_btn)
        browse_layout.addStretch()
        msg_layout.addLayout(browse_layout)

        msg_group.setLayout(msg_layout)
        layout.addWidget(msg_group)

        # 目标列表
        target_group = QGroupBox("发送目标 (每行一个联系人/群名)")
        target_layout = QVBoxLayout()

        target_type_layout = QHBoxLayout()
        target_type_layout.addWidget(QLabel("目标类型:"))
        self._target_type_combo = QComboBox()
        self._target_type_combo.addItems(["好友", "群聊"])
        self._target_type_combo.setMinimumHeight(30)
        target_type_layout.addWidget(self._target_type_combo)
        target_type_layout.addStretch()
        target_layout.addLayout(target_type_layout)

        self._target_input = QPlainTextEdit()
        self._target_input.setPlaceholderText("每行输入一个好友名称或群名")
        self._target_input.setMaximumHeight(120)
        target_layout.addWidget(self._target_input)

        target_group.setLayout(target_layout)
        layout.addWidget(target_group)

        # 操作按钮
        action_layout = QHBoxLayout()

        self._mass_send_btn = QPushButton("开始群发")
        self._mass_send_btn.setMinimumHeight(40)
        self._mass_send_btn.setStyleSheet("""
            QPushButton {
                background-color: #07c160;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #06ad56; }
        """)
        self._mass_send_btn.clicked.connect(self._start_mass_message)

        self._mass_stop_btn = QPushButton("停止")
        self._mass_stop_btn.setMinimumHeight(40)
        self._mass_stop_btn.setEnabled(False)
        self._mass_stop_btn.clicked.connect(self._stop_mass_message)

        self._mass_progress = QProgressBar()
        self._mass_progress.setMinimumHeight(25)

        action_layout.addWidget(self._mass_send_btn)
        action_layout.addWidget(self._mass_stop_btn)
        layout.addLayout(action_layout)
        layout.addWidget(self._mass_progress)

        layout.addStretch()
        return widget

    def _create_auto_reply_tab(self) -> QWidget:
        """创建自动回复标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 模式选择
        mode_group = QGroupBox("回复模式")
        mode_layout = QHBoxLayout()

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["全自动 (自动回复)", "半自动 (通知用户)"])
        self._mode_combo.setMinimumHeight(30)
        mode_layout.addWidget(QLabel("模式:"))
        mode_layout.addWidget(self._mode_combo)
        mode_layout.addStretch()

        self._monitor_btn = QPushButton("开始监控")
        self._monitor_btn.setMinimumHeight(35)
        self._monitor_btn.setCheckable(True)
        self._monitor_btn.clicked.connect(self._toggle_monitoring)
        mode_layout.addWidget(self._monitor_btn)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # 关键词规则
        keyword_group = QGroupBox("关键词规则")
        keyword_layout = QVBoxLayout()

        # 添加规则
        add_rule_layout = QHBoxLayout()
        self._keyword_input = QLineEdit()
        self._keyword_input.setPlaceholderText("关键词")
        self._keyword_input.setMinimumHeight(30)
        self._reply_input = QLineEdit()
        self._reply_input.setPlaceholderText("自动回复内容")
        self._reply_input.setMinimumHeight(30)
        add_rule_btn = QPushButton("添加")
        add_rule_btn.setMinimumHeight(30)
        add_rule_btn.clicked.connect(self._add_keyword_rule)

        add_rule_layout.addWidget(self._keyword_input, 2)
        add_rule_layout.addWidget(self._reply_input, 3)
        add_rule_layout.addWidget(add_rule_btn)
        keyword_layout.addLayout(add_rule_layout)

        # 规则列表
        self._rules_table = QTableWidget()
        self._rules_table.setColumnCount(3)
        self._rules_table.setHorizontalHeaderLabels(["关键词", "回复内容", "操作"])
        self._rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._rules_table.setEditTriggers(QTableWidget.NoEditTriggers)
        keyword_layout.addWidget(self._rules_table)

        keyword_group.setLayout(keyword_layout)
        layout.addWidget(keyword_group)

        # 消息日志
        log_group = QGroupBox("消息日志")
        log_layout = QVBoxLayout()
        self._reply_log = QPlainTextEdit()
        self._reply_log.setReadOnly(True)
        self._reply_log.setMaximumHeight(150)
        log_layout.addWidget(self._reply_log)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        return widget

    def _create_task_tab(self) -> QWidget:
        """创建任务列表标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 任务操作
        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("刷新任务")
        refresh_btn.setMinimumHeight(35)
        refresh_btn.clicked.connect(self._refresh_tasks)
        btn_layout.addWidget(refresh_btn)

        clear_btn = QPushButton("清除已完成")
        clear_btn.setMinimumHeight(35)
        clear_btn.clicked.connect(self._clear_completed_tasks)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 任务表格
        self._task_table = QTableWidget()
        self._task_table.setColumnCount(7)
        self._task_table.setHorizontalHeaderLabels(
            ["任务ID", "任务名称", "类型", "状态", "进度", "创建时间", "操作"]
        )
        self._task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._task_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._task_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self._task_table)

        return widget

    def _init_tray_icon(self):
        """初始化系统托盘"""
        self._tray_icon = TrayIcon(self)
        self._tray_icon.show_window_signal.connect(self._show_from_tray)
        self._tray_icon.exit_signal.connect(self._quit_app)
        self._tray_icon.show()

    def _connect_websocket(self):
        """连接WebSocket"""
        try:
            self._ws_client.register_handler("task_command", self._handle_server_command)
            self._ws_client.connect()
            if self._ws_client.is_connected:
                self._conn_label.setText("服务器: 已连接")
                self._conn_label.setStyleSheet("color: #07c160;")
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")

    # ---- 微信管理操作 ----

    def _launch_wechat(self):
        """启动微信"""
        if sys.platform != "win32":
            QMessageBox.warning(self, "提示", "当前平台不支持启动微信")
            return
        pid = self._engine.launch_wechat()
        if pid:
            QMessageBox.information(self, "提示", f"微信已启动，PID: {pid}")
            self._refresh_instances()
        else:
            QMessageBox.warning(self, "提示", "启动微信失败")

    def _connect_wechat(self):
        """连接微信"""
        if self._engine.connect_wechat():
            controller = self._engine.get_active_controller()
            if controller:
                info = controller.get_window_info()
                self._info_hwnd.setText(str(info["hwnd"]))
                self._info_pid.setText(str(info["pid"]))
                self._info_title.setText(info["title"])
                self._info_size.setText(
                    f"{info['size']['width']}x{info['size']['height']}"
                )
                self._wechat_label.setText("微信: 已连接")
                self._wechat_label.setStyleSheet("color: #07c160;")
                QMessageBox.information(self, "提示", "微信已连接")
        else:
            QMessageBox.warning(self, "提示", "连接微信失败，请确认微信已启动")

    def _disconnect_wechat(self):
        """断开微信"""
        self._engine.disconnect_wechat()
        self._info_hwnd.setText("--")
        self._info_pid.setText("--")
        self._info_title.setText("--")
        self._info_size.setText("--")
        self._wechat_label.setText("微信: 未连接")
        self._wechat_label.setStyleSheet("color: #999;")

    def _refresh_instances(self):
        """刷新微信实例列表"""
        instances = self._engine.get_wechat_instances()
        self._instance_table.setRowCount(len(instances))

        for row, inst in enumerate(instances):
            self._instance_table.setItem(row, 0, QTableWidgetItem(str(inst.pid)))
            self._instance_table.setItem(row, 1, QTableWidgetItem(inst.title or "--"))
            self._instance_table.setItem(row, 2, QTableWidgetItem(inst.status))
            self._instance_table.setItem(row, 3, QTableWidgetItem("是" if inst.connected else "否"))

            connect_btn = QPushButton("连接")
            connect_btn.clicked.connect(lambda checked, p=inst.pid: self._connect_to_instance(p))
            self._instance_table.setCellWidget(row, 4, connect_btn)

    def _connect_to_instance(self, pid: int):
        """连接到指定实例"""
        if self._engine.connect_wechat(pid):
            self._refresh_instances()
            self._wechat_label.setText(f"微信: 已连接 (PID:{pid})")
            self._wechat_label.setStyleSheet("color: #07c160;")

    # ---- 加好友操作 ----

    def _add_friend_by_phone(self):
        """按手机号添加好友"""
        target = self._search_input.text().strip()
        greeting = self._greeting_input.text().strip()
        if not target:
            QMessageBox.warning(self, "提示", "请输入手机号")
            return
        self._engine.add_task(
            name=f"添加好友: {target}",
            task_type="add_friend",
            params={"method": "phone", "targets": [target], "greeting": greeting},
        )
        self._status_bar.showMessage("添加好友任务已创建", 3000)

    def _add_friend_by_wxid(self):
        """按微信号添加好友"""
        target = self._search_input.text().strip()
        greeting = self._greeting_input.text().strip()
        if not target:
            QMessageBox.warning(self, "提示", "请输入微信号")
            return
        self._engine.add_task(
            name=f"添加好友: {target}",
            task_type="add_friend",
            params={"method": "wxid", "targets": [target], "greeting": greeting},
        )
        self._status_bar.showMessage("添加好友任务已创建", 3000)

    def _batch_add_friends(self):
        """批量添加好友"""
        text = self._batch_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请输入要添加的号码列表")
            return

        targets = [line.strip() for line in text.split("\n") if line.strip()]
        greeting = self._greeting_input.text().strip()

        self._engine.add_task(
            name=f"批量添加好友 ({len(targets)}个)",
            task_type="add_friend",
            params={"method": "phone", "targets": targets, "greeting": greeting},
        )
        self._status_bar.showMessage(f"批量添加任务已创建: {len(targets)} 个目标", 3000)

    def _toggle_auto_accept(self, checked: bool):
        """切换自动接受"""
        if checked:
            self._auto_accept_btn.setText("停止自动接受")
            self._engine.add_task(
                name="自动接受好友请求",
                task_type="add_friend",
                params={"method": "auto_accept"},
            )
        else:
            self._auto_accept_btn.setText("开始自动接受")

    # ---- 群发消息操作 ----

    def _start_mass_message(self):
        """开始群发"""
        message = self._msg_content.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "提示", "请输入消息内容")
            return

        targets_text = self._target_input.toPlainText().strip()
        if not targets_text:
            QMessageBox.warning(self, "提示", "请输入发送目标")
            return

        targets = [line.strip() for line in targets_text.split("\n") if line.strip()]
        msg_types = {"文本": "text", "图片": "image", "文件": "file"}
        msg_type = msg_types.get(self._msg_type_combo.currentText(), "text")
        target_type = "friend" if self._target_type_combo.currentText() == "好友" else "group"

        reply = QMessageBox.question(
            self, "确认群发",
            f"确定向 {len(targets)} 个{self._target_type_combo.currentText()}发送消息？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._mass_send_btn.setEnabled(False)
        self._mass_stop_btn.setEnabled(True)
        self._mass_progress.setMaximum(len(targets))
        self._mass_progress.setValue(0)

        self._engine.add_task(
            name=f"群发消息 ({len(targets)}个)",
            task_type="mass_message",
            params={
                "targets": targets,
                "message": message,
                "message_type": msg_type,
                "target_type": target_type,
            },
        )

    def _stop_mass_message(self):
        """停止群发"""
        self._mass_send_btn.setEnabled(True)
        self._mass_stop_btn.setEnabled(False)
        # 取消所有群发任务
        for task in self._engine.get_all_tasks():
            if task.task_type == "mass_message" and task.state == TaskState.RUNNING:
                self._engine.cancel_task(task.task_id)

    def _browse_file(self):
        """选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "所有文件 (*);;图片 (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        if file_path:
            self._msg_content.setPlainText(file_path)

    # ---- 自动回复操作 ----

    def _toggle_monitoring(self, checked: bool):
        """切换消息监控"""
        if checked:
            self._monitor_btn.setText("停止监控")
            mode = "full_auto" if self._mode_combo.currentIndex() == 0 else "semi_auto"

            # 收集关键词规则
            keywords = {}
            for row in range(self._rules_table.rowCount()):
                kw = self._rules_table.item(row, 0)
                reply = self._rules_table.item(row, 1)
                if kw and reply:
                    keywords[kw.text()] = reply.text()

            self._engine.add_task(
                name="自动回复监控",
                task_type="auto_reply",
                params={"keywords": keywords, "mode": mode},
            )
            self._reply_log.appendPlainText(f"[自动回复] 监控已启动, 模式: {mode}")
        else:
            self._monitor_btn.setText("开始监控")
            for task in self._engine.get_all_tasks():
                if task.task_type == "auto_reply" and task.state == TaskState.RUNNING:
                    self._engine.cancel_task(task.task_id)
            self._reply_log.appendPlainText("[自动回复] 监控已停止")

    def _add_keyword_rule(self):
        """添加关键词规则"""
        keyword = self._keyword_input.text().strip()
        reply = self._reply_input.text().strip()

        if not keyword or not reply:
            QMessageBox.warning(self, "提示", "请输入关键词和回复内容")
            return

        row = self._rules_table.rowCount()
        self._rules_table.insertRow(row)
        self._rules_table.setItem(row, 0, QTableWidgetItem(keyword))
        self._rules_table.setItem(row, 1, QTableWidgetItem(reply))

        del_btn = QPushButton("删除")
        del_btn.clicked.connect(lambda: self._delete_keyword_rule(row))
        self._rules_table.setCellWidget(row, 2, del_btn)

        self._keyword_input.clear()
        self._reply_input.clear()

    def _delete_keyword_rule(self, row: int):
        """删除关键词规则"""
        if 0 <= row < self._rules_table.rowCount():
            self._rules_table.removeRow(row)

    # ---- 任务列表操作 ----

    def _refresh_tasks(self):
        """刷新任务列表"""
        tasks = self._engine.get_all_tasks()
        self._task_table.setRowCount(len(tasks))

        state_colors = {
            TaskState.PENDING: "#f39c12",
            TaskState.RUNNING: "#3498db",
            TaskState.PAUSED: "#95a5a6",
            TaskState.COMPLETED: "#27ae60",
            TaskState.FAILED: "#e74c3c",
            TaskState.CANCELLED: "#7f8c8d",
        }

        state_names = {
            TaskState.PENDING: "等待中",
            TaskState.RUNNING: "运行中",
            TaskState.PAUSED: "已暂停",
            TaskState.COMPLETED: "已完成",
            TaskState.FAILED: "失败",
            TaskState.CANCELLED: "已取消",
        }

        for row, task in enumerate(tasks):
            self._task_table.setItem(row, 0, QTableWidgetItem(task.task_id))
            self._task_table.setItem(row, 1, QTableWidgetItem(task.name))
            self._task_table.setItem(row, 2, QTableWidgetItem(task.task_type))

            state_item = QTableWidgetItem(state_names.get(task.state, str(task.state)))
            color = state_colors.get(task.state, "#333")
            state_item.setForeground(QColor(color))
            self._task_table.setItem(row, 3, state_item)

            self._task_table.setItem(row, 4, QTableWidgetItem(f"{task.progress:.1f}%"))
            self._task_table.setItem(row, 5, QTableWidgetItem(
                task.created_at.strftime("%H:%M:%S") if task.created_at else "--"
            ))

            if task.state == TaskState.RUNNING:
                cancel_btn = QPushButton("取消")
                cancel_btn.clicked.connect(lambda checked, tid=task.task_id: self._cancel_task(tid))
                self._task_table.setCellWidget(row, 6, cancel_btn)
            else:
                self._task_table.setItem(row, 6, QTableWidgetItem(""))

    def _cancel_task(self, task_id: str):
        """取消任务"""
        self._engine.cancel_task(task_id)
        self._refresh_tasks()

    def _clear_completed_tasks(self):
        """清除已完成任务"""
        count = self._engine._task_scheduler.clear_completed()
        self._refresh_tasks()
        self._status_bar.showMessage(f"已清除 {count} 个完成的任务", 3000)

    # ---- 通用方法 ----

    def _refresh_status(self):
        """定时刷新状态"""
        report = self._engine.get_status_report()

        # 更新WebSocket状态
        if self._ws_client.is_connected:
            self._conn_label.setText("服务器: 已连接")
            self._conn_label.setStyleSheet("color: #07c160;")
        else:
            self._conn_label.setText("服务器: 未连接")
            self._conn_label.setStyleSheet("color: #e74c3c;")

    def _on_engine_status_change(self, task):
        """引擎状态变更回调"""
        self._refresh_tasks()

        # 通过WebSocket上报
        if self._ws_client.is_connected:
            self._ws_client.send_task_status(
                task.task_id, task.state.value, task.progress
            )

    def _handle_server_command(self, data: dict):
        """处理服务器推送的命令"""
        command = data.get("command", "")
        logger.info(f"收到服务器命令: {command}")

    def _show_settings(self):
        """显示设置对话框"""
        QMessageBox.information(self, "设置", "设置功能开发中...")

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, "关于 MyRPA",
            "MyRPA 微信自动化 v1.0.0\n\n"
            "智能微信RPA管理系统\n"
            "支持加好友、群发消息、自动回复等功能\n\n"
            "仅供学习和研究使用"
        )

    def _logout(self):
        """退出登录"""
        reply = QMessageBox.question(
            self, "确认", "确定要退出登录吗？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._auth_manager.clear_token()
            self._engine.shutdown()
            self._ws_client.disconnect()
            self.close()

    def _quit_app(self):
        """退出应用程序"""
        self._engine.shutdown()
        self._ws_client.disconnect()
        if self._tray_icon:
            self._tray_icon.hide()
        QApplication.quit()

    def _show_from_tray(self):
        """从托盘恢复窗口"""
        self.show()
        self.activateWindow()
        self.raise_()

    def _center_window(self):
        """居中显示窗口"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            x = (screen_geo.width() - self.width()) // 2
            y = (screen_geo.height() - self.height()) // 2
            self.move(x, y)

    def closeEvent(self, event):
        """关闭事件 - 最小化到托盘"""
        if self._settings.ui.minimize_to_tray and self._tray_icon:
            event.ignore()
            self.hide()
            self._tray_icon.showMessage(
                "MyRPA", "程序已最小化到系统托盘",
            )
        else:
            self._quit_app()
            event.accept()
