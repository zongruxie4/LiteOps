import base64
from cryptography.fernet import Fernet
from django.conf import settings
import hashlib

class CryptoUtils:
    """加密解密工具类"""
    
    @staticmethod
    def _get_key():
        """获取加密密钥"""
        key_material = settings.SECRET_KEY.encode('utf-8')
        digest = hashlib.sha256(key_material).digest()
        key = base64.urlsafe_b64encode(digest)
        return key
    
    @staticmethod
    def encrypt_password(password):
        """加密密码"""
        if not password:
            return password
            
        try:
            key = CryptoUtils._get_key()
            fernet = Fernet(key)
            encrypted = fernet.encrypt(password.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception:
            return password
    
    @staticmethod
    def decrypt_password(encrypted_password):
        """解密密码"""
        if not encrypted_password:
            return encrypted_password
            
        try:
            key = CryptoUtils._get_key()
            fernet = Fernet(key)
            encrypted_data = base64.urlsafe_b64decode(encrypted_password.encode('utf-8'))
            decrypted = fernet.decrypt(encrypted_data)
            return decrypted.decode('utf-8')
        except Exception:
            return encrypted_password 