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
from ..models import Project, User
from ..utils.auth import jwt_auth_required
from ..utils.permissions import get_user_permissions

logger = logging.getLogger('apps')

def generate_id():
    """生成唯一ID"""
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]

@method_decorator(csrf_exempt, name='dispatch')
class ProjectView(View):
    @method_decorator(jwt_auth_required)
    def get(self, request):
        """获取项目列表"""
        try:
            # 获取当前用户的权限信息
            user_permissions = get_user_permissions(request.user_id)
            data_permissions = user_permissions.get('data', {})
            
            # 检查用户是否有项目查看权限
            function_permissions = user_permissions.get('function', {})
            project_permissions = function_permissions.get('project', [])
            
            if 'view' not in project_permissions:
                logger.warning(f'用户[{request.user_id}]没有项目查看权限')
                return JsonResponse({
                    'code': 403,
                    'message': '没有权限查看项目'
                }, status=403)
            
            project_id = request.GET.get('project_id')
            name = request.GET.get('name')
            category = request.GET.get('category')

            # 构建查询条件
            query = Q()
            
            if project_id:
                query &= Q(project_id=project_id)
            if name:
                query &= Q(name__icontains=name)  # 使用 icontains 进行不区分大小写的模糊查询
            if category:
                query &= Q(category=category)

            # 应用项目权限过滤
            project_scope = data_permissions.get('project_scope', 'all')
            if project_scope == 'custom':
                permitted_project_ids = data_permissions.get('project_ids', [])
                if not permitted_project_ids:
                    # 如果设置了自定义项目权限但列表为空，意味着没有权限查看任何项目
                    logger.info(f'用户[{request.user_id}]没有权限查看任何项目')
                    return JsonResponse({
                        'code': 200,
                        'message': '获取项目列表成功',
                        'data': []
                    })
                
                # 限制只能查看有权限的项目
                query &= Q(project_id__in=permitted_project_ids)

            # 使用查询条件过滤项目
            projects = Project.objects.select_related('creator').filter(query)

            project_list = []
            for project in projects:
                project_list.append({
                    'project_id': project.project_id,
                    'name': project.name,
                    'description': project.description,
                    'category': project.category,
                    'repository': project.repository,
                    'creator': {
                        'user_id': project.creator.user_id,
                        'username': project.creator.username,
                        'name': project.creator.name
                    },
                    'create_time': project.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'update_time': project.update_time.strftime('%Y-%m-%d %H:%M:%S')
                })

            return JsonResponse({
                'code': 200,
                'message': '获取项目列表成功',
                'data': project_list
            })
        except Exception as e:
            logger.error(f'获取项目列表失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def post(self, request):
        """创建项目"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                name = data.get('name')
                description = data.get('description')
                category = data.get('category')
                repository = data.get('repository')

                if not name:
                    return JsonResponse({
                        'code': 400,
                        'message': '项目名称不能为空'
                    })

                # 检查项目名称是否已存在
                if Project.objects.filter(name=name).exists():
                    return JsonResponse({
                        'code': 400,
                        'message': '项目名称已存在'
                    })

                # 创建项目
                creator = User.objects.get(user_id=request.user_id)
                project = Project.objects.create(
                    project_id=generate_id(),
                    name=name,
                    description=description,
                    category=category,
                    repository=repository,
                    creator=creator
                )

                return JsonResponse({
                    'code': 200,
                    'message': '创建项目成功',
                    'data': {
                        'project_id': project.project_id,
                        'name': project.name
                    }
                })
        except Exception as e:
            logger.error(f'创建项目失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def put(self, request):
        """编辑项目"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                project_id = data.get('project_id')
                name = data.get('name')
                description = data.get('description')
                category = data.get('category')
                repository = data.get('repository')

                if not project_id:
                    return JsonResponse({
                        'code': 400,
                        'message': '项目ID不能为空'
                    })

                try:
                    project = Project.objects.get(project_id=project_id)
                except Project.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '项目不存在'
                    })

                # 检查项目名称是否已存在
                if name and name != project.name:
                    if Project.objects.filter(name=name).exists():
                        return JsonResponse({
                            'code': 400,
                            'message': '项目名称已存在'
                        })
                    project.name = name

                if description is not None:
                    project.description = description
                if category:
                    project.category = category
                if repository:
                    project.repository = repository

                project.save()

                return JsonResponse({
                    'code': 200,
                    'message': '更新项目成功'
                })
        except Exception as e:
            logger.error(f'更新项目失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def delete(self, request):
        """删除项目"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                project_id = data.get('project_id')

                if not project_id:
                    return JsonResponse({
                        'code': 400,
                        'message': '项目ID不能为空'
                    })

                try:
                    project = Project.objects.get(project_id=project_id)
                    project.delete()
                    return JsonResponse({
                        'code': 200,
                        'message': '删除项目成功'
                    })
                except Project.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '项目不存在'
                    })

        except Exception as e:
            logger.error(f'删除项目失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })


@method_decorator(csrf_exempt, name='dispatch')
class ProjectServiceView(View):
    @method_decorator(jwt_auth_required)
    def post(self, request):
        """创建项目服务"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                project_id = data.get('project_id')
                name = data.get('name')
                description = data.get('description')
                category = data.get('category')
                repository = data.get('repository')

                if not all([project_id, name, category, repository]):
                    return JsonResponse({
                        'code': 400,
                        'message': '项目ID、服务名称、类别和仓库地址不能为空'
                    })

                try:
                    project = Project.objects.get(project_id=project_id)
                except Project.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '项目不存在'
                    })

                # 检查服务名称在项目下是否已存在
                if ProjectService.objects.filter(project=project, name=name).exists():
                    return JsonResponse({
                        'code': 400,
                        'message': '该项目下已存在同名服务'
                    })

                creator = User.objects.get(user_id=request.user_id)
                service = ProjectService.objects.create(
                    service_id=generate_id(),
                    project=project,
                    name=name,
                    description=description,
                    category=category,
                    repository=repository,
                    creator=creator
                )

                return JsonResponse({
                    'code': 200,
                    'message': '创建服务成功',
                    'data': {
                        'service_id': service.service_id,
                        'name': service.name
                    }
                })
        except Exception as e:
            logger.error(f'创建服务失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def put(self, request):
        """更新项目服务"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                service_id = data.get('service_id')
                name = data.get('name')
                description = data.get('description')
                category = data.get('category')
                repository = data.get('repository')

                if not service_id:
                    return JsonResponse({
                        'code': 400,
                        'message': '服务ID不能为空'
                    })

                try:
                    service = ProjectService.objects.get(service_id=service_id)
                except ProjectService.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '服务不存在'
                    })

                # 检查服务名称是否已存在
                if name and name != service.name:
                    if ProjectService.objects.filter(project=service.project, name=name).exists():
                        return JsonResponse({
                            'code': 400,
                            'message': '该项目下已存在同名服务'
                        })
                    service.name = name

                if description is not None:
                    service.description = description
                if category:
                    service.category = category
                if repository:
                    service.repository = repository

                service.save()

                return JsonResponse({
                    'code': 200,
                    'message': '更新服务成功'
                })
        except Exception as e:
            logger.error(f'更新服务失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def delete(self, request):
        """删除项目服务"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                service_id = data.get('service_id')

                if not service_id:
                    return JsonResponse({
                        'code': 400,
                        'message': '服务ID不能为空'
                    })

                try:
                    service = ProjectService.objects.get(service_id=service_id)
                    service.delete()
                    return JsonResponse({
                        'code': 200,
                        'message': '删除服务成功'
                    })
                except ProjectService.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '服务不存在'
                    })

        except Exception as e:
            logger.error(f'删除服务失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            }) 