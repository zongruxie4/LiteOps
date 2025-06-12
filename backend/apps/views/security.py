import json
import logging
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from ..models import SecurityConfig, User
from ..utils.auth import jwt_auth_required

logger = logging.getLogger('apps')

@method_decorator(csrf_exempt, name='dispatch')
class SecurityConfigView(View):
    @method_decorator(jwt_auth_required)
    def get(self, request):
        """获取安全配置"""
        try:
            # 获取或创建安全配置
            security_config, created = SecurityConfig.objects.get_or_create(
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

            return JsonResponse({
                'code': 200,
                'message': '获取安全配置成功',
                'data': {
                    'min_password_length': security_config.min_password_length,
                    'password_complexity': security_config.password_complexity,
                    'session_timeout': security_config.session_timeout,
                    'max_login_attempts': security_config.max_login_attempts,
                    'lockout_duration': security_config.lockout_duration,
                    'enable_2fa': security_config.enable_2fa,
                    'update_time': security_config.update_time.strftime('%Y-%m-%d %H:%M:%S') if security_config.update_time else None
                }
            })

        except Exception as e:
            logger.error(f'获取安全配置失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def put(self, request):
        """更新安全配置"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                
                min_password_length = data.get('min_password_length')
                password_complexity = data.get('password_complexity')
                session_timeout = data.get('session_timeout')
                max_login_attempts = data.get('max_login_attempts')
                lockout_duration = data.get('lockout_duration')
                enable_2fa = data.get('enable_2fa')

                # 验证输入数据
                if min_password_length is not None:
                    if not isinstance(min_password_length, int) or min_password_length < 6 or min_password_length > 20:
                        return JsonResponse({
                            'code': 400,
                            'message': '密码最小长度必须在6-20之间'
                        })

                if password_complexity is not None:
                    if not isinstance(password_complexity, list):
                        return JsonResponse({
                            'code': 400,
                            'message': '密码复杂度要求格式错误'
                        })
                    valid_complexity = ['uppercase', 'lowercase', 'number', 'special']
                    for item in password_complexity:
                        if item not in valid_complexity:
                            return JsonResponse({
                                'code': 400,
                                'message': f'无效的密码复杂度要求: {item}'
                            })

                if session_timeout is not None:
                    if not isinstance(session_timeout, int) or session_timeout < 10 or session_timeout > 1440:
                        return JsonResponse({
                            'code': 400,
                            'message': '会话超时时间必须在10-1440分钟之间'
                        })

                if max_login_attempts is not None:
                    if not isinstance(max_login_attempts, int) or max_login_attempts < 3 or max_login_attempts > 10:
                        return JsonResponse({
                            'code': 400,
                            'message': '最大登录尝试次数必须在3-10次之间'
                        })

                if lockout_duration is not None:
                    if not isinstance(lockout_duration, int) or lockout_duration < 5 or lockout_duration > 60:
                        return JsonResponse({
                            'code': 400,
                            'message': '账户锁定时间必须在5-60分钟之间'
                        })

                # 获取或创建安全配置
                security_config, created = SecurityConfig.objects.get_or_create(id=1)

                # 更新配置
                if min_password_length is not None:
                    security_config.min_password_length = min_password_length
                if password_complexity is not None:
                    security_config.password_complexity = password_complexity
                if session_timeout is not None:
                    security_config.session_timeout = session_timeout
                if max_login_attempts is not None:
                    security_config.max_login_attempts = max_login_attempts
                if lockout_duration is not None:
                    security_config.lockout_duration = lockout_duration
                if enable_2fa is not None:
                    security_config.enable_2fa = enable_2fa

                security_config.save()

                # 记录操作日志
                user = User.objects.get(user_id=request.user_id)
                logger.info(f'用户[{user.username}]更新了安全配置')

                return JsonResponse({
                    'code': 200,
                    'message': '安全配置更新成功'
                })

        except Exception as e:
            logger.error(f'更新安全配置失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            }) 