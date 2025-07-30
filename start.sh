#!/bin/bash

# =============================================================================
# LiteOps 一键启动脚本
# =============================================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # 无颜色

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

# 端口检查函数
check_port() {
    local port=$1
    local service_name=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_error "端口 $port 已被占用！"
        print_info "检查占用进程："
        
        # 显示占用进程的详细信息
        local pid=$(lsof -Pi :$port -sTCP:LISTEN -t 2>/dev/null | head -1)
        if [ ! -z "$pid" ]; then
            local process_info=$(ps -p $pid -o pid,ppid,cmd --no-headers 2>/dev/null)
            if [ ! -z "$process_info" ]; then
                echo -e "  ${CYAN}PID${NC}: $pid"
                echo -e "  ${CYAN}进程${NC}: $process_info"
            fi
        fi
        
        print_warning "解决方案："
        echo -e "  1. 停止占用端口的进程: ${CYAN}kill $pid${NC}"
        echo -e "  2. 或使用强制停止: ${CYAN}kill -9 $pid${NC}"
        echo -e "  3. 或查看所有占用进程: ${CYAN}lsof -i :$port${NC}"
        echo ""
        return 1
    else
        print_info "端口 $port ($service_name) 可用"
        return 0
    fi
}

# 全局变量
BACKEND_PID=""
FRONTEND_PID=""
BACKEND_PORT=8900
FRONTEND_PORT=8000

# 清理函数
cleanup() {
    print_step "正在清理进程..."
    
    if [ ! -z "$BACKEND_PID" ]; then
        print_info "停止后端服务 (PID: $BACKEND_PID)"
        kill $BACKEND_PID 2>/dev/null || true
        wait $BACKEND_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        print_info "停止前端服务 (PID: $FRONTEND_PID)"
        kill $FRONTEND_PID 2>/dev/null || true
        wait $FRONTEND_PID 2>/dev/null || true
    fi
    
    # 清理可能残留的端口占用进程
    if command -v lsof &> /dev/null; then
        print_info "清理端口占用..."
        lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null || true
        lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
    else
        print_info "跳过端口清理（lsof命令不可用）"
    fi
    
    print_success "清理完成"
    exit 0
}

# 注册信号处理
trap cleanup SIGTERM SIGINT

# 检查环境
print_step "检查环境"

# 检查Python
if ! command -v python3 &> /dev/null; then
    print_error "Python3 未安装或不在PATH中"
    exit 1
fi

# 检查Node.js和npm
if ! command -v node &> /dev/null; then
    print_error "Node.js 未安装或不在PATH中"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    print_error "npm 未安装或不在PATH中"
    exit 1
fi

# 检查项目结构
if [ ! -d "backend" ]; then
    print_error "backend 目录不存在，请确保在项目根目录运行此脚本"
    exit 1
fi

if [ ! -d "web" ]; then
    print_error "web 目录不存在，请确保在项目根目录运行此脚本"
    exit 1
fi

print_success "环境检查通过"

# 检查端口占用
print_step "检查端口占用"

# 检查是否有lsof命令
if ! command -v lsof &> /dev/null; then
    print_warning "未检测到lsof命令，跳过端口检查"
    print_info "如需端口检查功能，请安装lsof："
    echo -e "  ${CYAN}macOS${NC}: brew install lsof"
    echo -e "  ${CYAN}Ubuntu/Debian${NC}: sudo apt-get install lsof"
    echo -e "  ${CYAN}CentOS/RHEL${NC}: sudo yum install lsof"
else
    if ! check_port $BACKEND_PORT "后端服务"; then
        exit 1
    fi

    if ! check_port $FRONTEND_PORT "前端服务"; then
        exit 1
    fi

    print_success "端口检查通过"
fi

# 检查后端依赖
print_step "检查后端依赖"
if [ ! -f "backend/requirements.txt" ]; then
    print_error "backend/requirements.txt 不存在"
    exit 1
fi

cd backend
if ! python3 -c "import uvicorn, django" &> /dev/null; then
    print_warning "后端依赖未完整安装，开始安装..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        print_error "后端依赖安装失败"
        exit 1
    fi
    print_success "后端依赖安装完成"
else
    print_success "后端依赖已安装"
fi
cd ..

# 检查前端依赖
print_step "检查前端依赖"
cd web
if [ ! -d "node_modules" ]; then
    print_warning "前端依赖未安装，开始安装..."
    npm install
    if [ $? -ne 0 ]; then
        print_error "前端依赖安装失败"
        exit 1
    fi
    print_success "前端依赖安装完成"
else
    print_success "前端依赖已安装"
fi
cd ..

# 启动后端服务
print_step "启动后端服务"
cd backend
print_info "启动后端服务在端口$BACKEND_PORT..."
python3 -m uvicorn backend.asgi:application --host 0.0.0.0 --port $BACKEND_PORT &
BACKEND_PID=$!
cd ..

# 等待后端启动
print_info "等待后端服务启动..."
sleep 3

# 检查后端是否启动成功
if kill -0 $BACKEND_PID 2>/dev/null; then
    print_success "后端服务启动成功 (PID: $BACKEND_PID)"
else
    print_error "后端服务启动失败"
    exit 1
fi

# 启动前端服务
print_step "启动前端服务"
cd web
print_info "启动前端开发服务器在端口$FRONTEND_PORT..."
npm run dev &
FRONTEND_PID=$!
cd ..

# 等待前端启动
print_info "等待前端服务启动..."
sleep 3

# 检查前端是否启动成功
if kill -0 $FRONTEND_PID 2>/dev/null; then
    print_success "前端服务启动成功 (PID: $FRONTEND_PID)"
else
    print_error "前端服务启动失败"
    cleanup
    exit 1
fi

# 启动完成
print_step "启动完成"
print_success "LiteOps 开发环境已成功启动！"
echo ""
print_info "访问地址："
echo -e "  ${CYAN}前端界面${NC}: http://localhost:$FRONTEND_PORT"
echo -e "  ${CYAN}后端API${NC}: http://localhost:$BACKEND_PORT"
echo ""
print_info "默认登录信息："
echo -e "  ${CYAN}用户名${NC}: admin"
echo -e "  ${CYAN}密码${NC}: admin123"
echo ""
print_warning "按 Ctrl+C 停止所有服务"

# 等待信号
while true; do
    # 检查进程是否还在运行
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        print_error "后端服务意外停止"
        cleanup
        exit 1
    fi
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        print_error "前端服务意外停止"
        cleanup
        exit 1
    fi
    
    sleep 5
done
