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

# 等待MySQL就绪的函数
wait_for_mysql() {
    local max_attempts=30
    local attempt=1
    
    print_info "等待MySQL服务完全启动..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec $MYSQL_CONTAINER mysqladmin ping -uroot -p$MYSQL_PASSWORD --silent >/dev/null 2>&1; then
            print_success "MySQL服务已就绪 (尝试次数: $attempt)"
            return 0
        fi
        
        print_info "MySQL还未就绪，等待中... (尝试 $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "MySQL在 $((max_attempts * 2)) 秒内未能就绪"
    return 1
}

# 导入SQL文件的函数
import_sql_with_retry() {
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        print_info "尝试导入初始化数据 (尝试 $attempt/$max_attempts)..."
        
        if docker exec -i $MYSQL_CONTAINER mysql -uroot -p$MYSQL_PASSWORD liteops < liteops_init.sql; then
            print_success "初始化数据导入成功"
            return 0
        else
            print_warning "初始化数据导入失败，尝试 $attempt/$max_attempts"
            if [ $attempt -lt $max_attempts ]; then
                print_info "等待5秒后重试..."
                sleep 5
            fi
            attempt=$((attempt + 1))
        fi
    done
    
    print_error "初始化数据导入失败，已尝试 $max_attempts 次"
    return 1
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

# 等待MySQL完全就绪
if ! wait_for_mysql; then
    print_error "MySQL启动失败，退出部署"
    exit 1
fi

# 初始化数据库
print_step "初始化数据库"
if ! import_sql_with_retry; then
    print_error "数据库初始化失败，退出部署"
    exit 1
fi
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