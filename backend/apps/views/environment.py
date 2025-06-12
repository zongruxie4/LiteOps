import json
import uuid
import hashlib
import logging
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Q
from ..models import Environment, User
from ..utils.auth import jwt_auth_required
from ..utils.permissions import get_user_permissions

logger = logging.getLogger('apps')

def generate_id():
    """生成唯一ID"""
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]

@method_decorator(csrf_exempt, name='dispatch')
class EnvironmentTypeView(View):
    @method_decorator(jwt_auth_required)
    def get(self, request):
        """获取环境类型列表"""
        try:
            # 获取当前用户的权限信息
            user_permissions = get_user_permissions(request.user_id)
            data_permissions = user_permissions.get('data', {})
            
            # 检查用户是否有环境查看权限
            function_permissions = user_permissions.get('function', {})
            environment_permissions = function_permissions.get('environment', [])
            
            if 'view' not in environment_permissions:
                logger.warning(f'用户[{request.user_id}]没有环境查看权限')
                return JsonResponse({
                    'code': 403,
                    'message': '没有权限查看环境'
                }, status=403)
            
            # 获取所有环境
            query = Q()
            
            # 应用环境权限过滤
            environment_scope = data_permissions.get('environment_scope', 'all')
            if environment_scope == 'custom':
                permitted_environment_types = data_permissions.get('environment_types', [])
                if not permitted_environment_types:
                    # 如果设置了自定义环境权限但列表为空，意味着没有权限查看任何环境
                    logger.info(f'用户[{request.user_id}]没有权限查看任何环境')
                    return JsonResponse({
                        'code': 200,
                        'message': '获取环境列表成功',
                        'data': []
                    })
                
                # 限制只能查看有权限的环境类型
                query &= Q(type__in=permitted_environment_types)
            
            environments = Environment.objects.filter(query).order_by('name')
            
            # 格式化结果
            env_list = []
            for env in environments:
                if env.type:
                    env_list.append({
                        'environment_id': env.environment_id,
                        'type': env.type,
                        'name': env.name
                    })
            
            return JsonResponse({
                'code': 200,
                'message': '获取环境列表成功',
                'data': env_list
            })
        except Exception as e:
            logger.error(f'获取环境列表失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

@method_decorator(csrf_exempt, name='dispatch')
class EnvironmentView(View):
    @method_decorator(jwt_auth_required)
    def get(self, request):
        """获取环境列表"""
        try:
            # 获取当前用户的权限信息
            user_permissions = get_user_permissions(request.user_id)
            data_permissions = user_permissions.get('data', {})
            
            # 检查用户是否有环境查看权限
            function_permissions = user_permissions.get('function', {})
            environment_permissions = function_permissions.get('environment', [])
            
            if 'view' not in environment_permissions:
                logger.warning(f'用户[{request.user_id}]没有环境查看权限')
                return JsonResponse({
                    'code': 403,
                    'message': '没有权限查看环境'
                }, status=403)
            
            environment_id = request.GET.get('environment_id')
            name = request.GET.get('name')
            type = request.GET.get('type')
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))

            # 构建查询条件
            query = Q()
            if environment_id:
                query &= Q(environment_id=environment_id)
            if name:
                query &= Q(name__icontains=name)
            if type:
                query &= Q(type=type)

            # 应用环境权限过滤
            environment_scope = data_permissions.get('environment_scope', 'all')
            if environment_scope == 'custom':
                permitted_environment_types = data_permissions.get('environment_types', [])
                if not permitted_environment_types:
                    logger.info(f'用户[{request.user_id}]没有权限查看任何环境')
                    return JsonResponse({
                        'code': 200,
                        'message': '获取环境列表成功',
                        'data': [],
                        'total': 0,
                        'page': page,
                        'page_size': page_size
                    })
                
                # 如果指定了环境类型，检查是否有权限
                if type and type not in permitted_environment_types:
                    logger.warning(f'用户[{request.user_id}]尝试查看无权限的环境类型[{type}]')
                    return JsonResponse({
                        'code': 403,
                        'message': '没有权限查看该类型的环境'
                    }, status=403)
                
                if environment_id:
                    try:
                        env = Environment.objects.get(environment_id=environment_id)
                        if env.type not in permitted_environment_types:
                            logger.warning(f'用户[{request.user_id}]尝试查看无权限的环境[{environment_id}]')
                            return JsonResponse({
                                'code': 403,
                                'message': '没有权限查看该环境'
                            }, status=403)
                    except Environment.DoesNotExist:
                        return JsonResponse({
                            'code': 404,
                            'message': '环境不存在'
                        }, status=404)
                
                # 限制只能查看有权限的环境类型
                query &= Q(type__in=permitted_environment_types)

            # 获取环境列表
            environments = Environment.objects.filter(query).select_related('creator')
            
            # 计算总数
            total = environments.count()
            
            # 分页
            start = (page - 1) * page_size
            end = start + page_size
            environments = environments[start:end]
            
            environment_list = []
            
            for env in environments:
                environment_list.append({
                    'environment_id': env.environment_id,
                    'name': env.name,
                    'type': env.type,
                    'description': env.description,
                    'creator': {
                        'user_id': env.creator.user_id,
                        'username': env.creator.username,
                        'name': env.creator.name
                    } if env.creator else None,
                    'create_time': env.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'update_time': env.update_time.strftime('%Y-%m-%d %H:%M:%S')
                })

            return JsonResponse({
                'code': 200,
                'message': '获取环境列表成功',
                'data': environment_list,
                'total': total,
                'page': page,
                'page_size': page_size
            })
        except Exception as e:
            logger.error(f'获取环境列表失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def post(self, request):
        """创建环境"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                name = data.get('name')
                type = data.get('type')
                description = data.get('description')

                if not all([name, type]):
                    return JsonResponse({
                        'code': 400,
                        'message': '环境名称和类型不能为空'
                    })

                # 检查环境名称是否已存在
                if Environment.objects.filter(name=name).exists():
                    return JsonResponse({
                        'code': 400,
                        'message': '环境名称已存在'
                    })

                # 创建环境
                creator = User.objects.get(user_id=request.user_id)
                environment = Environment.objects.create(
                    environment_id=generate_id(),
                    name=name,
                    type=type,
                    description=description,
                    creator=creator
                )

                return JsonResponse({
                    'code': 200,
                    'message': '创建环境成功',
                    'data': {
                        'environment_id': environment.environment_id,
                        'name': environment.name
                    }
                })
        except Exception as e:
            logger.error(f'创建环境失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def put(self, request):
        """编辑环境"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                environment_id = data.get('environment_id')
                name = data.get('name')
                type = data.get('type')
                description = data.get('description')

                if not environment_id:
                    return JsonResponse({
                        'code': 400,
                        'message': '环境ID不能为空'
                    })

                try:
                    environment = Environment.objects.get(environment_id=environment_id)
                except Environment.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '环境不存在'
                    })

                # 检查名称是否已存在（排除当前环境）
                if name and name != environment.name:
                    if Environment.objects.filter(name=name).exists():
                        return JsonResponse({
                            'code': 400,
                            'message': '环境名称已存在'
                        })
                    environment.name = name

                if type:
                    environment.type = type
                if description is not None:
                    environment.description = description

                environment.save()

                return JsonResponse({
                    'code': 200,
                    'message': '更新环境成功'
                })
        except Exception as e:
            logger.error(f'更新环境失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def delete(self, request):
        """删除环境"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                environment_id = data.get('environment_id')

                if not environment_id:
                    return JsonResponse({
                        'code': 400,
                        'message': '环境ID不能为空'
                    })

                try:
                    environment = Environment.objects.get(environment_id=environment_id)
                    environment.delete()
                    return JsonResponse({
                        'code': 200,
                        'message': '删除环境成功'
                    })
                except Environment.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '环境不存在'
                    })

        except Exception as e:
            logger.error(f'删除环境失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            }) 