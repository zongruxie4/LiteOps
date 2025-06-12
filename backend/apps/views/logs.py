import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.core.paginator import Paginator
from ..models import LoginLog, User
from ..utils.auth import jwt_auth_required

@csrf_exempt
@jwt_auth_required
@require_http_methods(["GET"])
def login_logs_list(request):
    """
    获取登录日志列表
    """
    try:
        # 获取查询参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        username = request.GET.get('username', '')
        status = request.GET.get('status', '')
        ip_address = request.GET.get('ip_address', '')
        start_time = request.GET.get('start_time', '')
        end_time = request.GET.get('end_time', '')
        
        # 构建查询条件
        query = Q()
        
        if username:
            users = User.objects.filter(username__icontains=username)
            query &= Q(user__in=users)
        
        if status:
            query &= Q(status=status)
            
        if ip_address:
            query &= Q(ip_address__icontains=ip_address)
            
        if start_time:
            query &= Q(login_time__gte=start_time)
            
        if end_time:
            query &= Q(login_time__lte=end_time)
        
        # 获取登录日志
        logs = LoginLog.objects.filter(query).select_related('user').order_by('-login_time')
        
        # 分页
        paginator = Paginator(logs, page_size)
        current_page = paginator.page(page)
        
        # 格式化返回数据
        log_list = []
        for log in current_page.object_list:
            log_data = {
                'log_id': log.log_id,
                'username': log.user.username if log.user else None,
                'user_id': log.user.user_id if log.user else None,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'status': log.status,
                'fail_reason': log.fail_reason,
                'login_time': log.login_time.strftime('%Y-%m-%d %H:%M:%S') if log.login_time else None
            }
            log_list.append(log_data)
        
        return JsonResponse({
            'code': 200,
            'message': '获取登录日志成功',
            'data': {
                'total': paginator.count,
                'page': page,
                'page_size': page_size,
                'logs': log_list
            }
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        })

@csrf_exempt
@jwt_auth_required
@require_http_methods(["GET"])
def login_log_detail(request, log_id):
    """
    获取登录日志详情
    """
    try:
        try:
            log = LoginLog.objects.select_related('user').get(log_id=log_id)
        except LoginLog.DoesNotExist:
            return JsonResponse({
                'code': 404,
                'message': '登录日志不存在'
            })
        
        log_data = {
            'log_id': log.log_id,
            'username': log.user.username if log.user else None,
            'user_id': log.user.user_id if log.user else None,
            'user_name': log.user.name if log.user else None,
            'ip_address': log.ip_address,
            'user_agent': log.user_agent,
            'status': log.status,
            'fail_reason': log.fail_reason,
            'login_time': log.login_time.strftime('%Y-%m-%d %H:%M:%S') if log.login_time else None
        }
        
        return JsonResponse({
            'code': 200,
            'message': '获取登录日志详情成功',
            'data': log_data
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }) 