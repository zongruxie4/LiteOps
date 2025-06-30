import json
import uuid
import hashlib
import logging
import threading
import time
from datetime import datetime

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Q, F
from ..models import BuildTask, BuildHistory, Project, Environment, GitlabTokenCredential, User, NotificationRobot
from ..utils.auth import jwt_auth_required
from ..utils.builder import Builder
from ..utils.permissions import get_user_permissions

logger = logging.getLogger('apps')

def generate_id():
    """生成唯一ID"""
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]

def execute_build(task, build_number, commit_id, history):
    """执行构建任务"""
    try:
        builder = Builder(task, build_number, commit_id, history)
        builder.execute()
    finally:
        # 无论构建成功、失败或异常，都将构建状态重置为空闲
        from django.db import transaction
        with transaction.atomic():
            # 重新获取任务对象，确保获取最新状态
            from ..models import BuildTask
            BuildTask.objects.filter(task_id=task.task_id).update(building_status='idle')
            logger.info(f"任务 [{task.task_id}] 构建状态已重置为空闲")

@method_decorator(csrf_exempt, name='dispatch')
class BuildTaskView(View):
    @method_decorator(jwt_auth_required)
    def get(self, request, task_id=None):
        """获取构建任务列表或单个任务详情"""
        try:
            # 获取当前用户的权限信息
            user_permissions = get_user_permissions(request.user_id)
            data_permissions = user_permissions.get('data', {})

            # 检查用户是否有构建任务查看权限
            function_permissions = user_permissions.get('function', {})
            build_permissions = function_permissions.get('build_task', [])

            if 'view' not in build_permissions:
                logger.warning(f'用户[{request.user_id}]没有构建任务查看权限')
                return JsonResponse({
                    'code': 403,
                    'message': '没有权限查看构建任务'
                }, status=403)

            # 如果请求参数中包含get_robots=true，则返回通知机器人列表
            if request.GET.get('get_robots') == 'true':
                robots = NotificationRobot.objects.all()
                robot_list = []
                for robot in robots:
                    robot_list.append({
                        'robot_id': robot.robot_id,
                        'type': robot.type,
                        'name': robot.name,
                    })
                return JsonResponse({
                    'code': 200,
                    'message': '获取通知机器人列表成功',
                    'data': robot_list
                })

            # 如果提供了task_id，则返回单个任务详情
            if task_id:
                try:
                    task = BuildTask.objects.select_related(
                        'project',
                        'environment',
                        'git_token',
                        'creator'
                    ).get(task_id=task_id)

                    # 检查是否有权限查看该任务（项目权限和环境权限）
                    # 项目权限检查
                    project_scope = data_permissions.get('project_scope', 'all')
                    if project_scope == 'custom':
                        permitted_project_ids = data_permissions.get('project_ids', [])
                        if task.project and task.project.project_id not in permitted_project_ids:
                            logger.warning(f'用户[{request.user_id}]尝试查看无权限的项目[{task.project.project_id}]的构建任务')
                            return JsonResponse({
                                'code': 403,
                                'message': '没有权限查看该项目的构建任务'
                            }, status=403)

                    # 环境权限检查
                    environment_scope = data_permissions.get('environment_scope', 'all')
                    if environment_scope == 'custom':
                        permitted_environment_types = data_permissions.get('environment_types', [])
                        if task.environment and task.environment.type not in permitted_environment_types:
                            logger.warning(f'用户[{request.user_id}]尝试查看无权限的环境类型[{task.environment.type}]的构建任务')
                            return JsonResponse({
                                'code': 403,
                                'message': '没有权限查看该环境的构建任务'
                            }, status=403)

                    # 获取最新的构建历史
                    latest_build = BuildHistory.objects.filter(task=task).order_by('-build_number').first()

                    # 获取通知机器人详情
                    notification_robots = []
                    if task.notification_channels:
                        robots = NotificationRobot.objects.filter(robot_id__in=task.notification_channels)
                        for robot in robots:
                            notification_robots.append({
                                'robot_id': robot.robot_id,
                                'type': robot.type,
                                'name': robot.name
                            })

                    return JsonResponse({
                        'code': 200,
                        'message': '获取任务详情成功',
                        'data': {
                            'task_id': task.task_id,
                            'name': task.name,
                            'project': {
                                'project_id': task.project.project_id,
                                'name': task.project.name,
                                'repository': task.project.repository
                            } if task.project else None,
                            'environment': {
                                'environment_id': task.environment.environment_id,
                                'name': task.environment.name,
                                'type': task.environment.type
                            } if task.environment else None,
                            'description': task.description,
                            'requirement': task.requirement,
                            'branch': task.branch,
                            'git_token': {
                                'credential_id': task.git_token.credential_id,
                                'name': task.git_token.name
                            } if task.git_token else None,
                            'stages': task.stages,
                            'notification_channels': task.notification_channels,
                            'notification_robots': notification_robots,
                            # 外部脚本库配置
                            'use_external_script': task.use_external_script,
                            'external_script_repo_url': task.external_script_config.get('repo_url', '') if task.external_script_config else '',
                            'external_script_directory': task.external_script_config.get('directory', '') if task.external_script_config else '',
                            'external_script_branch': task.external_script_config.get('branch', '') if task.external_script_config else '',
                            'external_script_token_id': task.external_script_config.get('token_id') if task.external_script_config else None,
                            'status': task.status,
                            'building_status': task.building_status,  # 添加构建状态字段
                            'version': task.version,
                            'last_build_number': task.last_build_number,
                            'total_builds': task.total_builds,
                            'success_builds': task.success_builds,
                            'failure_builds': task.failure_builds,
                            'last_build': {
                                'id': latest_build.history_id,
                                'number': latest_build.build_number,
                                'status': latest_build.status,
                                'time': latest_build.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                                'duration': '未完成' if latest_build.status in ['pending', 'running'] else str(latest_build.build_time.get('total_duration', 0)) + '秒'
                            } if latest_build else None,
                            'creator': {
                                'user_id': task.creator.user_id,
                                'name': task.creator.name
                            } if task.creator else None,
                            'create_time': task.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                            'update_time': task.update_time.strftime('%Y-%m-%d %H:%M:%S')
                        }
                    })
                except BuildTask.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '任务不存在'
                    })

            # 获取查询参数
            project_id = request.GET.get('project_id')
            environment_id = request.GET.get('environment_id')
            name = request.GET.get('name')

            # 构建查询条件
            query = Q()

            # 应用项目权限过滤
            project_scope = data_permissions.get('project_scope', 'all')
            if project_scope == 'custom':
                permitted_project_ids = data_permissions.get('project_ids', [])
                if not permitted_project_ids:
                    # 如果设置了自定义项目权限但列表为空，意味着没有权限查看任何项目
                    logger.info(f'用户[{request.user_id}]没有权限查看任何项目的构建任务')
                    return JsonResponse({
                        'code': 200,
                        'message': '获取任务列表成功',
                        'data': []
                    })

                # 用户只能查看有权限的项目
                if project_id and project_id != 'all':
                    # 如果指定了项目，检查是否有该项目的权限
                    if project_id not in permitted_project_ids:
                        logger.warning(f'用户[{request.user_id}]尝试查看无权限的项目[{project_id}]的构建任务')
                        return JsonResponse({
                            'code': 403,
                            'message': '没有权限查看该项目的构建任务'
                        }, status=403)
                    query &= Q(project__project_id=project_id)
                else:
                    # 如果没有指定项目或选择了全部，则限制为有权限的项目
                    query &= Q(project__project_id__in=permitted_project_ids)
            else:
                # 如果有全部项目权限，并且指定了项目ID
                if project_id and project_id != 'all':
                    query &= Q(project__project_id=project_id)

            # 应用环境权限过滤
            environment_scope = data_permissions.get('environment_scope', 'all')
            if environment_scope == 'custom':
                permitted_environment_types = data_permissions.get('environment_types', [])
                if not permitted_environment_types:
                    # 如果设置了自定义环境权限但列表为空，意味着没有权限查看任何环境
                    logger.info(f'用户[{request.user_id}]没有权限查看任何环境的构建任务')
                    return JsonResponse({
                        'code': 200,
                        'message': '获取任务列表成功',
                        'data': []
                    })

                if environment_id and environment_id != 'all':
                    # 如果指定了环境，需要检查是否在有权限的环境类型中
                    try:
                        env = Environment.objects.get(environment_id=environment_id)
                        if env.type not in permitted_environment_types:
                            logger.warning(f'用户[{request.user_id}]尝试查看无权限的环境[{environment_id}]的构建任务')
                            return JsonResponse({
                                'code': 403,
                                'message': '没有权限查看该环境的构建任务'
                            }, status=403)
                        query &= Q(environment__environment_id=environment_id)
                    except Environment.DoesNotExist:
                        return JsonResponse({
                            'code': 404,
                            'message': '环境不存在'
                        }, status=404)
                else:
                    # 如果没有指定环境或选择了全部，则限制为有权限的环境类型
                    query &= Q(environment__type__in=permitted_environment_types)
            else:
                # 如果有全部环境权限，并且指定了环境ID
                if environment_id and environment_id != 'all':
                    query &= Q(environment__environment_id=environment_id)

            # 添加其他查询条件
            if name:
                query &= Q(name__icontains=name)

            # 查询任务列表
            tasks = BuildTask.objects.select_related(
                'project',
                'environment',
                'creator'
            ).filter(query)

            task_list = []
            for task in tasks:
                # 获取最新的构建历史
                latest_build = BuildHistory.objects.filter(task=task).order_by('-build_number').first()

                task_list.append({
                    'task_id': task.task_id,
                    'name': task.name,
                    'project': {
                        'project_id': task.project.project_id,
                        'name': task.project.name
                    } if task.project else None,
                    'environment': {
                        'environment_id': task.environment.environment_id,
                        'name': task.environment.name,
                        'type': task.environment.type
                    } if task.environment else None,
                    'description': task.description,
                    'branch': task.branch,
                    'status': task.status,
                    'building_status': task.building_status,  # 添加构建状态字段
                    'version': task.version,
                    'last_build_number': task.last_build_number,
                    'total_builds': task.total_builds,
                    'success_builds': task.success_builds,
                    'failure_builds': task.failure_builds,
                    'last_build': {
                        'id': latest_build.history_id,
                        'number': latest_build.build_number,
                        'status': latest_build.status,
                        'time': latest_build.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'duration': '未完成' if latest_build.status in ['pending', 'running'] else str(latest_build.build_time.get('total_duration', 0)) + '秒'
                    } if latest_build else None,
                    'creator': {
                        'user_id': task.creator.user_id,
                        'name': task.creator.name
                    } if task.creator else None,
                    'create_time': task.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'update_time': task.update_time.strftime('%Y-%m-%d %H:%M:%S')
                })

            return JsonResponse({
                'code': 200,
                'message': '获取任务列表成功',
                'data': task_list
            })
        except Exception as e:
            logger.error(f'获取构建任务失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def post(self, request):
        """创建构建任务"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                name = data.get('name')
                project_id = data.get('project_id')
                environment_id = data.get('environment_id')
                description = data.get('description')
                branch = data.get('branch', 'main')
                git_token_id = data.get('git_token_id')
                stages = data.get('stages', [])
                notification_channels = data.get('notification_channels', [])

                # 外部脚本库配置
                use_external_script = data.get('use_external_script')
                external_script_config = None
                if 'use_external_script' in data:
                    if use_external_script:
                        repo_url = data.get('external_script_repo_url', '').strip()
                        directory = data.get('external_script_directory', '').strip()
                        external_script_branch = data.get('external_script_branch', '').strip()
                        token_id = data.get('external_script_token_id')

                        # 验证外部脚本库必填字段
                        if not repo_url:
                            return JsonResponse({
                                'code': 400,
                                'message': '外部脚本库仓库地址不能为空'
                            })
                        if not directory:
                            return JsonResponse({
                                'code': 400,
                                'message': '外部脚本库存放目录不能为空'
                            })
                        if not external_script_branch:
                            return JsonResponse({
                                'code': 400,
                                'message': '外部脚本库分支名称不能为空'
                            })

                        external_script_config = {
                            'repo_url': repo_url,
                            'directory': directory,
                            'branch': external_script_branch,
                            'token_id': token_id
                        }
                    else:
                        external_script_config = {}

                # 验证必要字段
                if not all([name, project_id, environment_id]):
                    return JsonResponse({
                        'code': 400,
                        'message': '任务名称、项目和环境不能为空'
                    })

                # 验证通知机器人是否存在
                if notification_channels:
                    existing_robots = set(NotificationRobot.objects.filter(
                        robot_id__in=notification_channels
                    ).values_list('robot_id', flat=True))
                    invalid_robots = set(notification_channels) - existing_robots
                    if invalid_robots:
                        return JsonResponse({
                            'code': 400,
                            'message': f'以下机器人不存在: {", ".join(invalid_robots)}'
                        })

                # 检查项目是否存在
                try:
                    project = Project.objects.get(project_id=project_id)
                except Project.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '项目不存在'
                    })

                # 检查环境是否存在
                try:
                    environment = Environment.objects.get(environment_id=environment_id)
                except Environment.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '环境不存在'
                    })

                # 检查GitLab Token凭证是否存在
                git_token = None
                if git_token_id:
                    try:
                        git_token = GitlabTokenCredential.objects.get(credential_id=git_token_id)
                    except GitlabTokenCredential.DoesNotExist:
                        return JsonResponse({
                            'code': 404,
                            'message': 'GitLab Token凭证不存在'
                        })

                # 创建构建任务
                creator = User.objects.get(user_id=request.user_id)
                task = BuildTask.objects.create(
                    task_id=generate_id(),
                    name=name,
                    project=project,
                    environment=environment,
                    description=description,
                    branch=branch,
                    git_token=git_token,
                    stages=stages,
                    notification_channels=notification_channels,
                    use_external_script=use_external_script,
                    external_script_config=external_script_config,
                    creator=creator
                )

                return JsonResponse({
                    'code': 200,
                    'message': '创建构建任务成功',
                    'data': {
                        'task_id': task.task_id,
                        'name': task.name
                    }
                })
        except Exception as e:
            logger.error(f'创建构建任务失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def put(self, request):
        """更新构建任务"""
        try:
            # 获取当前用户的权限信息
            user_permissions = get_user_permissions(request.user_id)
            data_permissions = user_permissions.get('data', {})
            function_permissions = user_permissions.get('function', {})
            build_permissions = function_permissions.get('build_task', [])

            with transaction.atomic():
                data = json.loads(request.body)
                
                task_id = data.get('task_id')
                name = data.get('name')
                project_id = data.get('project_id')
                environment_id = data.get('environment_id')
                description = data.get('description')
                branch = data.get('branch')
                git_token_id = data.get('git_token_id')
                stages = data.get('stages')
                notification_channels = data.get('notification_channels')
                status = data.get('status')

                # 外部脚本库配置
                use_external_script = data.get('use_external_script')
                external_script_config = None
                if 'use_external_script' in data:
                    if use_external_script:
                        repo_url = data.get('external_script_repo_url', '').strip()
                        directory = data.get('external_script_directory', '').strip()
                        external_script_branch = data.get('external_script_branch', '').strip()
                        token_id = data.get('external_script_token_id')

                        # 验证外部脚本库必填字段
                        if not repo_url:
                            return JsonResponse({
                                'code': 400,
                                'message': '外部脚本库仓库地址不能为空'
                            })
                        if not directory:
                            return JsonResponse({
                                'code': 400,
                                'message': '外部脚本库存放目录不能为空'
                            })
                        if not external_script_branch:
                            return JsonResponse({
                                'code': 400,
                                'message': '外部脚本库分支名称不能为空'
                            })

                        external_script_config = {
                            'repo_url': repo_url,
                            'directory': directory,
                            'branch': external_script_branch,
                            'token_id': token_id
                        }
                    else:
                        external_script_config = {}

                if not task_id:
                    return JsonResponse({
                        'code': 400,
                        'message': '任务ID不能为空'
                    })

                try:
                    task = BuildTask.objects.get(task_id=task_id)
                except BuildTask.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '任务不存在'
                    })

                # 如果只修改状态，需要检查是否有禁用权限
                if status and len(data) == 2 and 'task_id' in data and 'status' in data:
                    if 'disable' not in build_permissions:
                        logger.warning(f'用户[{request.user_id}]没有禁用/启用任务权限')
                        return JsonResponse({
                            'code': 403,
                            'message': '没有权限禁用/启用任务'
                        }, status=403)
                else:
                    # 否则检查是否有编辑权限
                    if 'edit' not in build_permissions:
                        logger.warning(f'用户[{request.user_id}]没有编辑任务权限')
                        return JsonResponse({
                            'code': 403,
                            'message': '没有权限编辑任务'
                        }, status=403)

                # 项目权限检查
                project_scope = data_permissions.get('project_scope', 'all')
                if project_id and project_scope == 'custom':
                    permitted_project_ids = data_permissions.get('project_ids', [])
                    if project_id not in permitted_project_ids:
                        logger.warning(f'用户[{request.user_id}]尝试编辑无权限的项目[{project_id}]的构建任务')
                        return JsonResponse({
                            'code': 403,
                            'message': '没有权限编辑该项目的构建任务'
                        }, status=403)

                # 环境权限检查
                environment_scope = data_permissions.get('environment_scope', 'all')
                if environment_id and environment_scope == 'custom':
                    try:
                        env = Environment.objects.get(environment_id=environment_id)
                        permitted_environment_types = data_permissions.get('environment_types', [])
                        if env.type not in permitted_environment_types:
                            logger.warning(f'用户[{request.user_id}]尝试编辑无权限的环境类型[{env.type}]的构建任务')
                            return JsonResponse({
                                'code': 403,
                                'message': '没有权限编辑该环境的构建任务'
                            }, status=403)
                    except Environment.DoesNotExist:
                        return JsonResponse({
                            'code': 404,
                            'message': '环境不存在'
                        })

                # 更新项目关联
                if project_id:
                    try:
                        project = Project.objects.get(project_id=project_id)
                        task.project = project
                    except Project.DoesNotExist:
                        return JsonResponse({
                            'code': 404,
                            'message': '项目不存在'
                        })

                # 更新环境关联
                if environment_id:
                    try:
                        environment = Environment.objects.get(environment_id=environment_id)
                        task.environment = environment
                    except Environment.DoesNotExist:
                        return JsonResponse({
                            'code': 404,
                            'message': '环境不存在'
                        })

                # 更新GitLab Token凭证关联
                if 'git_token_id' in data:
                    if git_token_id:
                        try:
                            git_token = GitlabTokenCredential.objects.get(credential_id=git_token_id)
                            task.git_token = git_token
                        except GitlabTokenCredential.DoesNotExist:
                            return JsonResponse({
                                'code': 404,
                                'message': 'GitLab Token凭证不存在'
                            })
                    else:
                        task.git_token = None

                # 更新其他字段
                if 'name' in data:
                    task.name = name
                if 'description' in data:
                    task.description = description
                if 'branch' in data:
                    task.branch = branch
                if 'stages' in data:
                    task.stages = stages
                if 'notification_channels' in data:
                    # 验证通知机器人是否存在
                    existing_robots = set(NotificationRobot.objects.filter(
                        robot_id__in=notification_channels
                    ).values_list('robot_id', flat=True))
                    invalid_robots = set(notification_channels) - existing_robots
                    if invalid_robots:
                        return JsonResponse({
                            'code': 400,
                            'message': f'以下机器人不存在: {", ".join(invalid_robots)}'
                        })
                    task.notification_channels = notification_channels
                if 'status' in data:
                    task.status = status

                # 更新外部脚本库配置
                if 'use_external_script' in data:
                    task.use_external_script = use_external_script
                    task.external_script_config = external_script_config

                task.save()

                return JsonResponse({
                    'code': 200,
                    'message': '更新构建任务成功'
                })
        except Exception as e:
            logger.error(f'更新构建任务失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def delete(self, request):
        """删除构建任务"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                task_id = data.get('task_id')

                if not task_id:
                    return JsonResponse({
                        'code': 400,
                        'message': '任务ID不能为空'
                    })

                try:
                    task = BuildTask.objects.get(task_id=task_id)
                    task.delete()
                    return JsonResponse({
                        'code': 200,
                        'message': '删除构建任务成功'
                    })
                except BuildTask.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '任务不存在'
                    })
        except Exception as e:
            logger.error(f'删除构建任务失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

@method_decorator(csrf_exempt, name='dispatch')
class BuildExecuteView(View):
    @method_decorator(jwt_auth_required)
    def post(self, request):
        """执行构建"""
        try:
            # 获取当前用户的权限信息
            user_permissions = get_user_permissions(request.user_id)
            data_permissions = user_permissions.get('data', {})

            # 检查用户是否有执行构建权限
            function_permissions = user_permissions.get('function', {})
            build_permissions = function_permissions.get('build_task', [])

            if 'execute' not in build_permissions:
                logger.warning(f'用户[{request.user_id}]没有执行构建权限')
                return JsonResponse({
                    'code': 403,
                    'message': '没有权限执行构建任务'
                }, status=403)

            data = json.loads(request.body)
            task_id = data.get('task_id')
            branch = data.get('branch')  # 获取用户选择的分支
            commit_id = data.get('commit_id')
            version = data.get('version') 
            requirement = data.get('requirement')

            if not task_id:
                return JsonResponse({
                    'code': 400,
                    'message': '任务ID不能为空'
                })

            try:
                task = BuildTask.objects.select_related('project', 'environment').get(task_id=task_id)
            except BuildTask.DoesNotExist:
                return JsonResponse({
                    'code': 404,
                    'message': '任务不存在'
                })

            # 检查是否有权限执行该任务
            # 项目权限检查
            project_scope = data_permissions.get('project_scope', 'all')
            if project_scope == 'custom':
                permitted_project_ids = data_permissions.get('project_ids', [])
                if task.project and task.project.project_id not in permitted_project_ids:
                    logger.warning(f'用户[{request.user_id}]尝试执行无权限的项目[{task.project.project_id}]的构建任务')
                    return JsonResponse({
                        'code': 403,
                        'message': '没有权限执行该项目的构建任务'
                    }, status=403)

            # 环境权限检查
            environment_scope = data_permissions.get('environment_scope', 'all')
            if environment_scope == 'custom':
                permitted_environment_types = data_permissions.get('environment_types', [])
                if task.environment and task.environment.type not in permitted_environment_types:
                    logger.warning(f'用户[{request.user_id}]尝试执行无权限的环境类型[{task.environment.type}]的构建任务')
                    return JsonResponse({
                        'code': 403,
                        'message': '没有权限执行该环境的构建任务'
                    }, status=403)

            # 根据环境类型检查必要参数
            env_type = task.environment.type if task.environment else None

            if env_type in ['development', 'testing']:
                # 开发环境和测试环境需要分支和commit_id
                if not branch:
                    return JsonResponse({
                        'code': 400,
                        'message': '分支不能为空'
                    })

                if not commit_id:
                    return JsonResponse({
                        'code': 400,
                        'message': 'Commit ID不能为空'
                    })
            elif env_type in ['staging', 'production']:
                if not version:
                    return JsonResponse({
                        'code': 400,
                        'message': '版本号不能为空'
                    })
                parts = version.split('_')
                if len(parts) == 2 and len(parts[1]) >= 8:
                    commit_id = parts[1]
                else:
                    return JsonResponse({
                        'code': 400,
                        'message': '版本号格式不正确，应为：YYYYMMDDHHmmSS_commitId'
                    })

            if not requirement:
                return JsonResponse({
                    'code': 400,
                    'message': '构建需求描述不能为空'
                })

            # 检查任务的构建状态
            if task.building_status == 'building':
                return JsonResponse({
                    'code': 400,
                    'message': '当前任务正在构建中，请等待构建完成后再试'
                })

            running_build = BuildHistory.objects.filter(
                task_id=task_id,
                status__in=['pending', 'running']
            ).exists()

            if running_build:
                # 如果有正在进行的构建，但building_status不是building，则修正状态
                BuildTask.objects.filter(task_id=task_id).update(building_status='building')
                return JsonResponse({
                    'code': 400,
                    'message': '当前任务有正在进行的构建，请等待构建完成后再试'
                })

            if task.status == 'disabled':
                return JsonResponse({
                    'code': 400,
                    'message': '任务已禁用'
                })

            # 生成构建号
            build_number = task.last_build_number + 1

            # 创建构建历史记录
            history = BuildHistory.objects.create(
                history_id=generate_id(),
                task=task,
                build_number=build_number,
                branch=branch if branch else '',  # 对于预发布和生产环境，分支为空
                commit_id=commit_id,
                version=version if version else None,  # 对于预发布和生产环境，使用传入的版本号
                status='pending',  # 初始状态为等待中
                requirement=requirement,
                operator=User.objects.get(user_id=request.user_id)  # 记录构建人
            )

            # 更新任务状态、构建号和构建状态
            BuildTask.objects.filter(task_id=task_id).update(
                last_build_number=build_number,
                total_builds=F('total_builds') + 1,
                building_status='building'  # 设置为构建中状态
            )

            # 在新线程中执行构建
            build_thread = threading.Thread(
                target=execute_build,
                args=(task, build_number, commit_id, history)
            )
            build_thread.start()

            return JsonResponse({
                'code': 200,
                'message': '开始构建',
                'data': {
                    'build_number': build_number,
                    'history_id': history.history_id
                }
            })
        except Exception as e:
            logger.error(f'执行构建失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def put(self, request):
        """停止构建"""
        try:
            data = json.loads(request.body)
            history_id = data.get('history_id')

            if not history_id:
                return JsonResponse({
                    'code': 400,
                    'message': '历史ID不能为空'
                })

            try:
                history = BuildHistory.objects.get(history_id=history_id)
            except BuildHistory.DoesNotExist:
                return JsonResponse({
                    'code': 404,
                    'message': '构建历史不存在'
                })

            # 只有进行中的构建可以停止
            if history.status not in ['pending', 'running']:
                return JsonResponse({
                    'code': 400,
                    'message': '只能停止进行中的构建'
                })

            # 更新构建状态为terminated
            history.status = 'terminated'

            # 如果构建日志存在，追加终止消息
            if history.build_log:
                history.build_log += "\n[系统] 构建被手动终止\n"
            else:
                history.build_log = "[系统] 构建被手动终止\n"

            # 更新构建时间
            if not history.build_time:
                history.build_time = {}

            if 'start_time' in history.build_time and 'total_duration' not in history.build_time:
                # 计算从开始到现在的持续时间
                start_time = datetime.strptime(history.build_time['start_time'], '%Y-%m-%d %H:%M:%S')
                duration = int((datetime.now() - start_time).total_seconds())
                history.build_time['total_duration'] = str(duration)
                history.build_time['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            history.save()

            # 更新任务统计信息和构建状态
            BuildTask.objects.filter(task_id=history.task.task_id).update(
                building_status='idle'  # 重置构建状态为空闲
            )

            return JsonResponse({
                'code': 200,
                'message': '构建已终止'
            })

        except Exception as e:
            logger.error(f'停止构建失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })