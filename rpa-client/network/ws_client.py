"""
WebSocket客户端模块

与服务器保持长连接，接收推送命令、上报任务状态和心跳。
"""

import json
import queue
import threading
import time
from typing import Optional, Callable, Dict, Any, List

from loguru import logger

try:
    import websockets
    import websockets.sync.client
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logger.warning("websockets库不可用")

from config.settings import get_settings


class WebSocketClient:
    """WebSocket客户端"""

    RECONNECT_DELAYS = [1, 2, 5, 10, 30, 60]

    def __init__(self, url: Optional[str] = None, token: Optional[str] = None):
        """
        初始化WebSocket客户端

        参数:
            url: WebSocket服务器URL
            token: 认证令牌
        """
        settings = get_settings()
        self._url = url or settings.server.ws_url
        self._token = token
        self._heartbeat_interval = settings.server.heartbeat_interval

        self._ws = None
        self._connected = False
        self._running = False
        self._reconnect_attempt = 0

        self._recv_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None

        self._message_handlers: Dict[str, Callable] = {}
        self._on_connect: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None
        self._on_error: Optional[Callable] = None

        # 离线消息缓存
        self._offline_cache: queue.Queue = queue.Queue(maxsize=1000)
        self._lock = threading.Lock()

    def set_token(self, token: str) -> None:
        """设置认证令牌"""
        self._token = token

    def set_url(self, url: str) -> None:
        """设置服务器URL"""
        self._url = url

    def on_connect(self, callback: Callable) -> None:
        """设置连接成功回调"""
        self._on_connect = callback

    def on_disconnect(self, callback: Callable) -> None:
        """设置断开连接回调"""
        self._on_disconnect = callback

    def on_error(self, callback: Callable) -> None:
        """设置错误回调"""
        self._on_error = callback

    def register_handler(self, message_type: str, handler: Callable) -> None:
        """
        注册消息处理器

        参数:
            message_type: 消息类型
            handler: 处理函数 (data: dict) -> None
        """
        self._message_handlers[message_type] = handler
        logger.debug(f"已注册WebSocket消息处理器: {message_type}")

    def connect(self) -> bool:
        """
        连接到WebSocket服务器

        返回:
            是否连接成功
        """
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets库不可用，无法连接")
            return False

        if self._connected:
            logger.warning("已经连接到WebSocket服务器")
            return True

        self._running = True

        # 启动接收线程
        self._recv_thread = threading.Thread(
            target=self._connection_loop,
            name="ws-connection",
            daemon=True,
        )
        self._recv_thread.start()

        # 等待连接建立
        for _ in range(50):  # 最多等5秒
            if self._connected:
                return True
            time.sleep(0.1)

        return self._connected

    def disconnect(self) -> None:
        """断开WebSocket连接"""
        self._running = False

        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

        self._connected = False

        if self._recv_thread:
            self._recv_thread.join(timeout=5)
            self._recv_thread = None

        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
            self._heartbeat_thread = None

        logger.info("WebSocket已断开连接")

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected

    def send(self, data: Dict[str, Any]) -> bool:
        """
        发送消息

        参数:
            data: 消息数据字典
        返回:
            是否发送成功
        """
        if not self._connected or self._ws is None:
            # 加入离线缓存
            try:
                self._offline_cache.put_nowait(data)
                logger.debug("消息已加入离线缓存")
            except queue.Full:
                logger.warning("离线缓存已满，消息被丢弃")
            return False

        try:
            message = json.dumps(data, ensure_ascii=False)
            self._ws.send(message)
            return True
        except Exception as e:
            logger.error(f"发送WebSocket消息失败: {e}")
            self._handle_disconnect()
            return False

    def send_heartbeat(self) -> bool:
        """发送心跳"""
        return self.send({
            "type": "heartbeat",
            "timestamp": int(time.time()),
        })

    def send_task_status(self, task_id: str, status: str, progress: float = 0,
                         data: Optional[Dict] = None) -> bool:
        """
        发送任务状态

        参数:
            task_id: 任务ID
            status: 任务状态
            progress: 进度百分比
            data: 附加数据
        返回:
            是否发送成功
        """
        return self.send({
            "type": "task_status",
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "data": data or {},
            "timestamp": int(time.time()),
        })

    def _connection_loop(self) -> None:
        """连接管理主循环"""
        while self._running:
            try:
                self._do_connect()

                if self._connected:
                    self._reconnect_attempt = 0
                    self._flush_offline_cache()
                    self._start_heartbeat()
                    self._receive_loop()

            except Exception as e:
                logger.error(f"WebSocket连接异常: {e}")

            if self._running:
                self._handle_disconnect()
                delay = self._get_reconnect_delay()
                logger.info(f"将在 {delay} 秒后重新连接...")
                time.sleep(delay)
                self._reconnect_attempt += 1

    def _do_connect(self) -> None:
        """建立WebSocket连接"""
        try:
            # 构造带认证的URL
            url = self._url
            if self._token:
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}token={self._token}"

            logger.info(f"正在连接WebSocket: {self._url}")

            self._ws = websockets.sync.client.connect(
                url,
                close_timeout=5,
                open_timeout=10,
            )

            self._connected = True
            logger.info("WebSocket连接已建立")

            # 发送认证消息
            self.send({
                "type": "auth",
                "token": self._token,
            })

            if self._on_connect:
                try:
                    self._on_connect()
                except Exception as e:
                    logger.error(f"连接回调异常: {e}")

        except Exception as e:
            self._connected = False
            logger.error(f"WebSocket连接失败: {e}")
            if self._on_error:
                try:
                    self._on_error(e)
                except Exception:
                    pass

    def _receive_loop(self) -> None:
        """消息接收循环"""
        while self._running and self._connected:
            try:
                message = self._ws.recv(timeout=5)
                if message:
                    self._handle_message(message)
            except TimeoutError:
                continue
            except Exception as e:
                if self._running:
                    logger.error(f"接收消息异常: {e}")
                    self._connected = False
                break

    def _handle_message(self, raw_message: str) -> None:
        """处理接收到的消息"""
        try:
            data = json.loads(raw_message)
            msg_type = data.get("type", "unknown")

            logger.debug(f"收到WebSocket消息: {msg_type}")

            # 处理心跳响应
            if msg_type == "pong":
                return

            # 调用对应的处理器
            handler = self._message_handlers.get(msg_type)
            if handler:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"消息处理器异常 ({msg_type}): {e}")
            else:
                logger.debug(f"未注册的消息类型: {msg_type}")

        except json.JSONDecodeError:
            logger.warning(f"收到无效JSON消息: {raw_message[:100]}")
        except Exception as e:
            logger.error(f"处理消息异常: {e}")

    def _start_heartbeat(self) -> None:
        """启动心跳"""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return

        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="ws-heartbeat",
            daemon=True,
        )
        self._heartbeat_thread.start()

    def _heartbeat_loop(self) -> None:
        """心跳发送循环"""
        while self._running and self._connected:
            try:
                self.send_heartbeat()
            except Exception as e:
                logger.debug(f"心跳发送失败: {e}")

            # 分段睡眠，以便快速响应停止信号
            for _ in range(self._heartbeat_interval * 2):
                if not self._running or not self._connected:
                    return
                time.sleep(0.5)

    def _flush_offline_cache(self) -> None:
        """刷新离线缓存"""
        sent = 0
        while not self._offline_cache.empty() and self._connected:
            try:
                data = self._offline_cache.get_nowait()
                if self.send(data):
                    sent += 1
            except queue.Empty:
                break
            except Exception:
                break

        if sent > 0:
            logger.info(f"已发送 {sent} 条离线缓存消息")

    def _handle_disconnect(self) -> None:
        """处理断开连接"""
        was_connected = self._connected
        self._connected = False

        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

        if was_connected and self._on_disconnect:
            try:
                self._on_disconnect()
            except Exception as e:
                logger.error(f"断开连接回调异常: {e}")

    def _get_reconnect_delay(self) -> int:
        """获取重连延迟"""
        index = min(self._reconnect_attempt, len(self.RECONNECT_DELAYS) - 1)
        return self.RECONNECT_DELAYS[index]
