import json
import time
import logging
import uuid
import threading
import queue
import asyncio
from django.http import StreamingHttpResponse, JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import sync_to_async
from ..utils.auth import jwt_auth_required
from ..utils.log_stream import log_stream_manager
from ..models import BuildHistory, UserToken

logger = logging.getLogger('apps')

@method_decorator(csrf_exempt, name='dispatch')
class BuildLogSSEView(View):
    """构建日志SSE流视图 - 异步实现以支持ASGI环境"""
    
    def options(self, request, task_id, build_number):
        """处理CORS预检请求"""
        response = JsonResponse({})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Cache-Control, Authorization'
        response['Access-Control-Max-Age'] = '86400'  # 24小时
        return response
    
    def get(self, request, task_id, build_number):
        """获取构建日志SSE流"""
        try:
            # 从URL参数获取token进行认证
            token = request.GET.get('token')
            if not token:
                return StreamingHttpResponse(
                    self._create_error_stream("缺少认证token"),
                    content_type='text/event-stream'
                )
            
            # 验证token
            try:
                user_info = self._verify_jwt_token(token)
                if not user_info:
                    return StreamingHttpResponse(
                        self._create_error_stream("无效的认证token"),
                        content_type='text/event-stream'
                    )
            except Exception as e:
                logger.error(f"Token验证失败: {str(e)}", exc_info=True)
                return StreamingHttpResponse(
                    self._create_error_stream("认证失败"),
                    content_type='text/event-stream'
                )
            
            # 验证构建历史记录是否存在
            try:
                history = BuildHistory.objects.get(
                    task__task_id=task_id,
                    build_number=int(build_number)
                )
            except BuildHistory.DoesNotExist:
                return StreamingHttpResponse(
                    self._create_error_stream("构建记录不存在"),
                    content_type='text/event-stream'
                )
            except ValueError:
                return StreamingHttpResponse(
                    self._create_error_stream("无效的构建号"),
                    content_type='text/event-stream'
                )
            
            # 创建异步SSE流
            response = StreamingHttpResponse(
                self._build_log_stream_async(task_id, int(build_number), history),
                content_type='text/event-stream'
            )
            
            # 设置SSE相关的HTTP头
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Headers'] = 'Cache-Control'
            response['Access-Control-Allow-Methods'] = 'GET'
            response['X-Accel-Buffering'] = 'no'  # 禁用nginx缓冲
            
            return response
            
        except Exception as e:
            logger.error(f"创建SSE流失败: {str(e)}", exc_info=True)
            return StreamingHttpResponse(
                self._create_error_stream(f"服务器错误: {str(e)}"),
                content_type='text/event-stream'
            )
    
    def _verify_jwt_token(self, token):
        """验证JWT token"""
        try:
            import jwt
            from django.conf import settings
            
            # 查询用户token
            user_token = UserToken.objects.filter(token=token).first()
            
            if not user_token:
                logger.warning("Token不存在于数据库中")
                return None
            
            # 验证JWT token
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                return {
                    'user_id': payload.get('user_id'),
                    'username': payload.get('username')
                }
            except jwt.ExpiredSignatureError:
                logger.warning("Token已过期")
                return None
            except jwt.InvalidTokenError as e:
                logger.warning(f"Token无效: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Token验证过程发生错误: {str(e)}", exc_info=True)
            return None
    
    async def _build_log_stream_async(self, task_id, build_number, history):
        """异步生成构建日志流"""
        # 生成唯一的客户端ID
        client_id = str(uuid.uuid4())
        
        try:
            # 发送连接建立消息
            yield self._format_sse_message({
                'type': 'connection_established',
                'message': '连接成功，开始接收构建日志...'
            })
            
            # 如果构建已完成，发送完成消息并结束
            if history.status in ['success', 'failed', 'terminated']:
                yield self._format_sse_message({
                    'type': 'build_complete',
                    'status': history.status,
                    'message': f'构建已完成，状态: {history.status}。请使用历史日志API获取完整日志。'
                })
                return
            
            # 对于正在进行的构建，使用实时日志流
            heartbeat_counter = 0
            
            # 获取异步日志流
            async for log_msg in self._async_log_stream(task_id, build_number, client_id):
                if log_msg is None:
                    # 心跳包
                    heartbeat_counter += 1
                    if heartbeat_counter >= 30:  # 每30秒发送一次心跳
                        yield self._format_sse_message({
                            'type': 'heartbeat',
                            'timestamp': int(time.time())
                        }, event_type='heartbeat')
                        heartbeat_counter = 0
                    continue
                
                # 重置心跳计数器
                heartbeat_counter = 0
                
                # 检查是否是构建完成消息
                if log_msg.message.startswith('BUILD_COMPLETE:'):
                    status = log_msg.message.split(':', 1)[1]
                    yield self._format_sse_message({
                        'type': 'build_complete',
                        'status': status,
                        'message': f'构建已完成，状态: {status}'
                    })
                    break
                else:
                    # 普通日志消息
                    yield self._format_sse_message({
                        'type': 'build_log',
                        'message': log_msg.message
                    })
                
        except Exception as e:
            logger.error(f"生成构建日志流时发生错误: {str(e)}", exc_info=True)
            yield self._format_sse_message({
                'type': 'error',
                'message': f'日志流发生错误: {str(e)}'
            })
    
    async def _async_log_stream(self, task_id, build_number, client_id):
        """异步日志流生成器 - 改进版本"""
        try:
            async_queue = asyncio.Queue(maxsize=1000)  # 限制队列大小
            stop_event = asyncio.Event()
            loop = asyncio.get_running_loop()
            
            def sync_log_reader():
                """在单独线程中读取同步日志流"""
                try:
                    for log_msg in log_stream_manager.get_log_stream(task_id, build_number, client_id):
                        if stop_event.is_set():
                            break
                        
                        # 使用线程安全的方式添加到异步队列
                        try:
                            asyncio.run_coroutine_threadsafe(
                                async_queue.put(log_msg), loop
                            ).result(timeout=0.1)
                        except Exception as queue_error:
                            logger.debug(f"队列添加失败，可能客户端已断开: {queue_error}")
                            break
                    
                    # 发送结束信号
                    try:
                        asyncio.run_coroutine_threadsafe(
                            async_queue.put(StopAsyncIteration), loop
                        ).result(timeout=0.1)
                    except Exception:
                        pass  # 忽略结束信号发送失败
                        
                except Exception as e:
                    logger.error(f"同步日志读取器出错: {str(e)}", exc_info=True)
                    try:
                        asyncio.run_coroutine_threadsafe(
                            async_queue.put(StopAsyncIteration), loop
                        ).result(timeout=0.1)
                    except Exception:
                        pass
            
            # 在线程池中启动同步日志读取器
            thread = threading.Thread(target=sync_log_reader, daemon=True)
            thread.start()
            
            try:
                while True:
                    try:
                        # 异步等待日志消息，使用较短的超时以提供更好的响应性
                        log_msg = await asyncio.wait_for(async_queue.get(), timeout=1.0)
                        
                        if log_msg is StopAsyncIteration:
                            break
                        
                        yield log_msg
                        
                    except asyncio.TimeoutError:
                        # 超时，发送心跳
                        yield None
                        
            finally:
                # 设置停止事件，清理资源
                stop_event.set()
                if thread.is_alive():
                    thread.join(timeout=2.0)  # 增加join超时时间
                
        except Exception as e:
            logger.error(f"异步日志流错误: {str(e)}", exc_info=True)
            yield None  # 确保生成器正常结束
    
    def _create_error_stream(self, error_message):
        """创建错误流"""
        yield self._format_sse_message({
            'type': 'error',
            'message': error_message
        })
    
    def _format_sse_message(self, data, event_type='message'):
        """格式化SSE消息"""
        message = f"event: {event_type}\n"
        message += f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        return message 