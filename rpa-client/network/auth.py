"""
认证管理模块

管理认证令牌的存储、加载、刷新，以及设备指纹和授权验证。
"""

import json
import os
import sys
import time
import platform
from typing import Optional, Dict, Any
from pathlib import Path

from loguru import logger

from utils.crypto import encrypt_string, decrypt_string, generate_device_fingerprint


def _get_auth_dir() -> Path:
    """获取认证数据存储目录"""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    auth_dir = base / "MyRPA" / "auth"
    auth_dir.mkdir(parents=True, exist_ok=True)
    return auth_dir


class AuthManager:
    """认证管理器"""

    TOKEN_FILE = "token.enc"
    DEVICE_FILE = "device.json"

    def __init__(self):
        self._auth_dir = _get_auth_dir()
        self._token: Optional[str] = None
        self._token_expiry: float = 0
        self._device_fingerprint: Optional[str] = None
        self._license_info: Optional[Dict[str, Any]] = None

    @property
    def token(self) -> Optional[str]:
        """获取当前令牌"""
        if self._token and time.time() < self._token_expiry:
            return self._token
        # 令牌过期，尝试从文件加载
        loaded = self.load_token()
        return loaded

    @property
    def is_authenticated(self) -> bool:
        """是否已认证"""
        return self._token is not None and time.time() < self._token_expiry

    @property
    def device_fingerprint(self) -> str:
        """获取设备指纹"""
        if self._device_fingerprint is None:
            self._device_fingerprint = self._load_or_generate_fingerprint()
        return self._device_fingerprint

    def save_token(self, token: str, expiry_seconds: int = 86400 * 7) -> bool:
        """
        保存认证令牌到加密文件

        参数:
            token: 令牌字符串
            expiry_seconds: 有效期（秒），默认7天
        返回:
            是否保存成功
        """
        try:
            self._token = token
            self._token_expiry = time.time() + expiry_seconds

            data = {
                "token": token,
                "expiry": self._token_expiry,
                "saved_at": time.time(),
            }

            encrypted = encrypt_string(json.dumps(data))
            token_path = self._auth_dir / self.TOKEN_FILE

            with open(token_path, "w", encoding="utf-8") as f:
                f.write(encrypted)

            logger.debug("令牌已保存")
            return True

        except Exception as e:
            logger.error(f"保存令牌失败: {e}")
            return False

    def load_token(self) -> Optional[str]:
        """
        从加密文件加载令牌

        返回:
            令牌字符串，加载失败或过期返回None
        """
        token_path = self._auth_dir / self.TOKEN_FILE

        if not token_path.exists():
            return None

        try:
            with open(token_path, "r", encoding="utf-8") as f:
                encrypted = f.read()

            decrypted = decrypt_string(encrypted)
            data = json.loads(decrypted)

            token = data.get("token")
            expiry = data.get("expiry", 0)

            if time.time() >= expiry:
                logger.info("令牌已过期")
                self.clear_token()
                return None

            self._token = token
            self._token_expiry = expiry
            logger.debug("令牌已从文件加载")
            return token

        except Exception as e:
            logger.error(f"加载令牌失败: {e}")
            return None

    def clear_token(self) -> None:
        """清除令牌"""
        self._token = None
        self._token_expiry = 0

        token_path = self._auth_dir / self.TOKEN_FILE
        if token_path.exists():
            try:
                os.remove(token_path)
            except Exception:
                pass

        logger.debug("令牌已清除")

    def refresh_token(self, api_client) -> bool:
        """
        刷新令牌

        参数:
            api_client: API客户端实例
        返回:
            是否刷新成功
        """
        if not self._token:
            logger.warning("没有现有令牌，无法刷新")
            return False

        try:
            result = api_client.post("/auth/refresh", {
                "token": self._token,
            })

            new_token = result.get("token")
            if new_token:
                expiry = result.get("expiry_seconds", 86400 * 7)
                self.save_token(new_token, expiry)
                api_client.set_token(new_token)
                logger.info("令牌已刷新")
                return True

            return False

        except Exception as e:
            logger.error(f"刷新令牌失败: {e}")
            return False

    def _load_or_generate_fingerprint(self) -> str:
        """加载或生成设备指纹"""
        device_path = self._auth_dir / self.DEVICE_FILE

        # 尝试从文件加载
        if device_path.exists():
            try:
                with open(device_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                fingerprint = data.get("fingerprint")
                if fingerprint:
                    return fingerprint
            except Exception:
                pass

        # 生成新的指纹
        fingerprint = generate_device_fingerprint()

        # 保存到文件
        try:
            device_info = self.get_device_info()
            device_info["fingerprint"] = fingerprint
            with open(device_path, "w", encoding="utf-8") as f:
                json.dump(device_info, f, ensure_ascii=False, indent=2)
            logger.info("设备指纹已生成并保存")
        except Exception as e:
            logger.error(f"保存设备指纹失败: {e}")

        return fingerprint

    def get_device_info(self) -> Dict[str, str]:
        """获取设备信息"""
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "machine": platform.machine(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
        }

    def validate_license(self, api_client) -> Dict[str, Any]:
        """
        验证授权许可

        参数:
            api_client: API客户端实例
        返回:
            授权信息
        """
        try:
            result = api_client.check_license()
            self._license_info = result
            is_valid = result.get("valid", False)

            if is_valid:
                logger.info("授权验证通过")
            else:
                logger.warning(f"授权验证失败: {result.get('message', '未知原因')}")

            return result

        except Exception as e:
            logger.error(f"授权验证异常: {e}")
            return {"valid": False, "message": str(e)}

    @property
    def license_info(self) -> Optional[Dict[str, Any]]:
        """获取授权信息"""
        return self._license_info

    def register_device(self, api_client) -> bool:
        """
        向服务器注册当前设备

        参数:
            api_client: API客户端实例
        返回:
            是否注册成功
        """
        try:
            fingerprint = self.device_fingerprint
            device_info = self.get_device_info()

            result = api_client.device_register(fingerprint, device_info)
            logger.info("设备注册成功")
            return True

        except Exception as e:
            logger.error(f"设备注册失败: {e}")
            return False
