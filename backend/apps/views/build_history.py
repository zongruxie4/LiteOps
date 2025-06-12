import json
import logging
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from ..models import BuildHistory, BuildTask, Project, Environment
from ..utils.auth import jwt_auth_required
from ..utils.permissions import get_user_permissions

logger = logging.getLogger('apps')

@method_decorator(csrf_exempt, name='dispatch')
class BuildHistoryView(View):
    def _get_stage_status_from_log(self, log: str, stage_name: str, overall_status: str = None) -> str:
        """从日志中获取指定阶段的状态"""
        if not log:
            return 'failed'
        
        # 处理特殊阶段：Git Clone
        if stage_name == 'Git Clone':
            # Git Clone 阶段使用 [Git Clone] 格式
            if '[Git Clone]' not in log:
                return 'failed'
            
            # 检查是否有完成标记
            if '[Git Clone] 代码克隆完成' in log:
                return 'success'
            elif overall_status == 'terminated':
                return 'terminated'
            else:
                return 'failed'
        
        # 处理普通构建阶段
        stage_start_pattern = f'[Build Stages] 开始执行阶段: {stage_name}'
        stage_complete_pattern = f'[Build Stages] 阶段 {stage_name} 执行完成'
        
        # 如果整体构建状态是terminated，检查阶段是否有开始执行
        if overall_status == 'terminated':
            if stage_start_pattern in log:
                # 检查阶段是否完成
                if stage_complete_pattern in log:
                    return 'success'
                else:
                    return 'terminated'
            else:
                # 没有该阶段的日志，说明还没开始执行就被终止了
                return 'terminated'
        
        if stage_start_pattern not in log:
            return 'failed'  # 阶段未开始执行
        
        # 检查阶段是否完成
        if stage_complete_pattern in log:
            return 'success'  # 阶段成功完成
        else:
            return 'failed'  # 阶段开始了但没有完成

    @method_decorator(jwt_auth_required)
    def get(self, request):
        """获取构建历史列表"""
        try:
            # 获取当前用户的权限信息
            user_permissions = get_user_permissions(request.user_id)
            data_permissions = user_permissions.get('data', {})
            
            # 检查用户是否有构建历史查看权限
            function_permissions = user_permissions.get('function', {})
            build_history_permissions = function_permissions.get('build_history', [])
            
            if 'view' not in build_history_permissions:
                logger.warning(f'用户[{request.user_id}]没有构建历史查看权限')
                return JsonResponse({
                    'code': 403,
                    'message': '没有权限查看构建历史'
                }, status=403)
            
            # 获取查询参数
            project_id = request.GET.get('project_id')
            environment_id = request.GET.get('environment_id')
            task_id = request.GET.get('task_id')  # 添加task_id参数
            task_name = request.GET.get('task_name')
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))

            # 构建查询条件
            query = Q()
            
            # 应用项目权限过滤
            project_scope = data_permissions.get('project_scope', 'all')
            if project_scope == 'custom':
                permitted_project_ids = data_permissions.get('project_ids', [])
                if not permitted_project_ids:
                    logger.info(f'用户[{request.user_id}]没有权限查看任何项目的构建历史')
                    return JsonResponse({
                        'code': 200,
                        'message': '获取构建历史列表成功',
                        'data': [],
                        'total': 0,
                        'page': page,
                        'page_size': page_size
                    })
                
                # 用户只能查看有权限的项目
                if project_id and project_id != 'all':
                    # 如果指定了项目，检查是否有该项目的权限
                    if project_id not in permitted_project_ids:
                        logger.warning(f'用户[{request.user_id}]尝试查看无权限的项目[{project_id}]的构建历史')
                        return JsonResponse({
                            'code': 403,
                            'message': '没有权限查看该项目的构建历史'
                        }, status=403)
                    query &= Q(task__project__project_id=project_id)
                else:
                    query &= Q(task__project__project_id__in=permitted_project_ids)
            else:
                # 如果有全部项目权限，并且指定了项目ID
                if project_id and project_id != 'all':
                    query &= Q(task__project__project_id=project_id)
            
            # 应用环境权限过滤
            environment_scope = data_permissions.get('environment_scope', 'all')
            if environment_scope == 'custom':
                permitted_environment_types = data_permissions.get('environment_types', [])
                if not permitted_environment_types:
                    # 如果设置了自定义环境权限但列表为空，意味着没有权限查看任何环境
                    logger.info(f'用户[{request.user_id}]没有权限查看任何环境的构建历史')
                    return JsonResponse({
                        'code': 200,
                        'message': '获取构建历史列表成功',
                        'data': [],
                        'total': 0,
                        'page': page,
                        'page_size': page_size
                    })
                
                if environment_id and environment_id != 'all':
                    # 如果指定了环境，需要检查是否在有权限的环境类型中
                    try:
                        env = Environment.objects.get(environment_id=environment_id)
                        if env.type not in permitted_environment_types:
                            logger.warning(f'用户[{request.user_id}]尝试查看无权限的环境[{environment_id}]的构建历史')
                            return JsonResponse({
                                'code': 403,
                                'message': '没有权限查看该环境的构建历史'
                            }, status=403)
                        query &= Q(task__environment__environment_id=environment_id)
                    except Environment.DoesNotExist:
                        return JsonResponse({
                            'code': 404,
                            'message': '环境不存在'
                        }, status=404)
                else:
                    # 如果没有指定环境或选择了全部，则限制为有权限的环境类型
                    query &= Q(task__environment__type__in=permitted_environment_types)
            else:
                # 如果有全部环境权限，并且指定了环境ID
                if environment_id and environment_id != 'all':
                    query &= Q(task__environment__environment_id=environment_id)
            
            # 添加其他查询条件
            if task_id:
                query &= Q(task__task_id=task_id)
            if task_name:
                query &= Q(task__name__icontains=task_name)

            # 查询构建历史
            histories = BuildHistory.objects.select_related(
                'task',
                'task__project',
                'task__environment',
                'operator'
            ).filter(query).order_by('-create_time')

            # 计算总数
            total = histories.count()

            # 分页
            start = (page - 1) * page_size
            end = start + page_size
            histories = histories[start:end]

            # 构建返回数据
            history_list = []
            for history in histories:
                # 计算构建耗时
                duration = '未完成'
                if history.build_time and 'total_duration' in history.build_time:
                    duration_seconds = int(history.build_time['total_duration'])
                    if duration_seconds < 60:
                        duration = f"{duration_seconds}秒"
                    else:
                        minutes = duration_seconds // 60
                        seconds = duration_seconds % 60
                        duration = f"{minutes}分{seconds}秒"

                # 处理构建阶段信息
                stages = []
                
                # 添加 Git Clone 阶段
                git_clone_stage = next(
                    (t for t in history.build_time.get('stages_time', []) if t['name'] == 'Git Clone'),
                    None
                ) if history.build_time else None

                if git_clone_stage:
                    git_clone_status = self._get_stage_status_from_log(history.build_log, 'Git Clone', history.status)
                    stages.append({
                        'name': 'Git Clone',
                        'status': git_clone_status,
                        'startTime': git_clone_stage['start_time'],
                        'duration': git_clone_stage['duration'] + '秒'
                    })

                # 添加其他阶段
                for stage in history.stages:
                    stage_time = next(
                        (t for t in history.build_time.get('stages_time', []) if t['name'] == stage['name']),
                        None
                    ) if history.build_time else None

                    stage_status = self._get_stage_status_from_log(history.build_log, stage['name'], history.status)
                    stages.append({
                        'name': stage['name'],
                        'status': stage_status,
                        'startTime': stage_time['start_time'] if stage_time else None,
                        'duration': stage_time['duration'] + '秒' if stage_time else '未知'
                    })

                # 检查是否有回滚权限
                can_rollback = history.status == 'success'

                history_list.append({
                    'id': history.history_id,
                    'build_number': history.build_number,
                    'status': history.status,
                    'branch': history.branch,
                    'commit': history.commit_id[:8] if history.commit_id else None,
                    'version': history.version,
                    'environment': history.task.environment.name if history.task.environment else None,
                    'startTime': history.build_time.get('start_time') if history.build_time else history.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': duration,
                    'operator': history.operator.name if history.operator else None,
                    'requirement': history.requirement,
                    'stages': stages,
                    'canRollback': can_rollback,
                    'task': {
                        'id': history.task.task_id,
                        'name': history.task.name,
                        'description': history.task.description
                    }
                })

            return JsonResponse({
                'code': 200,
                'message': '获取构建历史列表成功',
                'data': history_list,
                'total': total,
                'page': page,
                'page_size': page_size
            })

        except Exception as e:
            logger.error(f'获取构建历史列表失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def post(self, request):
        """回滚到指定版本"""
        try:
            # 获取当前用户的权限信息
            user_permissions = get_user_permissions(request.user_id)
            function_permissions = user_permissions.get('function', {})
            build_history_permissions = function_permissions.get('build_history', [])
            
            # 检查是否有回滚权限
            if 'rollback' not in build_history_permissions:
                logger.warning(f'用户[{request.user_id}]没有构建历史回滚权限')
                return JsonResponse({
                    'code': 403,
                    'message': '没有权限执行回滚操作'
                }, status=403)
            
            data = json.loads(request.body)
            history_id = data.get('history_id')

            if not history_id:
                return JsonResponse({
                    'code': 400,
                    'message': '历史ID不能为空'
                })

            try:
                history = BuildHistory.objects.select_related('task', 'task__project', 'task__environment').get(history_id=history_id)
            except BuildHistory.DoesNotExist:
                return JsonResponse({
                    'code': 404,
                    'message': '构建历史不存在'
                })

            # 检查项目和环境权限
            data_permissions = user_permissions.get('data', {})
            
            # 项目权限检查
            project_scope = data_permissions.get('project_scope', 'all')
            if project_scope == 'custom':
                permitted_project_ids = data_permissions.get('project_ids', [])
                if history.task.project.project_id not in permitted_project_ids:
                    logger.warning(f'用户[{request.user_id}]尝试回滚无权限的项目[{history.task.project.project_id}]的构建')
                    return JsonResponse({
                        'code': 403,
                        'message': '没有权限回滚该项目的构建'
                    }, status=403)
            
            # 环境权限检查
            environment_scope = data_permissions.get('environment_scope', 'all')
            if environment_scope == 'custom':
                permitted_environment_types = data_permissions.get('environment_types', [])
                if history.task.environment.type not in permitted_environment_types:
                    logger.warning(f'用户[{request.user_id}]尝试回滚无权限的环境类型[{history.task.environment.type}]的构建')
                    return JsonResponse({
                        'code': 403,
                        'message': '没有权限回滚该环境的构建'
                    }, status=403)

            if history.status != 'success':
                return JsonResponse({
                    'code': 400,
                    'message': '只能回滚到构建成功的版本'
                })

            # TODO: 实现回滚逻辑

            return JsonResponse({
                'code': 200,
                'message': '开始回滚',
                'data': {
                    'version': history.version
                }
            })

        except Exception as e:
            logger.error(f'回滚失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })


@method_decorator(csrf_exempt, name='dispatch')
class BuildLogView(View):
    @method_decorator(jwt_auth_required)
    def get(self, request, history_id):
        """获取构建日志"""
        try:
            # 获取当前用户的权限信息
            user_permissions = get_user_permissions(request.user_id)
            data_permissions = user_permissions.get('data', {})
            
            # 检查用户是否有构建历史查看日志权限
            function_permissions = user_permissions.get('function', {})
            build_task_permissions = function_permissions.get('build_task', [])
            build_history_permissions = function_permissions.get('build_history', [])
            
            has_log_permission = 'view_log' in build_task_permissions or 'view_log' in build_history_permissions
            
            if not has_log_permission:
                logger.warning(f'用户[{request.user_id}]没有构建历史查看日志权限')
                return JsonResponse({
                    'code': 403,
                    'message': '没有权限查看构建日志'
                }, status=403)
            
            try:
                history = BuildHistory.objects.select_related('task', 'task__project', 'task__environment').get(history_id=history_id)
            except BuildHistory.DoesNotExist:
                return JsonResponse({
                    'code': 404,
                    'message': '构建历史不存在'
                })
                
            # 项目权限检查
            project_scope = data_permissions.get('project_scope', 'all')
            if project_scope == 'custom':
                permitted_project_ids = data_permissions.get('project_ids', [])
                if history.task.project and history.task.project.project_id not in permitted_project_ids:
                    logger.warning(f'用户[{request.user_id}]尝试查看无权限的项目[{history.task.project.project_id}]的构建日志')
                    return JsonResponse({
                        'code': 403,
                        'message': '没有权限查看该项目的构建日志'
                    }, status=403)
            
            # 环境权限检查
            environment_scope = data_permissions.get('environment_scope', 'all')
            if environment_scope == 'custom':
                permitted_environment_types = data_permissions.get('environment_types', [])
                if history.task.environment and history.task.environment.type not in permitted_environment_types:
                    logger.warning(f'用户[{request.user_id}]尝试查看无权限的环境类型[{history.task.environment.type}]的构建日志')
                    return JsonResponse({
                        'code': 403,
                        'message': '没有权限查看该环境的构建日志'
                    }, status=403)

            # 检查是否为下载请求
            is_download = request.GET.get('download') == 'true'
            if is_download:
                # 生成日志文件名
                filename = f"build_log_{history.task.name}_{history.build_number}.txt"
                
                # 准备日志内容
                log_content = history.build_log or '暂无日志'
                
                # 创建响应对象
                response = HttpResponse(log_content, content_type='text/plain')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response

            return JsonResponse({
                'code': 200,
                'message': '获取构建日志成功',
                'data': {
                    'log': history.build_log or '暂无日志'
                }
            })

        except Exception as e:
            logger.error(f'获取构建日志失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })


@method_decorator(csrf_exempt, name='dispatch')
class BuildStageLogView(View):
    @method_decorator(jwt_auth_required)
    def get(self, request, history_id, stage_name):
        """获取构建阶段日志"""
        try:
            # 获取当前用户的权限信息
            user_permissions = get_user_permissions(request.user_id)
            data_permissions = user_permissions.get('data', {})
            
            # 检查用户是否有构建历史查看日志权限
            function_permissions = user_permissions.get('function', {})
            build_task_permissions = function_permissions.get('build_task', [])
            build_history_permissions = function_permissions.get('build_history', [])
            
            # 只要有任何一方的view_log权限即可
            has_log_permission = 'view_log' in build_task_permissions or 'view_log' in build_history_permissions
            
            if not has_log_permission:
                logger.warning(f'用户[{request.user_id}]没有构建历史查看日志权限')
                return JsonResponse({
                    'code': 403,
                    'message': '没有权限查看构建日志'
                }, status=403)
            
            try:
                history = BuildHistory.objects.select_related('task', 'task__project', 'task__environment').get(history_id=history_id)
            except BuildHistory.DoesNotExist:
                return JsonResponse({
                    'code': 404,
                    'message': '构建历史不存在'
                })
                
            # 项目权限检查
            project_scope = data_permissions.get('project_scope', 'all')
            if project_scope == 'custom':
                permitted_project_ids = data_permissions.get('project_ids', [])
                if history.task.project and history.task.project.project_id not in permitted_project_ids:
                    logger.warning(f'用户[{request.user_id}]尝试查看无权限的项目[{history.task.project.project_id}]的构建阶段日志')
                    return JsonResponse({
                        'code': 403,
                        'message': '没有权限查看该项目的构建日志'
                    }, status=403)
            
            # 环境权限检查
            environment_scope = data_permissions.get('environment_scope', 'all')
            if environment_scope == 'custom':
                permitted_environment_types = data_permissions.get('environment_types', [])
                if history.task.environment and history.task.environment.type not in permitted_environment_types:
                    logger.warning(f'用户[{request.user_id}]尝试查看无权限的环境类型[{history.task.environment.type}]的构建阶段日志')
                    return JsonResponse({
                        'code': 403,
                        'message': '没有权限查看该环境的构建日志'
                    }, status=403)

            # 在完整日志中查找指定阶段的日志
            if not history.build_log:
                return JsonResponse({
                    'code': 200,
                    'message': '获取阶段日志成功',
                    'data': {
                        'log': '暂无日志'
                    }
                })

            # 适配Jenkins风格日志格式的阶段日志解析
            stage_logs = []
            lines = history.build_log.split('\n')
            in_stage = False
            
            # 处理特殊阶段：Git Clone
            if stage_name == 'Git Clone':
                # Git Clone 阶段使用 [Git Clone] 格式
                for line in lines:
                    if '[Git Clone]' in line:
                        stage_logs.append(line)
            else:
                # 普通构建阶段使用 [Build Stages] 格式
                stage_start_pattern = f'[Build Stages] 开始执行阶段: {stage_name}'
                stage_complete_pattern = f'[Build Stages] 阶段 {stage_name} 执行完成'
                
                for line in lines:
                    if stage_start_pattern in line:
                        in_stage = True
                        stage_logs.append(line)
                    elif in_stage and stage_complete_pattern in line:
                        stage_logs.append(line)
                        break  # 阶段结束
                    elif in_stage:
                        # 在阶段执行期间的所有日志都属于该阶段
                        # 排除其他阶段的开始标记
                        if '[Build Stages] 开始执行阶段:' not in line:
                            stage_logs.append(line)
                        else:
                            # 遇到其他阶段开始，当前阶段结束
                            break

            return JsonResponse({
                'code': 200,
                'message': '获取阶段日志成功',
                'data': {
                    'log': '\n'.join(stage_logs) if stage_logs else '暂无该阶段日志'
                }
            })

        except Exception as e:
            logger.error(f'获取阶段日志失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            }) 