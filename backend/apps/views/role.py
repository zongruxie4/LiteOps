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
from ..models import User, Role, UserRole
from ..utils.auth import jwt_auth_required

logger = logging.getLogger('apps')

def generate_id():
    """生成唯一ID"""
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]

@method_decorator(csrf_exempt, name='dispatch')
class RoleView(View):
    @method_decorator(jwt_auth_required)
    def get(self, request):
        """获取角色列表"""
        try:
            role_id = request.GET.get('role_id')
            name = request.GET.get('name')

            # 构建查询条件
            query = {}
            
            if role_id:
                query['role_id'] = role_id
            if name:
                query['name__icontains'] = name

            # 使用查询条件过滤角色
            roles = Role.objects.select_related('creator').filter(**query)

            role_list = []
            for role in roles:
                # 处理permissions字段，确保是对象形式
                permissions = role.permissions
                if isinstance(permissions, str):
                    try:
                        permissions = json.loads(permissions)
                    except json.JSONDecodeError:
                        logger.error(f'角色[{role.name}]的权限数据格式错误')
                        permissions = {}
                    
                role_data = {
                    'role_id': role.role_id,
                    'name': role.name,
                    'description': role.description,
                    'permissions': permissions,  # 返回处理后的权限配置
                    'creator': {
                        'user_id': role.creator.user_id,
                        'username': role.creator.username,
                        'name': role.creator.name
                    } if role.creator else None,
                    'create_time': role.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'update_time': role.update_time.strftime('%Y-%m-%d %H:%M:%S'),
                }
                role_list.append(role_data)

            return JsonResponse({
                'code': 200,
                'message': '获取角色列表成功',
                'data': role_list
            })
        except Exception as e:
            logger.error(f'获取角色列表失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def post(self, request):
        """创建角色"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                name = data.get('name')
                description = data.get('description')
                permissions = data.get('permissions', {})

                if not name:
                    return JsonResponse({
                        'code': 400,
                        'message': '角色名称不能为空'
                    })

                # 检查角色名称是否已存在
                if Role.objects.filter(name=name).exists():
                    return JsonResponse({
                        'code': 400,
                        'message': '角色名称已存在'
                    })

                # 创建角色
                creator = User.objects.get(user_id=request.user_id)
                role = Role.objects.create(
                    role_id=generate_id(),
                    name=name,
                    description=description,
                    permissions=permissions,
                    creator=creator
                )

                return JsonResponse({
                    'code': 200,
                    'message': '创建角色成功',
                    'data': {
                        'role_id': role.role_id,
                        'name': role.name
                    }
                })
        except Exception as e:
            logger.error(f'创建角色失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def put(self, request):
        """编辑角色"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                role_id = data.get('role_id')
                name = data.get('name')
                description = data.get('description')
                permissions = data.get('permissions')

                if not role_id:
                    return JsonResponse({
                        'code': 400,
                        'message': '角色ID不能为空'
                    })

                try:
                    role = Role.objects.get(role_id=role_id)
                except Role.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '角色不存在'
                    })

                # 检查角色名称是否已存在
                if name and name != role.name:
                    if Role.objects.filter(name=name).exists():
                        return JsonResponse({
                            'code': 400,
                            'message': '角色名称已存在'
                        })
                    role.name = name

                if description is not None:
                    role.description = description
                
                # 处理permissions字段
                if permissions is not None:
                    # 确保permissions是对象而不是字符串
                    if isinstance(permissions, str):
                        try:
                            permissions = json.loads(permissions)
                        except json.JSONDecodeError:
                            return JsonResponse({
                                'code': 400,
                                'message': '权限数据格式错误'
                            })
                    role.permissions = permissions

                role.save()

                return JsonResponse({
                    'code': 200,
                    'message': '更新角色成功'
                })
        except Exception as e:
            logger.error(f'更新角色失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def delete(self, request):
        """删除角色"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                role_id = data.get('role_id')

                if not role_id:
                    return JsonResponse({
                        'code': 400,
                        'message': '角色ID不能为空'
                    })

                try:
                    role = Role.objects.get(role_id=role_id)
                    
                    # 检查是否有用户使用该角色
                    if UserRole.objects.filter(role=role).exists():
                        return JsonResponse({
                            'code': 400,
                            'message': '该角色已分配给用户，无法删除'
                        })
                    
                    role.delete()
                    return JsonResponse({
                        'code': 200,
                        'message': '删除角色成功'
                    })
                except Role.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '角色不存在'
                    })

        except Exception as e:
            logger.error(f'删除角色失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

@method_decorator(csrf_exempt, name='dispatch')
class UserPermissionView(View):
    @method_decorator(jwt_auth_required)
    def get(self, request):
        """获取当前用户的权限"""
        try:
            user_id = request.user_id
            try:
                user = User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                return JsonResponse({
                    'code': 404,
                    'message': '用户不存在'
                })
            
            # 记录操作日志
            logger.info(f'用户[{user.username}]获取权限信息')
            
            # 获取用户的所有角色
            user_roles = UserRole.objects.filter(user=user).select_related('role')
            
            # 合并所有角色的权限
            menu_permissions = set()
            function_permissions = {}
            data_permissions = {
                'project_scope': 'all',
                'project_ids': [],
                'environment_scope': 'all',
                'environment_types': []
            }
            
            has_custom_project_scope = False
            has_custom_environment_scope = False
            
            for user_role in user_roles:
                role = user_role.role
                permissions = role.permissions
                
                # 如果permissions是字符串，解析为JSON
                if isinstance(permissions, str):
                    try:
                        permissions = json.loads(permissions)
                    except json.JSONDecodeError:
                        logger.error(f'解析角色[{role.name}]的权限数据失败')
                        permissions = {}
                
                # 合并菜单权限
                if permissions.get('menu') and isinstance(permissions['menu'], list):
                    menu_permissions.update(permissions['menu'])
                
                # 合并功能权限
                if permissions.get('function') and isinstance(permissions['function'], dict):
                    for module, actions in permissions['function'].items():
                        if not isinstance(actions, list):
                            continue
                            
                        if module not in function_permissions:
                            function_permissions[module] = []
                        function_permissions[module].extend(actions)
                        # 确保不重复
                        function_permissions[module] = list(set(function_permissions[module]))
                
                # 合并数据权限
                if permissions.get('data') and isinstance(permissions['data'], dict):
                    data_perms = permissions['data']
                    
                    # 项目权限
                    if data_perms.get('project_scope') == 'custom':
                        has_custom_project_scope = True
                        if data_permissions['project_scope'] == 'all':
                            data_permissions['project_scope'] = 'custom'
                            data_permissions['project_ids'] = data_perms.get('project_ids', [])
                        else:
                            # 合并项目ID列表
                            data_permissions['project_ids'].extend(data_perms.get('project_ids', []))
                            # 确保不重复
                            data_permissions['project_ids'] = list(set(data_permissions['project_ids']))
                    
                    # 环境权限
                    if data_perms.get('environment_scope') == 'custom':
                        has_custom_environment_scope = True
                        if data_permissions['environment_scope'] == 'all':
                            data_permissions['environment_scope'] = 'custom'
                            data_permissions['environment_types'] = data_perms.get('environment_types', [])
                        else:
                            # 合并环境类型列表
                            data_permissions['environment_types'].extend(data_perms.get('environment_types', []))
                            # 确保不重复
                            data_permissions['environment_types'] = list(set(data_permissions['environment_types']))
            
            # 如果没有任何角色有自定义项目/环境范围，保持为'all'
            if not has_custom_project_scope:
                data_permissions['project_scope'] = 'all'
                data_permissions['project_ids'] = []
            
            if not has_custom_environment_scope:
                data_permissions['environment_scope'] = 'all'
                data_permissions['environment_types'] = []
            
            permissions_result = {
                'menu': list(menu_permissions),
                'function': function_permissions,
                'data': data_permissions
            }
            
            return JsonResponse({
                'code': 200,
                'message': '获取用户权限成功',
                'data': permissions_result
            })
        except Exception as e:
            logger.error(f'获取用户权限失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            }) 