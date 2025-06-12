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

def generate_token_id():
    """生成token_id"""
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]

def generate_log_id():
    """生成log_id"""
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]

@csrf_exempt
@require_http_methods(["POST"])
def login(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        # 获取客户端IP和用户代理
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        if not username or not password:
            return JsonResponse({
                'code': 400,
                'message': '用户名和密码不能为空'
            })

        # 密码加密
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        try:
            user = User.objects.get(username=username)
            
            # 记录登录日志
            log_id = generate_log_id()
            
            # 检查账户是否被锁定
            is_not_locked, lockout_message = SecurityValidator.check_account_lockout(user, ip_address)
            if not is_not_locked:
                # 账户被锁定，记录失败登录
                LoginLog.objects.create(
                    log_id=log_id,
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status='failed',
                    fail_reason=lockout_message
                )
                
                return JsonResponse({
                    'code': 423,  # 423 Locked
                    'message': lockout_message
                })
            
            if user.password != password_hash:
                # 密码错误，记录失败尝试
                failed_attempts, max_attempts = SecurityValidator.record_failed_login(user, ip_address)
                
                # 记录失败登录日志
                LoginLog.objects.create(
                    log_id=log_id,
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status='failed',
                    fail_reason='密码错误'
                )
                
                # 提供剩余尝试次数信息
                remaining_attempts = max_attempts - failed_attempts
                if remaining_attempts > 0:
                    message = f'密码错误，还可尝试{remaining_attempts}次'
                else:
                    config = SecurityValidator.get_security_config()
                    message = f'密码错误次数过多，账户已被锁定{config.lockout_duration}分钟'
                
                return JsonResponse({
                    'code': 401,
                    'message': message
                })
            
            if user.status == 0:
                # 账号锁定，记录失败登录
                LoginLog.objects.create(
                    log_id=log_id,
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status='failed',
                    fail_reason='账号已被锁定'
                )
                
                return JsonResponse({
                    'code': 423,  # 423 Locked
                    'message': '账号已被锁定，请联系管理员解锁'
                })

            # 登录成功，重置失败尝试次数
            SecurityValidator.record_successful_login(user, ip_address)

            # 检查会话超时设置
            config = SecurityValidator.get_security_config()
            
            # 生成token_id和JWT token
            token_id = generate_token_id()
            token_payload = {
                'user_id': user.user_id,
                'username': user.username,
                'exp': datetime.utcnow() + timedelta(minutes=config.session_timeout)  # 使用配置的会话超时时间
            }
            token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm='HS256')
            
            # 更新或创建token记录
            UserToken.objects.update_or_create(
                user=user,
                defaults={
                    'token_id': token_id,
                    'token': token
                }
            )

            # 更新登录时间
            user.login_time = datetime.now()
            user.save()
            
            # 记录成功登录日志
            LoginLog.objects.create(
                log_id=log_id,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                status='success'
            )

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

        except User.DoesNotExist:
            # 用户不存在，记录失败登录
            log_id = generate_log_id()
            LoginLog.objects.create(
                log_id=log_id,
                ip_address=ip_address,
                user_agent=user_agent,
                status='failed',
                fail_reason='用户不存在'
            )
            
            return JsonResponse({
                'code': 404,
                'message': '用户不存在'
            })

    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        })

@csrf_exempt
@require_http_methods(["POST"])
def logout(request):
    try:
        token = request.headers.get('Authorization')
        if not token:
            return JsonResponse({
                'code': 400,
                'message': '未提供Token'
            })

        try:
            # 解析token获取user_id
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')
            
            # 删除该用户的token记录
            UserToken.objects.filter(user_id=user_id).delete()

            return JsonResponse({
                'code': 200,
                'message': '退出成功'
            })
        except jwt.ExpiredSignatureError:
            return JsonResponse({
                'code': 401,
                'message': 'Token已过期'
            })
        except jwt.InvalidTokenError:
            return JsonResponse({
                'code': 401,
                'message': '无效的Token'
            })

    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }) 