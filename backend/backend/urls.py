from django.contrib import admin
from django.urls import path
from apps.views.login import login, logout
from apps.views.project import ProjectView, ProjectServiceView
from apps.views.environment import EnvironmentView, EnvironmentTypeView
from apps.views.credentials import CredentialView
from apps.views.gitlab import GitlabBranchView, GitlabCommitView
from apps.views.build import BuildTaskView, BuildExecuteView
from apps.views.build_history import BuildHistoryView, BuildLogView, BuildStageLogView
from apps.views.build_sse import BuildLogSSEView
from apps.views.notification import NotificationRobotView, NotificationTestView
from apps.views.user import UserView, UserProfileView
from apps.views.role import RoleView, UserPermissionView
from apps.views.logs import login_logs_list, login_log_detail
from apps.views.dashboard import DashboardStatsView, BuildTrendView, BuildDetailView, RecentBuildsView, ProjectDistributionView

from apps.views.security import SecurityConfigView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/login/', login, name='login'),
    path('api/logout/', logout, name='logout'),
    path('api/projects/', ProjectView.as_view(), name='projects'),
    path('api/project-services/', ProjectServiceView.as_view(), name='project-services'),
    path('api/environments/', EnvironmentView.as_view(), name='environments'),
    path('api/environments/types/', EnvironmentTypeView.as_view(), name='environment-types'),
    path('api/credentials/', CredentialView.as_view(), name='credentials'),
    path('api/gitlab/branches/', GitlabBranchView.as_view(), name='gitlab-branches'),
    path('api/gitlab/commits/', GitlabCommitView.as_view(), name='gitlab-commits'),
    path('api/build/tasks/', BuildTaskView.as_view(), name='build-tasks'),
    path('api/build/tasks/<str:task_id>/', BuildTaskView.as_view(), name='build-task-detail'),
    path('api/build/tasks/build', BuildExecuteView.as_view(), name='build-execute'),

    # 构建历史相关路由
    path('api/build/history/', BuildHistoryView.as_view(), name='build-history'),
    path('api/build/history/log/<str:history_id>/', BuildLogView.as_view(), name='build-log'),
    path('api/build/history/log/<str:history_id>/download/', BuildLogView.as_view(), name='build-log-download'),
    path('api/build/history/stage-log/<str:history_id>/<str:stage_name>/', BuildStageLogView.as_view(), name='build-stage-log'),
    
    # SSE构建日志流
    path('api/build/logs/stream/<str:task_id>/<str:build_number>/', BuildLogSSEView.as_view(), name='build-log-sse'),

    # 通知机器人相关路由
    path('api/notification/robots/', NotificationRobotView.as_view(), name='notification-robots'),
    path('api/notification/robots/test/', NotificationTestView.as_view(), name='notification-robot-test'),
    path('api/notification/robots/<str:robot_id>/', NotificationRobotView.as_view(), name='notification-robot-detail'),

    # 用户管理相关路由
    path('api/users/', UserView.as_view(), name='users'),
    path('api/roles/', RoleView.as_view(), name='roles'),
    path('api/user/permissions/', UserPermissionView.as_view(), name='user-permissions'),
    path('api/user/profile/', UserProfileView.as_view(), name='user-profile'),

    # 登录日志相关路由
    path('api/logs/login/', login_logs_list, name='login-logs'),
    path('api/logs/login/<str:log_id>/', login_log_detail, name='login-log-detail'),

    # 首页仪表盘相关路由
    path('api/dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('api/dashboard/build-trend/', BuildTrendView.as_view(), name='build-trend'),
    path('api/dashboard/build-detail/', BuildDetailView.as_view(), name='build-detail'),
    path('api/dashboard/recent-builds/', RecentBuildsView.as_view(), name='recent-builds'),
    path('api/dashboard/project-distribution/', ProjectDistributionView.as_view(), name='project-distribution'),

    # 安全配置相关路由
    path('api/system/security/', SecurityConfigView.as_view(), name='security-config'),
]
