#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Docker in Docker (DinD) 启动脚本 - 轻量级CI/CD版本
# =============================================================================

echo "🐳 启动 Docker in Docker 环境..."

# 检测是否为容器重启
RESTART_FLAG="/tmp/.docker-restart-flag"
if [ -f "$RESTART_FLAG" ]; then
    echo "🔄 检测到容器重启，执行清理..."
    CONTAINER_RESTART=true
else
    echo "🆕 首次启动容器"
    CONTAINER_RESTART=false
    touch "$RESTART_FLAG"
fi

# 检查是否在特权模式下运行
if [ ! -w /sys/fs/cgroup ]; then
    echo "❌ 错误: 容器必须在特权模式下运行才能使用 Docker in Docker"
    echo "请使用 --privileged 参数启动容器"
    exit 1
fi

# 确保必要的内核模块和设备
modprobe overlay 2>/dev/null || true
modprobe br_netfilter 2>/dev/null || true

# 创建必要的设备节点
if [ ! -e /dev/fuse ]; then
    mknod /dev/fuse c 10 229 2>/dev/null || true
fi

# 创建必要的目录
mkdir -p /var/lib/docker
mkdir -p /var/run/docker
mkdir -p /etc/docker

# 配置轻量级Docker daemon - 使用vfs存储驱动确保兼容性
cat > /etc/docker/daemon.json << 'EOF'
{
    "storage-driver": "vfs",
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "2"
    },
    "registry-mirrors": [
        "https://mirrors.aliyun.com/docker-hub",
        "https://docker.mirrors.ustc.edu.cn",
        "https://hub-mirror.c.163.com"
    ],
    "insecure-registries": [],
    "exec-opt": ["native.cgroupdriver=cgroupfs"],
    "max-concurrent-downloads": 3,
    "max-concurrent-uploads": 3,
    "live-restore": false
}
EOF

# 启动轻量级Docker daemon
echo "🚀 启动 Docker daemon (轻量级CI/CD模式)..."

# 清理存在的旧进程和文件
echo "🧹 清理旧的Docker进程和文件..."
# 停止所有Docker相关进程
pkill -f dockerd 2>/dev/null || true
pkill -f containerd 2>/dev/null || true
pkill -f docker-proxy 2>/dev/null || true

# 等待进程完全停止
sleep 2

# 强制清理残留进程
pkill -9 -f dockerd 2>/dev/null || true
pkill -9 -f containerd 2>/dev/null || true
pkill -9 -f docker-proxy 2>/dev/null || true

# 清理所有相关文件和socket
rm -f /var/run/docker.sock /var/run/docker.pid 2>/dev/null || true
rm -f /var/run/containerd/containerd.sock 2>/dev/null || true
rm -f /var/run/containerd/containerd.pid 2>/dev/null || true
rm -rf /var/run/containerd/* 2>/dev/null || true

# 清理可能的锁文件
rm -f /var/lib/docker/.docker-lock 2>/dev/null || true
rm -f /var/lib/containerd/io.containerd.metadata.v1.bolt/meta.db-lock 2>/dev/null || true

# 重新创建必要的目录
mkdir -p /var/run/containerd
mkdir -p /var/lib/containerd

# 启动dockerd 
dockerd \
    --host=unix:///var/run/docker.sock \
    --userland-proxy=false \
    --experimental=false \
    --iptables=false \
    --ip-forward=false \
    --pidfile=/var/run/docker.pid \
    --tls=false \
    --log-level=warn &

# 记录dockerd进程ID
DOCKERD_PID=$!

# 等待Docker daemon启动
echo "⏳ 等待 Docker daemon 启动..."
timeout=60
while [ $timeout -gt 0 ]; do
    # 检查socket文件是否存在
    if [ -S /var/run/docker.sock ]; then
        # 尝试连接Docker daemon
        if docker version >/dev/null 2>&1; then
            echo "✅ Docker daemon 启动成功"
            break
        fi
    fi

    # 检查dockerd进程是否还在运行
    if ! kill -0 $DOCKERD_PID 2>/dev/null; then
        echo "❌ Docker daemon 进程意外退出"
        echo "检查最近的错误日志:"
        dmesg | tail -5 2>/dev/null || echo "无法获取系统日志"
        exit 1
    fi

    sleep 1
    timeout=$((timeout - 1))
done

if [ $timeout -eq 0 ]; then
    echo "❌ Docker daemon 启动超时"
    echo "检查dockerd进程状态:"
    ps aux | grep dockerd || true
    echo "检查socket文件:"
    ls -la /var/run/docker.sock 2>/dev/null || echo "socket文件不存在"
    exit 1
fi

# 简单验证Docker功能
echo "🔍 验证 Docker 功能..."
DOCKER_VERSION=$(docker version --format '{{.Server.Version}}' 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "✅ Docker daemon 版本: $DOCKER_VERSION"
    echo "✅ 存储驱动: $(docker info --format '{{.Driver}}' 2>/dev/null || echo 'unknown')"
else
    echo "❌ Docker daemon 验证失败"
    exit 1
fi

# 设置环境变量
export DOCKER_HOST=unix:///var/run/docker.sock
export DOCKER_BUILDKIT=1

echo "🎉 Docker in Docker 环境启动完成 (轻量级CI/CD模式)"

# 设置清理函数
cleanup() {
    echo "🧹 清理 Docker daemon..."
    if [ -n "$DOCKERD_PID" ] && kill -0 $DOCKERD_PID 2>/dev/null; then
        kill $DOCKERD_PID
        wait $DOCKERD_PID 2>/dev/null || true
    fi
    exit 0
}

# 注册信号处理
trap cleanup SIGTERM SIGINT

# 执行传入的命令
exec "$@"
