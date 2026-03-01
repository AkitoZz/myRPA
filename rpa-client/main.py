"""
MyRPA 微信自动化客户端 - 程序入口

初始化应用程序、加载配置、启动PyQt5界面。
"""

import os
import sys
import platform


def check_platform():
    """检查运行平台"""
    current_platform = platform.system()
    if current_platform == "Windows":
        return True
    else:
        print(f"当前平台: {current_platform}")
        print("注意: RPA自动化功能仅在Windows平台上完整可用")
        print("当前平台下仅UI功能可用，微信控制功能将被禁用")
        return False


def setup_environment():
    """设置运行环境"""
    # 将项目根目录添加到Python路径
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # 设置环境变量
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    # Windows高DPI支持
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def init_logging():
    """初始化日志系统"""
    from utils.logger import setup_logger
    from config.settings import get_settings

    settings = get_settings()
    setup_logger(
        log_dir=settings.log.log_dir,
        console_level=settings.log.console_level,
        file_level=settings.log.file_level,
        rotation=settings.log.rotation,
        retention=settings.log.retention,
    )


def main():
    """主函数"""
    # 设置环境
    setup_environment()

    # 检查平台
    is_windows = check_platform()

    # 初始化日志
    init_logging()

    from loguru import logger
    logger.info("=" * 50)
    logger.info("MyRPA 微信自动化客户端启动")
    logger.info(f"平台: {platform.system()} {platform.release()}")
    logger.info(f"Python: {platform.python_version()}")
    logger.info(f"RPA功能: {'可用' if is_windows else '不可用 (非Windows平台)'}")
    logger.info("=" * 50)

    # 加载配置
    from config.settings import get_settings
    settings = get_settings()
    logger.info(f"服务器地址: {settings.server.api_url}")

    # 启动PyQt5应用
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt

    # 高DPI缩放
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("MyRPA")
    app.setApplicationDisplayName("MyRPA 微信自动化")
    app.setOrganizationName("MyRPA")

    # 全局样式
    app.setStyleSheet("""
        QWidget {
            font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
            font-size: 13px;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 15px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            color: #333;
        }
        QLineEdit, QPlainTextEdit, QTextEdit {
            border: 1px solid #ddd;
            border-radius: 3px;
            padding: 5px;
        }
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
            border-color: #07c160;
        }
        QPushButton {
            border: 1px solid #ddd;
            border-radius: 3px;
            padding: 5px 15px;
            background: #f5f5f5;
        }
        QPushButton:hover {
            background: #e8e8e8;
        }
        QTableWidget {
            border: 1px solid #ddd;
            gridline-color: #eee;
        }
        QHeaderView::section {
            background-color: #f5f5f5;
            padding: 5px;
            border: 1px solid #ddd;
            font-weight: bold;
        }
        QProgressBar {
            border: 1px solid #ddd;
            border-radius: 3px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #07c160;
            border-radius: 2px;
        }
    """)

    # 显示登录窗口
    from ui.login_window import LoginWindow
    from ui.main_window import MainWindow

    login_window = LoginWindow()
    main_window_ref = [None]

    def on_login_success(token: str, phone: str):
        """登录成功回调"""
        logger.info("登录成功，打开主窗口")
        login_window.hide()

        main_window = MainWindow(
            token=token,
            phone=phone,
            api_client=login_window.get_api_client(),
            auth_manager=login_window.get_auth_manager(),
        )
        main_window.show()
        main_window_ref[0] = main_window

    login_window.login_successful.connect(on_login_success)
    login_window.show()

    # 运行事件循环
    exit_code = app.exec_()

    # 清理
    logger.info("应用程序退出")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
