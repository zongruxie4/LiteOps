#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # 无颜色

# 设置变量
CONTAINER_IMAGE="liteops:v1"
CONTAINER_NAME="liteops"
MYSQL_CONTAINER="liteops-mysql"
MYSQL_VERSION="8"
MYSQL_PASSWORD="1234567xx"
MYSQL_PORT="3306"
NETWORK_NAME="liteops-network"

# 打印带颜色的信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "\n${PURPLE}=== $1 ===${NC}"
}

# 创建Docker网络（如果不存在）
print_step "创建Docker网络"
if ! docker network inspect $NETWORK_NAME >/dev/null 2>&1; then
    print_info "创建Docker网络: $NETWORK_NAME"
    docker network create $NETWORK_NAME
    print_success "网络创建成功"
else
    print_info "网络 $NETWORK_NAME 已存在，跳过创建"
fi

# 停止并删除已存在的容器
print_step "清理已存在的容器"
print_info "停止并删除已存在的容器..."
docker stop $CONTAINER_NAME $MYSQL_CONTAINER 2>/dev/null || true
docker rm $CONTAINER_NAME $MYSQL_CONTAINER 2>/dev/null || true
print_success "容器清理完成"

# 构建镜像
print_step "构建应用镜像"
print_info "构建LiteOps镜像..."
# 确保前端已经构建
if [ ! -d "web/dist" ]; then
    print_error "前端dist目录不存在，请先运行 npm run build"
    exit 1
fi
docker build --platform linux/amd64 -t $CONTAINER_IMAGE .
print_success "镜像构建成功: $CONTAINER_IMAGE"

# 启动MySQL容器
print_step "启动MySQL容器"
print_info "启动MySQL $MYSQL_VERSION 容器..."
docker run -d \
    --name $MYSQL_CONTAINER \
    --network $NETWORK_NAME \
    -p $MYSQL_PORT:3306 \
    -e MYSQL_ROOT_PASSWORD=$MYSQL_PASSWORD \
    -e MYSQL_DATABASE=liteops \
    mysql:$MYSQL_VERSION

# 等待MySQL启动
print_info "等待MySQL启动..."
sleep 10

# 初始化数据库
print_step "初始化数据库"
print_info "导入初始数据..."
docker exec -i $MYSQL_CONTAINER mysql -uroot -p$MYSQL_PASSWORD liteops < liteops_init.sql
print_success "数据库初始化完成"

# 启动应用容器
print_step "启动应用容器"
print_info "启动LiteOps容器（Docker in Docker模式）..."
docker run -d \
    --name $CONTAINER_NAME \
    --network $NETWORK_NAME \
    --privileged \
    -p 80:80 \
    -p 8900:8900 \
    $CONTAINER_IMAGE

print_step "部署完成"
print_success "LiteOps已成功部署！"
print_info "前端访问地址: ${CYAN}http://localhost${NC}"
print_info "后端API地址: ${CYAN}http://localhost:8900/api/${NC}"
print_info "MySQL端口映射: ${CYAN}$MYSQL_PORT${NC}"