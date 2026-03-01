"""
REST API客户端模块

封装与后端服务器的HTTP API通信，包含认证、设备注册、任务管理等接口。
"""

import time
from typing import Optional, Dict, Any, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from loguru import logger

from config.settings import get_settings


class APIError(Exception):
    """API错误"""
    def __init__(self, message: str, status_code: int = 0, response_data: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class APIClient:
    """REST API客户端"""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        """
        初始化API客户端

        参数:
            base_url: API基础URL
            token: 认证令牌
        """
        settings = get_settings()
        self._base_url = (base_url or settings.server.api_url).rstrip("/")
        self._token = token
        self._timeout = settings.server.request_timeout
        self._max_retries = settings.server.max_retries

        # 配置请求会话
        self._session = requests.Session()
        retry_strategy = Retry(
            total=self._max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def set_token(self, token: str) -> None:
        """设置认证令牌"""
        self._token = token

    def set_base_url(self, url: str) -> None:
        """设置API基础URL"""
        self._base_url = url.rstrip("/")

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "MyRPA-Client/1.0",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        发送HTTP请求

        参数:
            method: HTTP方法
            endpoint: 端点路径
            data: 请求体数据
            params: 查询参数
            retry_count: 当前重试次数
        返回:
            响应数据
        """
        url = f"{self._base_url}/{endpoint.lstrip('/')}"

        try:
            response = self._session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=self._get_headers(),
                timeout=self._timeout,
            )

            # 处理HTTP错误
            if response.status_code == 401:
                raise APIError("认证失败，请重新登录", 401)
            elif response.status_code == 403:
                raise APIError("权限不足", 403)
            elif response.status_code == 404:
                raise APIError(f"接口不存在: {endpoint}", 404)
            elif response.status_code >= 500:
                raise APIError(f"服务器错误: {response.status_code}", response.status_code)

            response.raise_for_status()

            # 解析响应
            if response.content:
                result = response.json()
            else:
                result = {"status": "ok"}

            return result

        except requests.exceptions.ConnectionError as e:
            logger.error(f"连接服务器失败: {url}")
            if retry_count < self._max_retries:
                wait = 2 ** retry_count
                logger.info(f"将在 {wait} 秒后重试 ({retry_count + 1}/{self._max_retries})")
                time.sleep(wait)
                return self._request(method, endpoint, data, params, retry_count + 1)
            raise APIError(f"无法连接服务器: {e}")

        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {url}")
            if retry_count < self._max_retries:
                wait = 2 ** retry_count
                time.sleep(wait)
                return self._request(method, endpoint, data, params, retry_count + 1)
            raise APIError("请求超时")

        except APIError:
            raise

        except requests.exceptions.RequestException as e:
            raise APIError(f"请求失败: {e}")

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET请求"""
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """POST请求"""
        return self._request("POST", endpoint, data=data)

    def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """PUT请求"""
        return self._request("PUT", endpoint, data=data)

    def delete(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """DELETE请求"""
        return self._request("DELETE", endpoint, params=params)

    # ---- 认证接口 ----

    def login(self, phone: str, password: str) -> Dict[str, Any]:
        """
        用户登录

        参数:
            phone: 手机号
            password: 密码
        返回:
            登录结果（含token）
        """
        result = self.post("/auth/login", {
            "phone": phone,
            "password": password,
        })
        if "token" in result:
            self._token = result["token"]
        logger.info(f"登录成功: {phone}")
        return result

    def register(self, phone: str, password: str) -> Dict[str, Any]:
        """
        用户注册

        参数:
            phone: 手机号
            password: 密码
        返回:
            注册结果
        """
        result = self.post("/auth/register", {
            "phone": phone,
            "password": password,
        })
        logger.info(f"注册成功: {phone}")
        return result

    def device_register(self, fingerprint: str, device_info: Dict[str, str]) -> Dict[str, Any]:
        """
        设备注册

        参数:
            fingerprint: 设备指纹
            device_info: 设备信息
        返回:
            注册结果
        """
        return self.post("/device/register", {
            "fingerprint": fingerprint,
            "device_info": device_info,
        })

    def heartbeat(self) -> Dict[str, Any]:
        """发送心跳"""
        return self.post("/heartbeat", {
            "timestamp": int(time.time()),
        })

    # ---- 任务接口 ----

    def get_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取任务列表"""
        params = {}
        if status:
            params["status"] = status
        result = self.get("/tasks", params=params)
        return result.get("tasks", [])

    def get_task(self, task_id: str) -> Dict[str, Any]:
        """获取单个任务详情"""
        return self.get(f"/tasks/{task_id}")

    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建任务"""
        return self.post("/tasks", task_data)

    def update_task(self, task_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新任务"""
        return self.put(f"/tasks/{task_id}", task_data)

    def delete_task(self, task_id: str) -> Dict[str, Any]:
        """删除任务"""
        return self.delete(f"/tasks/{task_id}")

    def report_task_status(self, task_id: str, status: str, progress: float = 0,
                           result: Optional[Dict] = None) -> Dict[str, Any]:
        """上报任务状态"""
        return self.post(f"/tasks/{task_id}/status", {
            "status": status,
            "progress": progress,
            "result": result,
        })

    # ---- 授权接口 ----

    def activate_license(self, license_key: str) -> Dict[str, Any]:
        """
        激活授权

        参数:
            license_key: 授权码
        返回:
            激活结果
        """
        return self.post("/license/activate", {
            "license_key": license_key,
        })

    def check_license(self) -> Dict[str, Any]:
        """检查授权状态"""
        return self.get("/license/status")

    # ---- 配置接口 ----

    def get_remote_config(self) -> Dict[str, Any]:
        """获取远程配置"""
        return self.get("/config")

    def upload_log(self, log_data: str) -> Dict[str, Any]:
        """上传日志"""
        return self.post("/logs", {"content": log_data})

    def close(self) -> None:
        """关闭客户端"""
        self._session.close()
