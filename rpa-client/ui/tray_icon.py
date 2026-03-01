"""
系统托盘图标模块

提供系统托盘图标、右键菜单和托盘通知功能。
"""

from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt5.QtCore import pyqtSignal

from loguru import logger


class TrayIcon(QSystemTrayIcon):
    """系统托盘图标"""

    show_window_signal = pyqtSignal()
    exit_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent

        self._create_icon()
        self._create_menu()

        self.activated.connect(self._on_activated)

    def _create_icon(self):
        """创建托盘图标"""
        # 生成简单的程序图标（绿色圆形带字母R）
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绿色圆形背景
        painter.setBrush(QColor("#07c160"))
        painter.setPen(QColor("#07c160"))
        painter.drawEllipse(2, 2, 60, 60)

        # 白色字母
        painter.setPen(QColor("white"))
        font = QFont("Arial", 28, QFont.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), 0x0084, "R")  # AlignCenter

        painter.end()

        icon = QIcon(pixmap)
        self.setIcon(icon)
        self.setToolTip("MyRPA 微信自动化")

    def _create_menu(self):
        """创建右键菜单"""
        menu = QMenu()

        # 显示/隐藏主窗口
        show_action = QAction("显示主窗口", menu)
        show_action.triggered.connect(self._show_window)
        menu.addAction(show_action)

        menu.addSeparator()

        # 状态信息
        self._status_action = QAction("状态: 运行中", menu)
        self._status_action.setEnabled(False)
        menu.addAction(self._status_action)

        self._wechat_action = QAction("微信: 未连接", menu)
        self._wechat_action.setEnabled(False)
        menu.addAction(self._wechat_action)

        menu.addSeparator()

        # 退出
        exit_action = QAction("退出", menu)
        exit_action.triggered.connect(self._exit_app)
        menu.addAction(exit_action)

        self.setContextMenu(menu)

    def _on_activated(self, reason):
        """图标被激活（点击）"""
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_window()
        elif reason == QSystemTrayIcon.Trigger:
            self._show_window()

    def _show_window(self):
        """显示主窗口"""
        self.show_window_signal.emit()
        if self._parent:
            self._parent.show()
            self._parent.activateWindow()
            self._parent.raise_()

    def _exit_app(self):
        """退出应用"""
        self.exit_signal.emit()

    def update_status(self, status: str):
        """更新状态显示"""
        self._status_action.setText(f"状态: {status}")

    def update_wechat_status(self, connected: bool, info: str = ""):
        """更新微信连接状态"""
        if connected:
            self._wechat_action.setText(f"微信: 已连接 {info}")
        else:
            self._wechat_action.setText("微信: 未连接")

    def showMessage(self, title: str, message: str, icon_type=None, duration: int = 3000):
        """显示托盘通知"""
        if icon_type is None:
            icon_type = QSystemTrayIcon.Information
        super().showMessage(title, message, icon_type, duration)
