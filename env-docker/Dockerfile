FROM ubuntu:22.04

# 避免交互式提示
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# 设置DNS环境变量
ENV RES_OPTIONS="timeout:1 attempts:5 rotate single-request-reopen"

# 使用清华大学镜像源
RUN rm -rf /etc/apt/sources.list && \
    echo "deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy main restricted universe multiverse" > /etc/apt/sources.list && \
    echo "deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-backports main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-security main restricted universe multiverse" >> /etc/apt/sources.list

# 安装基本工具
RUN apt-get update && apt-get install -y \
    supervisor \
    bash-completion \
    vim \
    nano \
    less \
    curl \
    wget \
    jq \
    iproute2 \
    iputils-ping \
    netcat-openbsd \
    dnsutils \
    openssl \
    ca-certificates \
    tzdata \
    python3-venv \
    python3-pip \
    git \
    sudo \
    gnupg \
    lsb-release \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装OpenStack组件和依赖
RUN apt-get update && apt-get install -y software-properties-common gnupg \
    && add-apt-repository cloud-archive:zed -y \
    && apt-get update \
    && apt-get install -y \
    # 数据库
    mysql-server python3-pymysql \
    # 消息队列
    rabbitmq-server \
    # 缓存
    memcached python3-memcache \
    # OpenStack客户端
    python3-openstackclient \
    # Keystone及其依赖（包括Doctor组件）
    keystone python3-keystoneclient apache2 libapache2-mod-wsgi-py3 \
    # Nova组件（API和计算服务）
    nova-api nova-conductor nova-scheduler nova-compute-kvm python3-novaclient \
    # Placement服务
    placement-api python3-placement \
    # Glance（最小版本）
    glance python3-glanceclient \
    # Neutron（最小版本）
    neutron-server neutron-plugin-ml2 python3-neutronclient \
    # Cinder（最小版本）
    cinder-api cinder-scheduler python3-cinderclient \
    # Horizon
    openstack-dashboard \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /opt/openstack

# 创建OpenStack服务目录
RUN mkdir -p /etc/openstack \
    && mkdir -p /var/log/openstack \
    && mkdir -p /var/lib/openstack

# 创建非root用户
RUN useradd -m -s /bin/bash openstack \
    && echo "openstack ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/openstack

# 设置root密码
RUN echo 'root:openstack' | chpasswd

# 设置时区
RUN ln -fs /usr/share/zoneinfo/UTC /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata

# 设置环境变量
ENV PATH="/opt/openstack/bin:${PATH}"

# 创建启动脚本目录
RUN mkdir -p /opt/openstack/scripts

# 复制初始化脚本
COPY scripts/init.sh /opt/openstack/scripts/
COPY scripts/restore-state.sh /opt/openstack/scripts/
RUN chmod +x /opt/openstack/scripts/*.sh

# 复制supervisord配置
COPY openstack.conf /etc/supervisor/conf.d/

# 设置工作目录
WORKDIR /opt/openstack
