import jwt
import logging
from functools import wraps
from django.http import JsonResponse
from django.conf import settings
from ..models import UserToken

logger = logging.getLogger('apps')

def jwt_auth_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            logger.info('认证失败: 未提供Token')
            return JsonResponse({
                'code': 401,
                'message': '未提供Token'
            }, status=401)

        try:
            # 验证token是否存在于数据库
            user_token = UserToken.objects.filter(token=token).first()
            if not user_token:
                logger.info('认证失败: Token无效')
                return JsonResponse({
                    'code': 401,
                    'message': 'Token无效'
                }, status=401)

            # 解析token
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            request.user_id = payload.get('user_id')
            
            return view_func(request, *args, **kwargs)

        except jwt.ExpiredSignatureError:
            logger.info('认证失败: Token已过期')
            return JsonResponse({
                'code': 401,
                'message': 'Token已过期'
            }, status=401)
        except jwt.InvalidTokenError:
            logger.info('认证失败: Token格式无效')
            return JsonResponse({
                'code': 401,
                'message': '无效的Token'
            }, status=401)
        except Exception as e:
            logger.error('认证过程发生错误', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': '服务器错误'
            }, status=500)

    return wrapper 