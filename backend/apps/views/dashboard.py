import logging
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count
from ..models import Project, BuildTask, BuildHistory, User, Environment

logger = logging.getLogger('apps')

@method_decorator(csrf_exempt, name='dispatch')
class DashboardStatsView(View):
    """首页统计数据接口"""

    def get(self, request):
        """获取首页统计数据"""
        try:
            # 获取项目总数
            project_count = Project.objects.count()

            # 获取构建任务总数
            task_count = BuildTask.objects.count()

            # 获取用户总数
            user_count = User.objects.count()

            # 获取环境总数
            env_count = Environment.objects.count()

            # 获取总构建数量
            total_builds_count = BuildHistory.objects.count()

            # 获取最近7天的构建成功率
            seven_days_ago = datetime.now() - timedelta(days=7)
            recent_builds = BuildHistory.objects.filter(create_time__gte=seven_days_ago)
            total_recent_builds = recent_builds.count()
            success_recent_builds = recent_builds.filter(status='success').count()

            success_rate = 0
            if total_recent_builds > 0:
                success_rate = round((success_recent_builds / total_recent_builds) * 100, 2)

            return JsonResponse({
                'code': 200,
                'message': '获取首页统计数据成功',
                'data': {
                    'project_count': project_count,
                    'task_count': task_count,
                    'user_count': user_count,
                    'env_count': env_count,
                    'total_builds_count': total_builds_count,
                    'success_rate': success_rate,
                    'total_recent_builds': total_recent_builds
                }
            })
        except Exception as e:
            logger.error(f'获取首页统计数据失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })


@method_decorator(csrf_exempt, name='dispatch')
class BuildTrendView(View):
    """构建任务趋势接口"""

    def get(self, request):
        """获取构建任务趋势数据"""
        try:
            # 获取时间范围参数，默认为最近7天
            days = int(request.GET.get('days', 7))

            # 计算日期范围：包含今天在内的最近 days 天
            today = datetime.now().date() # 获取今天的日期部分
            start_date = today - timedelta(days=days - 1) # 开始日期是今天往前 days-1 天

            # 准备日期列表和结果数据
            date_list = []
            success_data = []
            failed_data = []

            # 生成从 start_date 到 today 的日期列表
            current_date = start_date
            while current_date <= today:
                date_str = current_date.strftime('%Y-%m-%d')
                date_list.append(date_str)

                # 查询当天的构建数据
                day_start = datetime.combine(current_date, datetime.min.time())
                day_end = datetime.combine(current_date, datetime.max.time())

                # 成功构建数
                success_count = BuildHistory.objects.filter(
                    create_time__gte=day_start,
                    create_time__lte=day_end,
                    status='success'
                ).count()

                # 失败构建数
                failed_count = BuildHistory.objects.filter(
                    create_time__gte=day_start,
                    create_time__lte=day_end,
                    status='failed'
                ).count()

                success_data.append(success_count)
                failed_data.append(failed_count)

                current_date += timedelta(days=1)

            return JsonResponse({
                'code': 200,
                'message': '获取构建任务趋势数据成功',
                'data': {
                    'dates': date_list,
                    'success': success_data,
                    'failed': failed_data
                }
            })
        except Exception as e:
            logger.error(f'获取构建任务趋势数据失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })


@method_decorator(csrf_exempt, name='dispatch')
class BuildDetailView(View):
    """构建详细数据接口"""

    def get(self, request):
        """获取指定日期的构建详细数据"""
        try:
            # 获取日期参数
            date_str = request.GET.get('date')
            if not date_str:
                return JsonResponse({
                    'code': 400,
                    'message': '日期参数不能为空'
                })

            # 解析日期
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
                day_start = datetime(date.year, date.month, date.day, 0, 0, 0)
                day_end = datetime(date.year, date.month, date.day, 23, 59, 59)
            except ValueError:
                return JsonResponse({
                    'code': 400,
                    'message': '日期格式不正确，应为YYYY-MM-DD'
                })

            # 查询当天的构建历史
            builds = BuildHistory.objects.filter(
                create_time__gte=day_start,
                create_time__lte=day_end
            ).select_related('task', 'operator').order_by('-create_time')

            build_list = []
            for build in builds:
                # 计算构建耗时
                duration = '未完成'
                if build.build_time and 'total_duration' in build.build_time:
                    total_seconds = int(build.build_time.get('total_duration', 0))
                    minutes = total_seconds // 60
                    seconds = total_seconds % 60
                    duration = f"{minutes}分{seconds}秒"

                build_list.append({
                    'id': build.history_id,
                    'build_number': build.build_number,
                    'task_name': build.task.name,
                    'status': build.status,
                    'branch': build.branch,
                    'version': build.version,
                    'start_time': build.build_time.get('start_time') if build.build_time else build.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': duration,
                    'operator': build.operator.name if build.operator else '系统'
                })

            return JsonResponse({
                'code': 200,
                'message': '获取构建详细数据成功',
                'data': build_list
            })
        except Exception as e:
            logger.error(f'获取构建详细数据失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })


@method_decorator(csrf_exempt, name='dispatch')
class RecentBuildsView(View):
    """最近构建任务接口"""

    def get(self, request):
        """获取最近构建任务数据"""
        try:
            # 获取数量参数，默认为10条
            limit = int(request.GET.get('limit', 5))

            # 查询最近的构建历史
            recent_builds = BuildHistory.objects.select_related(
                'task', 'task__environment', 'operator'  # 关联环境信息
            ).order_by('-create_time')[:limit]

            build_list = []
            for build in recent_builds:
                # 计算构建耗时
                duration = '未完成'
                if build.build_time and 'total_duration' in build.build_time:
                    total_seconds = int(build.build_time.get('total_duration', 0))
                    minutes = total_seconds // 60
                    seconds = total_seconds % 60
                    duration = f"{minutes}分 {seconds}秒"

                build_list.append({
                    'id': build.history_id,
                    'build_number': build.build_number,
                    'task_name': build.task.name,
                    'status': build.status,
                    'branch': build.branch,
                    'version': build.version,
                    'environment': build.task.environment.name if build.task.environment else None, # 添加环境名称
                    'requirement': build.requirement,
                    'start_time': build.build_time.get('start_time') if build.build_time else build.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': duration,
                    'operator': build.operator.name if build.operator else '系统'
                })

            return JsonResponse({
                'code': 200,
                'message': '获取最近构建任务数据成功',
                'data': build_list
            })
        except Exception as e:
            logger.error(f'获取最近构建任务数据失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })


@method_decorator(csrf_exempt, name='dispatch')
class ProjectDistributionView(View):
    """项目分布接口"""

    def get(self, request):
        """获取项目分布数据"""
        try:
            # 按项目类别统计
            category_stats = Project.objects.values('category').annotate(count=Count('id'))

            # 格式化数据
            category_data = []
            for stat in category_stats:
                category = stat['category'] or '未分类'
                category_data.append({
                    'type': self._get_category_name(category),
                    'value': stat['count']
                })

            return JsonResponse({
                'code': 200,
                'message': '获取项目分布数据成功',
                'data': category_data
            })
        except Exception as e:
            logger.error(f'获取项目分布数据失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    def _get_category_name(self, category):
        """获取项目类别名称"""
        category_map = {
            'frontend': '前端项目',
            'backend': '后端项目',
            'mobile': '移动端项目',
            'other': '其他项目'
        }
        return category_map.get(category, '未分类')