import json
import logging
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from ..models import SecurityConfig, User, BuildTask, BuildHistory, LoginLog
from ..utils.auth import jwt_auth_required
from ..utils.permissions import get_user_permissions

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


@csrf_exempt
@jwt_auth_required
@require_http_methods(["GET"])
def get_build_tasks_for_cleanup(request):
    """获取可用于日志清理的构建任务列表"""
    try:
        # 获取用户权限信息
        user_permissions = get_user_permissions(request.user_id)
        data_permissions = user_permissions.get('data', {})

        # 检查用户是否有系统基本设置权限
        function_permissions = user_permissions.get('function', {})
        system_permissions = function_permissions.get('system_basic', [])

        if 'view' not in system_permissions:
            logger.warning(f'用户[{request.user_id}]没有系统基本设置查看权限')
            return JsonResponse({
                'code': 403,
                'message': '没有权限查看构建任务'
            }, status=403)

        # 应用项目权限过滤
        project_scope = data_permissions.get('project_scope', 'all')
        if project_scope == 'custom':
            permitted_project_ids = data_permissions.get('project_ids', [])
            if not permitted_project_ids:
                return JsonResponse({
                    'code': 200,
                    'message': '获取构建任务列表成功',
                    'data': []
                })
            tasks = BuildTask.objects.filter(project__project_id__in=permitted_project_ids).select_related('project')
        else:
            tasks = BuildTask.objects.all().select_related('project')

        # 格式化返回数据
        task_list = []
        for task in tasks:
            task_list.append({
                'task_id': task.task_id,
                'name': task.name,
                'project_name': task.project.name if task.project else '未知项目',
                'total_builds': task.total_builds
            })

        return JsonResponse({
            'code': 200,
            'message': '获取构建任务列表成功',
            'data': task_list
        })

    except Exception as e:
        logger.error(f'获取构建任务列表失败: {str(e)}', exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        })


@csrf_exempt
@jwt_auth_required
@require_http_methods(["POST"])
def cleanup_build_logs(request):
    """清理构建日志"""
    try:
        # 获取用户权限信息
        user_permissions = get_user_permissions(request.user_id)

        # 检查用户是否有系统基本设置编辑权限
        function_permissions = user_permissions.get('function', {})
        system_permissions = function_permissions.get('system_basic', [])

        if 'edit' not in system_permissions:
            logger.warning(f'用户[{request.user_id}]没有系统基本设置编辑权限')
            return JsonResponse({
                'code': 403,
                'message': '没有权限执行日志清理操作'
            }, status=403)

        data = json.loads(request.body)
        task_ids = data.get('task_ids', [])
        days_before = data.get('days_before', 30)

        if not isinstance(days_before, int) or days_before < 1 or days_before > 365:
            return JsonResponse({
                'code': 400,
                'message': '保留天数必须在1-365天之间'
            })

        # 计算截止日期
        cutoff_date = timezone.now() - timedelta(days=days_before)

        # 查询要删除的构建历史记录
        if task_ids:
            # 清理指定任务的日志
            histories_to_delete = BuildHistory.objects.filter(
                task__task_id__in=task_ids,
                create_time__lt=cutoff_date
            )
        else:
            # 清理所有任务的日志
            histories_to_delete = BuildHistory.objects.filter(
                create_time__lt=cutoff_date
            )

        # 统计信息
        total_count = histories_to_delete.count()

        if total_count == 0:
            task_desc = f"{len(task_ids)}个指定任务" if task_ids else "所有任务"
            return JsonResponse({
                'code': 200,
                'message': f'没有找到{task_desc}中需要清理的构建日志记录',
                'data': {
                    'deleted_count': 0,
                    'task_count': len(task_ids) if task_ids else 0,
                    'days_before': days_before
                }
            })

        # 执行删除操作
        with transaction.atomic():
            deleted_count, _ = histories_to_delete.delete()

            # 记录操作日志
            user = User.objects.get(user_id=request.user_id)
            task_desc = f"{len(task_ids)}个指定任务" if task_ids else "所有任务"
            logger.info(f'用户[{user.username}]清理了{task_desc}{days_before}天前的构建日志，共删除{deleted_count}条记录')

        return JsonResponse({
            'code': 200,
            'message': f'构建日志清理完成，共删除{deleted_count}条记录',
            'data': {
                'deleted_count': deleted_count,
                'task_count': len(task_ids) if task_ids else 0,
                'days_before': days_before
            }
        })

    except Exception as e:
        logger.error(f'清理构建日志失败: {str(e)}', exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        })


@csrf_exempt
@jwt_auth_required
@require_http_methods(["POST"])
def cleanup_login_logs(request):
    """清理登录日志"""
    try:
        # 获取用户权限信息
        user_permissions = get_user_permissions(request.user_id)

        # 检查用户是否有系统基本设置编辑权限
        function_permissions = user_permissions.get('function', {})
        system_permissions = function_permissions.get('system_basic', [])

        if 'edit' not in system_permissions:
            logger.warning(f'用户[{request.user_id}]没有系统基本设置编辑权限')
            return JsonResponse({
                'code': 403,
                'message': '没有权限执行日志清理操作'
            }, status=403)

        data = json.loads(request.body)
        days_before = data.get('days_before', 30)

        # 验证输入参数
        if not isinstance(days_before, int) or days_before < 1 or days_before > 365:
            return JsonResponse({
                'code': 400,
                'message': '保留天数必须在1-365天之间'
            })

        # 计算截止日期
        cutoff_date = timezone.now() - timedelta(days=days_before)

        # 查询要删除的登录日志记录
        logs_to_delete = LoginLog.objects.filter(
            login_time__lt=cutoff_date
        )

        # 统计信息
        total_count = logs_to_delete.count()

        if total_count == 0:
            return JsonResponse({
                'code': 200,
                'message': '没有找到需要清理的登录日志记录',
                'data': {
                    'deleted_count': 0,
                    'days_before': days_before
                }
            })

        # 执行删除操作
        with transaction.atomic():
            deleted_count, _ = logs_to_delete.delete()

            # 记录操作日志
            user = User.objects.get(user_id=request.user_id)
            logger.info(f'用户[{user.username}]清理了{days_before}天前的登录日志，共删除{deleted_count}条记录')

        return JsonResponse({
            'code': 200,
            'message': f'登录日志清理完成，共删除{deleted_count}条记录',
            'data': {
                'deleted_count': deleted_count,
                'days_before': days_before
            }
        })

    except Exception as e:
        logger.error(f'清理登录日志失败: {str(e)}', exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        })