import re
import hashlib
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from ..models import SecurityConfig, LoginAttempt, User

logger = logging.getLogger('apps')

class SecurityValidator:
    """安全验证工具类"""
    
    @staticmethod
    def get_security_config():
        """获取安全配置"""
        try:
            config, created = SecurityConfig.objects.get_or_create(
                id=1,
                defaults={
                    'min_password_length': 8,
                    'password_complexity': ['lowercase', 'number'],
                    'session_timeout': 120,
                    'max_login_attempts': 5,
                    'lockout_duration': 30,
                    'enable_2fa': False
                }
            )
            return config
        except Exception as e:
            logger.error(f'获取安全配置失败: {str(e)}')
            # 返回默认配置
            return type('SecurityConfig', (), {
                'min_password_length': 8,
                'password_complexity': ['lowercase', 'number'],
                'session_timeout': 120,
                'max_login_attempts': 5,
                'lockout_duration': 30,
                'enable_2fa': False
            })()

    @staticmethod
    def validate_password(password):
        """验证密码是否符合安全策略"""
        config = SecurityValidator.get_security_config()
        
        # 检查密码长度
        if len(password) < config.min_password_length:
            return False, f'密码长度不能少于{config.min_password_length}位'
        
        # 检查密码复杂度
        complexity_checks = {
            'uppercase': (r'[A-Z]', '大写字母'),
            'lowercase': (r'[a-z]', '小写字母'),
            'number': (r'[0-9]', '数字'),
            'special': (r'[!@#$%^&*(),.?":{}|<>]', '特殊字符')
        }
        
        missing_requirements = []
        for requirement in config.password_complexity:
            if requirement in complexity_checks:
                pattern, description = complexity_checks[requirement]
                if not re.search(pattern, password):
                    missing_requirements.append(description)
        
        if missing_requirements:
            return False, f'密码必须包含: {", ".join(missing_requirements)}'
        
        return True, '密码验证通过'

    @staticmethod
    def check_account_lockout(user, ip_address):
        """检查账户是否被锁定"""
        try:
            # 首先检查用户表中的status字段
            if user.status == 0:
                return False, '账户已被锁定，请联系管理员解锁'
            
            config = SecurityValidator.get_security_config()
            
            # 获取登录尝试记录
            try:
                attempt = LoginAttempt.objects.get(user=user, ip_address=ip_address)
            except LoginAttempt.DoesNotExist:
                return True, '账户未被锁定'
            
            # 如果账户被锁定，检查是否已过期
            if attempt.locked_until and attempt.locked_until > timezone.now():
                remaining_time = attempt.locked_until - timezone.now()
                minutes = int(remaining_time.total_seconds() / 60)
                return False, f'账户因登录失败次数过多被临时锁定，请在{minutes}分钟后重试'
            
            # 如果临时锁定已过期，重置失败次数并解锁
            if attempt.locked_until and attempt.locked_until <= timezone.now():
                attempt.failed_attempts = 0
                attempt.locked_until = None
                attempt.save()
                
                # 如果用户被系统锁定（status=0），检查是否需要自动解锁
                if user.status == 0:
                    # 暂时保持锁定状态，需要管理员手动解锁
                    return False, '账户已被锁定，请联系管理员解锁'
            
            return True, '账户未被锁定'
            
        except Exception as e:
            logger.error(f'检查账户锁定状态失败: {str(e)}')
            return True, '锁定检查跳过'

    @staticmethod
    def record_failed_login(user, ip_address):
        """记录登录失败"""
        try:
            config = SecurityValidator.get_security_config()
            
            # 获取或创建登录尝试记录
            attempt, created = LoginAttempt.objects.get_or_create(
                user=user,
                ip_address=ip_address,
                defaults={'failed_attempts': 0}
            )
            
            # 增加失败次数
            attempt.failed_attempts += 1
            attempt.last_attempt_time = timezone.now()
            
            # 如果达到最大失败次数，锁定账户
            if attempt.failed_attempts >= config.max_login_attempts:
                attempt.locked_until = timezone.now() + timedelta(minutes=config.lockout_duration)
                
                # 同时将用户状态设置为锁定
                user.status = 0
                user.save()
                
                logger.warning(f'用户[{user.username}]账户因多次登录失败被锁定，IP: {ip_address}')
            
            attempt.save()
            
            return attempt.failed_attempts, config.max_login_attempts
            
        except Exception as e:
            logger.error(f'记录登录失败失败: {str(e)}')
            return 0, 5

    @staticmethod
    def record_successful_login(user, ip_address):
        """记录登录成功，重置失败次数"""
        try:
            # 清除登录失败记录
            LoginAttempt.objects.filter(
                user=user,
                ip_address=ip_address
            ).delete()
            
        except Exception as e:
            logger.error(f'重置登录失败记录失败: {str(e)}')

    @staticmethod
    def unlock_user_account(user):
        """解锁用户账户（管理员操作）"""
        try:
            # 清除所有登录尝试记录
            LoginAttempt.objects.filter(user=user).delete()
            
            # 解锁用户状态
            if user.status == 0:
                user.status = 1
                user.save()
                logger.info(f'管理员解锁了用户[{user.username}]的账户')
                return True, '账户解锁成功'
            
            return True, '账户状态正常'
            
        except Exception as e:
            logger.error(f'解锁用户账户失败: {str(e)}')
            return False, '解锁失败'

    @staticmethod
    def lock_user_account(user):
        """锁定用户账户（管理员操作）"""
        try:
            # 锁定用户状态
            if user.status == 1:
                user.status = 0
                user.save()
                logger.info(f'管理员锁定了用户[{user.username}]的账户')
                return True, '账户锁定成功'
            
            return True, '账户已处于锁定状态'
            
        except Exception as e:
            logger.error(f'锁定用户账户失败: {str(e)}')
            return False, '锁定失败'

    @staticmethod
    def is_session_expired(login_time):
        """检查会话是否过期"""
        try:
            config = SecurityValidator.get_security_config()
            
            if not login_time:
                return True
            
            # 计算会话过期时间
            session_expire_time = login_time + timedelta(minutes=config.session_timeout)
            
            return timezone.now() > session_expire_time
            
        except Exception as e:
            logger.error(f'检查会话过期失败: {str(e)}')
            return False

def validate_password_strength(password):
    """独立的密码强度验证函数，供其他模块使用"""
    return SecurityValidator.validate_password(password) 