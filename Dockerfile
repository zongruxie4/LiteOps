# =============================================================================
# LiteOps CI/CD Platform - Docker in Docker Multi-stage Dockerfile
# =============================================================================
# 第一阶段：构建和工具安装阶段
FROM debian:bullseye-slim AS builder

# 设置构建时的环境变量
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Java环境变量
    JAVA_HOME=/usr/local/java/jdk1.8.0_211 \
    MAVEN_HOME=/usr/local/maven/apache-maven-3.8.8 \
    # NVM环境变量
    NVM_DIR=/root/.nvm \
    # Docker版本
    DOCKER_VERSION=24.0.7

# =============================================================================
# 系统基础配置和轻量化软件安装
# =============================================================================
RUN set -eux; \
    # 配置阿里云镜像源以加速下载
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        # Python
        python3.9 \
        python3-pip \
        curl \
        ca-certificates \
        # SSH
        openssh-client \
        # Git（GitPython依赖）
        git \
        # 进程管理
        procps \
        bash \
        # Docker安装依赖
        apt-transport-https \
        gnupg \
        lsb-release \
        iptables \
        && \
    # 创建Python符号链接
    ln -sf /usr/bin/python3.9 /usr/bin/python3 && \
    ln -sf /usr/bin/python3.9 /usr/bin/python && \
    # 配置pip镜像源
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com && \
    # SSH客户端基础配置
    mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh && \
    # 安装NVM
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash && \
    echo 'export NVM_DIR="$HOME/.nvm"' >> /root/.bashrc && \
    echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"' >> /root/.bashrc && \
    echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" --no-use' >> /root/.profile && \
    # 创建Java和Maven安装目录
    mkdir -p /usr/local/java /usr/local/maven && \
    # 安装Docker Engine
    (curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
     echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://mirrors.aliyun.com/docker-ce/linux/debian bullseye stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null) || \
    (curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
     echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian bullseye stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null) && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        docker-ce-cli \
        docker-ce \
        && \
    apt-get autoremove -y && \
    apt-get autoclean && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/cache/apt/* /root/.cache/*

# =============================================================================
# Java环境安装
# =============================================================================
COPY jdk-8u211-linux-x64.tar.gz apache-maven-3.8.8-bin.tar.gz /tmp/

RUN set -eux; \
    # 解压JDK和Maven
    tar -xzf /tmp/jdk-8u211-linux-x64.tar.gz -C /usr/local/java && \
    tar -xzf /tmp/apache-maven-3.8.8-bin.tar.gz -C /usr/local/maven && \
    # 立即清理压缩包
    rm -f /tmp/jdk-8u211-linux-x64.tar.gz /tmp/apache-maven-3.8.8-bin.tar.gz && \
    # 删除所有不必要的文件
    cd /usr/local/java/jdk1.8.0_211 && \
    rm -rf src.zip javafx-src.zip man sample demo \
           COPYRIGHT LICENSE README.html THIRDPARTYLICENSEREADME.txt \
           release ASSEMBLY_EXCEPTION && \
    # 删除不常用的JDK工具
    cd bin && \
    rm -f appletviewer extcheck jarsigner java-rmi.cgi \
          javadoc javah javap javaws jcmd jconsole jdb jhat \
          jinfo jmap jps jrunscript jsadebugd jstack jstat \
          jstatd jvisualvm native2ascii orbd policytool \
          rmic rmid rmiregistry schemagen serialver servertool \
          tnameserv wsgen wsimport xjc && \
    # 删除JRE中的不必要文件
    cd ../jre && \
    rm -rf COPYRIGHT LICENSE README THIRDPARTYLICENSEREADME.txt \
           ASSEMBLY_EXCEPTION release && \
    cd bin && \
    rm -f javaws jvisualvm orbd policytool rmid \
          rmiregistry servertool tnameserv && \
    # Maven安装，删除文档和示例
    cd /usr/local/maven/apache-maven-3.8.8 && \
    rm -rf LICENSE NOTICE README.txt

# =============================================================================
# 第二阶段：超轻量运行时镜像
# =============================================================================
FROM debian:bullseye-slim

# 设置运行时环境变量
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Java环境变量
    JAVA_HOME=/usr/local/java/jdk1.8.0_211 \
    MAVEN_HOME=/usr/local/maven/apache-maven-3.8.8 \
    # NVM环境变量
    NVM_DIR=/root/.nvm \
    # Docker版本
    DOCKER_VERSION=24.0.7 \
    # Locale配置 - 使用POSIX避免SSH locale警告
    LC_ALL=POSIX \
    LANG=POSIX \
    # 更新PATH环境变量
    PATH=/usr/local/java/jdk1.8.0_211/bin:/usr/local/maven/apache-maven-3.8.8/bin:/usr/local/bin:/usr/local/sbin:$PATH

# =============================================================================
# 运行时最小化系统配置
# =============================================================================
RUN set -eux; \
    # 配置阿里云镜像源
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    # 只安装绝对必需的运行时包
    apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.9 \
        python3-pip \
        curl \
        ca-certificates \
        # SSH
        openssh-client \
        # Git（GitPython依赖）
        git \
        # 轻量web服务器
        nginx-light \
        # 进程管理
        procps \
        bash \
        # Docker运行时依赖
        apt-transport-https \
        gnupg \
        lsb-release \
        iptables \
        && \
    # 创建Python符号链接
    ln -sf /usr/bin/python3.9 /usr/bin/python3 && \
    ln -sf /usr/bin/python3.9 /usr/bin/python && \
    # 配置pip镜像源
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com && \
    # 安装Docker Engine
    (curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
     echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://mirrors.aliyun.com/docker-ce/linux/debian bullseye stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null) || \
    (curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
     echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian bullseye stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null) && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        docker-ce-cli \
        docker-ce \
        && \
    # 安装kubectl - 使用官方二进制文件
    KUBECTL_VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt) && \
    curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/ && \
    # 创建必要的目录
    mkdir -p /app/logs && \
    rm -rf /var/log/nginx/* /var/lib/nginx/body /var/lib/nginx/fastcgi \
           /var/lib/nginx/proxy /var/lib/nginx/scgi /var/lib/nginx/uwsgi \
           /etc/nginx/sites-enabled/default && \
    apt-get autoremove -y && \
    apt-get autoclean && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/cache/apt/* /root/.cache/* \
           /var/cache/debconf/* /var/lib/dpkg/info/* /usr/share/doc/* \
           /usr/share/man/* /usr/share/locale/* /usr/share/info/*

# =============================================================================
# 从构建阶段复制文件
# =============================================================================
# 复制SSH配置
COPY --from=builder /root/.ssh /root/.ssh

# 复制NVM环境
COPY --from=builder /root/.nvm /root/.nvm
COPY --from=builder /root/.bashrc /root/.bashrc
COPY --from=builder /root/.profile /root/.profile

# 复制Java环境
COPY --from=builder /usr/local/java /usr/local/java
COPY --from=builder /usr/local/maven /usr/local/maven

# Docker已在运行时阶段安装，无需复制

# =============================================================================
# 应用程序配置
# =============================================================================
# 设置工作目录
WORKDIR /app

# 配置Nginx - 复制自定义配置文件
COPY nginx.conf /etc/nginx/sites-available/default
RUN ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# 复制前端构建文件到Nginx静态文件目录
COPY web/dist/ /usr/share/nginx/html/

# Python依赖安装
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt && \
    # 清理pip缓存和不必要的文件
    rm -rf /root/.cache/pip /tmp/* && \
    # 移除pip的缓存目录
    pip cache purge 2>/dev/null || true

# 复制后端应用代码
COPY backend/ /app/

# 复制启动脚本并设置执行权限
COPY docker-entrypoint.sh /app/
COPY ci-entrypoint-dind.sh /usr/local/bin/
RUN chmod +x /app/docker-entrypoint.sh /usr/local/bin/ci-entrypoint-dind.sh

# =============================================================================
# 容器配置
# =============================================================================
# 暴露端口
# 80: Nginx Web服务器端口
# 8900: Django后端API端口
EXPOSE 80 8900

# 设置容器入口点和默认命令
ENTRYPOINT ["/usr/local/bin/ci-entrypoint-dind.sh"]
CMD ["/app/docker-entrypoint.sh"]