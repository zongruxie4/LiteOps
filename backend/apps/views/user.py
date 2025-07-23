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
from ..utils.security import SecurityValidator

logger = logging.getLogger('apps')

def generate_id():
    """生成唯一ID"""
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]

@method_decorator(csrf_exempt, name='dispatch')
class UserView(View):
    @method_decorator(jwt_auth_required)
    def get(self, request):
        """获取用户列表"""
        try:
            user_id = request.GET.get('user_id')
            username = request.GET.get('username')
            email = request.GET.get('email')
            status = request.GET.get('status')

            # 构建查询条件
            query = {}

            if user_id:
                query['user_id'] = user_id
            if username:
                query['username__icontains'] = username  # 使用 icontains 进行不区分大小写的模糊查询
            if email:
                query['email__icontains'] = email
            if status:
                query['status'] = status

            # 使用查询条件过滤用户
            users = User.objects.filter(**query)

            user_list = []
            for user in users:
                # 获取用户角色
                user_roles = UserRole.objects.filter(user=user).select_related('role')
                roles = [{"role_id": ur.role.role_id, "name": ur.role.name} for ur in user_roles]

                user_list.append({
                    'user_id': user.user_id,
                    'username': user.username,
                    'name': user.name,
                    'email': user.email,
                    'status': user.status,
                    'roles': roles,
                    'user_type': user.user_type,
                    'login_time': user.login_time.strftime('%Y-%m-%d %H:%M:%S') if user.login_time else None,
                    'create_time': user.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                })

            return JsonResponse({
                'code': 200,
                'message': '获取用户列表成功',
                'data': user_list
            })
        except Exception as e:
            logger.error(f'获取用户列表失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def post(self, request):
        """创建用户"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                username = data.get('username')
                name = data.get('name')
                password = data.get('password')
                email = data.get('email')
                role_ids = data.get('role_ids', [])

                if not all([username, name, password, email]):
                    return JsonResponse({
                        'code': 400,
                        'message': '用户名、姓名、密码和邮箱不能为空'
                    })

                # 检查用户名是否已存在
                if User.objects.filter(username=username).exists():
                    return JsonResponse({
                        'code': 400,
                        'message': '用户名已存在'
                    })

                # 检查邮箱是否已存在
                if User.objects.filter(email=email).exists():
                    return JsonResponse({
                        'code': 400,
                        'message': '邮箱已存在'
                    })

                # 验证密码强度
                is_valid, message = SecurityValidator.validate_password(password)
                if not is_valid:
                    return JsonResponse({
                        'code': 400,
                        'message': message
                    })

                # 密码加密
                password_hash = hashlib.sha256(password.encode()).hexdigest()

                # 创建用户
                user = User.objects.create(
                    user_id=generate_id(),
                    username=username,
                    name=name,
                    password=password_hash,
                    email=email,
                    status=1  # 默认启用
                )

                # 分配角色
                for role_id in role_ids:
                    try:
                        role = Role.objects.get(role_id=role_id)
                        UserRole.objects.create(user=user, role=role)
                    except Role.DoesNotExist:
                        logger.warning(f'角色不存在: {role_id}')

                return JsonResponse({
                    'code': 200,
                    'message': '创建用户成功',
                    'data': {
                        'user_id': user.user_id,
                        'username': user.username
                    }
                })
        except Exception as e:
            logger.error(f'创建用户失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def put(self, request):
        """编辑用户"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                user_id = data.get('user_id')
                name = data.get('name')
                email = data.get('email')
                status = data.get('status')
                password = data.get('password')
                role_ids = data.get('role_ids')

                if not user_id:
                    return JsonResponse({
                        'code': 400,
                        'message': '用户ID不能为空'
                    })

                try:
                    user = User.objects.get(user_id=user_id)
                except User.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '用户不存在'
                    })

                # 更新用户信息
                if name:
                    user.name = name
                if email and email != user.email:
                    # 检查邮箱是否已存在
                    if User.objects.filter(email=email).exclude(user_id=user_id).exists():
                        return JsonResponse({
                            'code': 400,
                            'message': '邮箱已存在'
                        })
                    user.email = email
                if status is not None:
                    if user.status == 0 and status == 1:
                        success, message = SecurityValidator.unlock_user_account(user)
                        if not success:
                            return JsonResponse({
                                'code': 400,
                                'message': message
                            })
                    elif user.status == 1 and status == 0:
                        success, message = SecurityValidator.lock_user_account(user)
                        if not success:
                            return JsonResponse({
                                'code': 400,
                                'message': message
                            })
                    else:
                        user.status = status
                if password:
                    # 验证密码强度
                    is_valid, message = SecurityValidator.validate_password(password)
                    if not is_valid:
                        return JsonResponse({
                            'code': 400,
                            'message': message
                        })
                    
                    # 密码加密
                    password_hash = hashlib.sha256(password.encode()).hexdigest()
                    user.password = password_hash

                user.save()

                # 更新角色
                if role_ids is not None:
                    # 删除旧角色关联
                    UserRole.objects.filter(user=user).delete()

                    # 添加新角色关联
                    for role_id in role_ids:
                        try:
                            role = Role.objects.get(role_id=role_id)
                            UserRole.objects.create(user=user, role=role)
                        except Role.DoesNotExist:
                            logger.warning(f'角色不存在: {role_id}')

                return JsonResponse({
                    'code': 200,
                    'message': '更新用户成功'
                })
        except Exception as e:
            logger.error(f'更新用户失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def delete(self, request):
        """删除用户"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                user_id = data.get('user_id')

                if not user_id:
                    return JsonResponse({
                        'code': 400,
                        'message': '用户ID不能为空'
                    })

                try:
                    user = User.objects.get(user_id=user_id)
                    # 删除关联的角色
                    UserRole.objects.filter(user=user).delete()
                    # 删除用户
                    user.delete()
                    return JsonResponse({
                        'code': 200,
                        'message': '删除用户成功'
                    })
                except User.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '用户不存在'
                    })

        except Exception as e:
            logger.error(f'删除用户失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })


@method_decorator(csrf_exempt, name='dispatch')
class UserProfileView(View):
    @method_decorator(jwt_auth_required)
    def get(self, request):
        """获取当前登录用户的个人信息"""
        try:
            user_id = request.user_id

            try:
                user = User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                return JsonResponse({
                    'code': 404,
                    'message': '用户不存在'
                })

            # 获取用户角色
            user_roles = UserRole.objects.filter(user=user).select_related('role')
            roles = [{
                "role_id": ur.role.role_id,
                "name": ur.role.name,
                "description": ur.role.description
            } for ur in user_roles]

            # 构建用户信息
            user_info = {
                'user_id': user.user_id,
                'username': user.username,
                'name': user.name,
                'email': user.email,
                'status': user.status,
                'roles': roles,
                'user_type': user.user_type,
                'login_time': user.login_time.strftime('%Y-%m-%d %H:%M:%S') if user.login_time else None,
                'create_time': user.create_time.strftime('%Y-%m-%d %H:%M:%S') if user.create_time else None,
                'update_time': user.update_time.strftime('%Y-%m-%d %H:%M:%S') if user.update_time else None,
            }

            return JsonResponse({
                'code': 200,
                'message': '获取用户信息成功',
                'data': user_info
            })

        except Exception as e:
            logger.error(f'获取用户信息失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })