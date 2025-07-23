import json
import hashlib
import jwt
import uuid
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from ..models import User, UserToken, LoginLog
from ..utils.security import SecurityValidator
from .ldap import LDAPAuthenticator

def generate_token_id():
    """生成token_id"""
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]

def generate_log_id():
    """生成log_id"""
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]

class LoginHandler:
    """登录处理器"""
    
    def __init__(self, username, password, ip_address, user_agent):
        self.username = username
        self.password = password
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.log_id = generate_log_id()

    def authenticate_system_user(self):
        """系统用户认证"""
        try:
            user = User.objects.get(username=self.username)
        except User.DoesNotExist:
            self._log_failed_login(fail_reason='用户不存在')
            return JsonResponse({'code': 404, 'message': '用户不存在'})

        # 检查账户锁定
        is_not_locked, lockout_message = SecurityValidator.check_account_lockout(user, self.ip_address)
        if not is_not_locked:
            self._log_failed_login(user=user, fail_reason=lockout_message)
            return JsonResponse({'code': 423, 'message': lockout_message})

        # 验证密码
        password_hash = hashlib.sha256(self.password.encode()).hexdigest()
        if user.password != password_hash:
            return self._handle_password_error(user)
            
        # 检查用户状态
        if user.status == 0:
            self._log_failed_login(user=user, fail_reason='账号已被锁定')
            return JsonResponse({'code': 423, 'message': '账号已被锁定，请联系管理员解锁'})

        # 登录成功
        SecurityValidator.record_successful_login(user, self.ip_address)
        return self._create_login_response(user)

    def authenticate_ldap_user(self):
        """LDAP用户认证"""
        success, result = LDAPAuthenticator.authenticate(self.username, self.password)
        
        if not success:
            self._log_failed_login(fail_reason=f'LDAP认证失败: {result}')
            return JsonResponse({'code': 401, 'message': result})

        user = result
        if user.status == 0:
            self._log_failed_login(user=user, fail_reason='账号已被锁定')
            return JsonResponse({'code': 423, 'message': '账号已被锁定，请联系管理员解锁'})

        return self._create_login_response(user)

    def _handle_password_error(self, user):
        """处理密码错误"""
        failed_attempts, max_attempts = SecurityValidator.record_failed_login(user, self.ip_address)
        self._log_failed_login(user=user, fail_reason='密码错误')
                
        remaining_attempts = max_attempts - failed_attempts
        if remaining_attempts > 0:
            message = f'密码错误，还可尝试{remaining_attempts}次'
        else:
            config = SecurityValidator.get_security_config()
            message = f'密码错误次数过多，账户已被锁定{config.lockout_duration}分钟'
                
        return JsonResponse({'code': 401, 'message': message})

    def _create_login_response(self, user):
        """创建登录成功响应"""
        config = SecurityValidator.get_security_config()
        
    # 生成token
        token_id = generate_token_id()
        token_payload = {
            'user_id': user.user_id,
            'username': user.username,
        'exp': datetime.utcnow() + timedelta(minutes=config.session_timeout)
        }
        token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm='HS256')
        
    # 更新token记录
        UserToken.objects.update_or_create(
            user=user,
        defaults={'token_id': token_id, 'token': token}
        )

        # 更新登录时间
        user.login_time = datetime.now()
        user.save()
        
        # 记录成功登录日志
        self._log_successful_login(user)
        
        return JsonResponse({
            'code': 200,
            'message': '登录成功',
            'data': {
                'token_id': token_id,
                'token': token,
                'user': {
                    'user_id': user.user_id,
                    'username': user.username,
                    'name': user.name,
                    'email': user.email
                }
            }
        })

    def _log_failed_login(self, user=None, fail_reason=''):
        """记录失败登录日志"""
        LoginLog.objects.create(
        log_id=self.log_id,
        user=user,
        ip_address=self.ip_address,
        user_agent=self.user_agent,
            status='failed',
        fail_reason=fail_reason
    )

    def _log_successful_login(self, user):
        """记录成功登录日志"""
        LoginLog.objects.create(
            log_id=self.log_id,
            user=user,
            ip_address=self.ip_address,
            user_agent=self.user_agent,
            status='success'
            )
            
@csrf_exempt
@require_http_methods(["POST"])
def login(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        auth_type = data.get('auth_type', 'system')
        
        if not username or not password:
            return JsonResponse({'code': 400, 'message': '用户名和密码不能为空'})

        # 获取客户端信息
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # 创建登录处理器
        handler = LoginHandler(username, password, ip_address, user_agent)
        
        # 根据认证类型进行认证
        if auth_type == 'ldap':
            return handler.authenticate_ldap_user()
        else:
            return handler.authenticate_system_user()

    except Exception as e:
        return JsonResponse({'code': 500, 'message': f'服务器错误: {str(e)}'})

@csrf_exempt
@require_http_methods(["POST"])
def logout(request):
    try:
        token = request.headers.get('Authorization')
        if not token:
            return JsonResponse({'code': 400, 'message': '未提供Token'})

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')
            UserToken.objects.filter(user_id=user_id).delete()
            return JsonResponse({'code': 200, 'message': '退出成功'})

        except jwt.ExpiredSignatureError:
            return JsonResponse({'code': 401, 'message': 'Token已过期'})
        except jwt.InvalidTokenError:
            return JsonResponse({'code': 401, 'message': '无效的Token'})

    except Exception as e:
        return JsonResponse({'code': 500, 'message': f'服务器错误: {str(e)}'}) 