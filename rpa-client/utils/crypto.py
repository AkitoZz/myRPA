"""
加密工具模块

提供字符串加密/解密、设备指纹生成、密码哈希等功能。
"""

import hashlib
import os
import sys
import uuid
import platform
import base64
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger


# 固定的盐值（用于密钥派生）
_SALT = b"myRPA_2024_salt_value"
_PASSPHRASE = b"myRPA_default_encryption_key_2024"


def _derive_key(passphrase: bytes = _PASSPHRASE) -> bytes:
    """从口令派生加密密钥"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase))
    return key


def encrypt_string(plaintext: str, passphrase: Optional[str] = None) -> str:
    """
    加密字符串

    参数:
        plaintext: 待加密的明文字符串
        passphrase: 可选的加密口令
    返回:
        Base64编码的密文字符串
    """
    try:
        key = _derive_key(passphrase.encode() if passphrase else _PASSPHRASE)
        f = Fernet(key)
        encrypted = f.encrypt(plaintext.encode("utf-8"))
        return base64.urlsafe_b64encode(encrypted).decode("ascii")
    except Exception as e:
        logger.error(f"加密失败: {e}")
        raise


def decrypt_string(ciphertext: str, passphrase: Optional[str] = None) -> str:
    """
    解密字符串

    参数:
        ciphertext: Base64编码的密文
        passphrase: 可选的解密口令
    返回:
        解密后的明文字符串
    """
    try:
        key = _derive_key(passphrase.encode() if passphrase else _PASSPHRASE)
        f = Fernet(key)
        encrypted = base64.urlsafe_b64decode(ciphertext.encode("ascii"))
        decrypted = f.decrypt(encrypted)
        return decrypted.decode("utf-8")
    except Exception as e:
        logger.error(f"解密失败: {e}")
        raise


def generate_device_fingerprint() -> str:
    """
    生成设备指纹

    基于硬件信息生成唯一设备标识符。
    返回:
        设备指纹字符串（SHA256哈希）
    """
    components = []

    # 平台信息
    components.append(platform.system())
    components.append(platform.machine())
    components.append(platform.processor())

    # 主机名
    components.append(platform.node())

    # MAC地址
    mac = uuid.getnode()
    components.append(str(mac))

    if sys.platform == "win32":
        # Windows特有信息
        try:
            import subprocess
            result = subprocess.run(
                ["wmic", "bios", "get", "serialnumber"],
                capture_output=True, text=True, timeout=5
            )
            bios_serial = result.stdout.strip().split("\n")[-1].strip()
            if bios_serial and bios_serial != "SerialNumber":
                components.append(bios_serial)
        except Exception:
            pass

        try:
            import subprocess
            result = subprocess.run(
                ["wmic", "diskdrive", "get", "serialnumber"],
                capture_output=True, text=True, timeout=5
            )
            lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip() and l.strip() != "SerialNumber"]
            if lines:
                components.append(lines[0])
        except Exception:
            pass
    elif sys.platform == "darwin":
        # macOS特有信息
        try:
            import subprocess
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if "IOPlatformSerialNumber" in line:
                    serial = line.split('"')[-2]
                    components.append(serial)
                    break
        except Exception:
            pass

    # 生成哈希
    raw = "|".join(components)
    fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    logger.debug(f"设备指纹已生成: {fingerprint[:16]}...")
    return fingerprint


def hash_password(password: str) -> str:
    """
    密码哈希（用于本地存储）

    参数:
        password: 原始密码
    返回:
        哈希后的密码字符串
    """
    salt = _SALT
    hash_value = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations=100000,
    )
    return base64.b64encode(salt + hash_value).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    """
    验证密码

    参数:
        password: 原始密码
        hashed: 存储的哈希值
    返回:
        密码是否匹配
    """
    try:
        decoded = base64.b64decode(hashed.encode("ascii"))
        salt = decoded[:len(_SALT)]
        stored_hash = decoded[len(_SALT):]
        computed_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations=100000,
        )
        return computed_hash == stored_hash
    except Exception as e:
        logger.error(f"密码验证失败: {e}")
        return False


def generate_token_storage_key() -> str:
    """生成用于存储认证令牌的加密密钥"""
    fingerprint = generate_device_fingerprint()
    return hashlib.sha256(f"token_key_{fingerprint}".encode()).hexdigest()[:32]
