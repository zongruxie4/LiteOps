import threading
import queue
import time
import logging
from typing import Dict, Set, Optional
from dataclasses import dataclass

logger = logging.getLogger('apps')

@dataclass
class LogMessage:
    """日志消息数据类"""
    task_id: str
    build_number: int
    message: str
    stage: Optional[str] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class LogStreamManager:
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        # 存储每个构建的日志队列 {(task_id, build_number): queue.Queue}
        self._log_queues: Dict[tuple, queue.Queue] = {}
        # 存储每个构建的SSE客户端集合 {(task_id, build_number): set}
        self._sse_clients: Dict[tuple, Set] = {}
        # 线程锁
        self._queues_lock = threading.Lock()
        self._clients_lock = threading.Lock()
        
        logger.info("LogStreamManager initialized")
    
    def get_build_key(self, task_id: str, build_number: int) -> tuple:
        """获取构建的唯一键"""
        return (task_id, build_number)
    
    def create_build_stream(self, task_id: str, build_number: int):
        """为新构建创建日志流"""
        build_key = self.get_build_key(task_id, build_number)
        
        with self._queues_lock:
            if build_key not in self._log_queues:
                self._log_queues[build_key] = queue.Queue(maxsize=20000)  # 最大缓存20000条日志
                logger.info(f"Created log stream for build {task_id}#{build_number}")
        
        with self._clients_lock:
            if build_key not in self._sse_clients:
                self._sse_clients[build_key] = set()
    
    def add_sse_client(self, task_id: str, build_number: int, client_id: str):
        """添加SSE客户端"""
        build_key = self.get_build_key(task_id, build_number)
        
        with self._clients_lock:
            if build_key not in self._sse_clients:
                self._sse_clients[build_key] = set()
            self._sse_clients[build_key].add(client_id)
            logger.info(f"Added SSE client {client_id} for build {task_id}#{build_number}")
    
    def remove_sse_client(self, task_id: str, build_number: int, client_id: str):
        """移除SSE客户端"""
        build_key = self.get_build_key(task_id, build_number)
        
        with self._clients_lock:
            if build_key in self._sse_clients:
                self._sse_clients[build_key].discard(client_id)
                logger.info(f"Removed SSE client {client_id} for build {task_id}#{build_number}")
                
                if not self._sse_clients[build_key]:
                    del self._sse_clients[build_key]
                    self._cleanup_build_stream(build_key)
    
    def _cleanup_build_stream(self, build_key: tuple):
        """清理构建流资源"""
        with self._queues_lock:
            if build_key in self._log_queues:
                del self._log_queues[build_key]
                logger.info(f"Cleaned up log stream for build {build_key[0]}#{build_key[1]}")
    
    def push_log(self, task_id: str, build_number: int, message: str, stage: Optional[str] = None):
        """推送日志消息到流"""
        build_key = self.get_build_key(task_id, build_number)
        
        # 创建日志消息
        log_msg = LogMessage(
            task_id=task_id,
            build_number=build_number,
            message=message,
            stage=stage
        )
        
        # 推送到队列
        with self._queues_lock:
            if build_key not in self._log_queues:
                # 如果队列不存在，先创建
                self._log_queues[build_key] = queue.Queue(maxsize=20000)
                logger.debug(f"Created log queue for build {task_id}#{build_number} during push")
            
            try:
                # 非阻塞推送，如果队列满了就丢弃最老的消息
                if self._log_queues[build_key].full():
                    try:
                        self._log_queues[build_key].get_nowait()  # 移除最老的消息
                    except queue.Empty:
                        pass
                
                self._log_queues[build_key].put_nowait(log_msg)
            except queue.Full:
                logger.warning(f"Log queue full for build {task_id}#{build_number}, dropping message")
    
    def get_log_stream(self, task_id: str, build_number: int, client_id: str):
        """获取日志流生成器"""
        build_key = self.get_build_key(task_id, build_number)
        
        # 确保流存在
        self.create_build_stream(task_id, build_number)
        self.add_sse_client(task_id, build_number, client_id)
        
        try:
            while True:
                try:
                    # 检查客户端是否还在连接
                    with self._clients_lock:
                        if build_key not in self._sse_clients or client_id not in self._sse_clients[build_key]:
                            logger.info(f"Client {client_id} disconnected from build {task_id}#{build_number}")
                            break
                    
                    # 获取日志队列
                    with self._queues_lock:
                        log_queue = self._log_queues.get(build_key)
                    
                    if log_queue is None:
                        break
                    
                    try:
                        # 等待新日志消息，超时时间为1秒
                        log_msg = log_queue.get(timeout=1.0)
                        yield log_msg
                    except queue.Empty:
                        # 超时，发送心跳
                        yield None  # None表示心跳
                        
                except Exception as e:
                    logger.error(f"Error in log stream for {task_id}#{build_number}: {str(e)}")
                    break
        finally:
            # 清理客户端
            self.remove_sse_client(task_id, build_number, client_id)
    
    def complete_build(self, task_id: str, build_number: int, status: str):
        """标记构建完成"""
        build_key = self.get_build_key(task_id, build_number)
        
        # 推送完成消息
        completion_msg = LogMessage(
            task_id=task_id,
            build_number=build_number,
            message=f"BUILD_COMPLETE:{status}",
            stage="SYSTEM"
        )
        
        with self._queues_lock:
            if build_key in self._log_queues:
                try:
                    self._log_queues[build_key].put_nowait(completion_msg)
                except queue.Full:
                    pass
    
    def has_active_clients(self, task_id: str, build_number: int) -> bool:
        """检查是否有活跃的SSE客户端"""
        build_key = self.get_build_key(task_id, build_number)
        
        with self._clients_lock:
            return build_key in self._sse_clients and len(self._sse_clients[build_key]) > 0

# 全局单例实例
log_stream_manager = LogStreamManager() 