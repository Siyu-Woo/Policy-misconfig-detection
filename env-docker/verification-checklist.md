# OpenStack权限错误配置检测环境验证清单

本文档提供了验证OpenStack容器环境是否正确配置的步骤和命令。

## 1. 基础镜像和工具验证

验证Ubuntu 22.04基础镜像和基本工具是否正确安装：

```bash
# 检查操作系统版本
docker exec openstack-policy-detection cat /etc/os-release

# 验证基本工具是否安装
docker exec openstack-policy-detection which supervisord
docker exec openstack-policy-detection which vim
docker exec openstack-policy-detection which nano
docker exec openstack-policy-detection which curl
docker exec openstack-policy-detection which wget
docker exec openstack-policy-detection which jq
docker exec openstack-policy-detection which ip
docker exec openstack-policy-detection which ping
docker exec openstack-policy-detection which nc
docker exec openstack-policy-detection which dig
docker exec openstack-policy-detection which openssl
docker exec openstack-policy-detection python3 -m venv --help
```

预期结果：所有命令都应该返回成功，显示工具的路径或帮助信息。

## 2. OpenStack组件验证

验证OpenStack组件是否正确安装：

```bash
# 验证OpenStack客户端
docker exec openstack-policy-detection openstack --version

# 验证Keystone服务
docker exec openstack-policy-detection systemctl status apache2
docker exec openstack-policy-detection ls -la /etc/keystone/

# 验证Nova服务
docker exec openstack-policy-detection ls -la /etc/nova/

# 验证Placement服务
docker exec openstack-policy-detection ls -la /etc/placement/

# 验证Glance服务
docker exec openstack-policy-detection ls -la /etc/glance/

# 验证Neutron服务
docker exec openstack-policy-detection ls -la /etc/neutron/

# 验证Cinder服务
docker exec openstack-policy-detection ls -la /etc/cinder/

# 验证Horizon
docker exec openstack-policy-detection ls -la /etc/openstack-dashboard/
```

预期结果：所有命令都应该返回成功，显示相应服务的配置文件或状态信息。

## 3. 网络配置验证

验证容器网络配置是否正确：

```bash
# 检查网络配置
docker exec openstack-policy-detection ip addr

# 测试网络连接
docker exec openstack-policy-detection ping -c 3 google.com

# 测试DNS解析
docker exec openstack-policy-detection nslookup google.com
```

预期结果：容器应该能够访问外部网络，包括通过主机VPN访问的网络。

## 4. 卷挂载验证

验证卷挂载是否正确配置：

```bash
# 验证Doctor组件挂载
docker exec openstack-policy-detection ls -la /opt/stack/keystone/keystone/cmd/doctor

# 验证策略文件挂载
docker exec openstack-policy-detection ls -la /etc/keystone/policy.yaml

# 验证服务状态挂载
docker exec openstack-policy-detection ls -la /var/lib/openstack/state

# 验证环境信息挂载
docker exec openstack-policy-detection ls -la /opt/openstack/envinfo
```

预期结果：所有挂载点都应该存在，并且包含相应的文件。

## 5. 服务自启动验证

验证服务是否通过supervisord自动启动：

```bash
# 检查supervisord配置
docker exec openstack-policy-detection cat /etc/supervisor/conf.d/openstack.conf

# 检查supervisord进程
docker exec openstack-policy-detection ps aux | grep supervisord

# 检查服务状态
docker exec openstack-policy-detection supervisorctl status
```

预期结果：supervisord应该正在运行，并且所有配置的服务都应该处于RUNNING状态。

## 6. 初始化脚本验证

验证keystone-manage bootstrap初始化脚本是否正确执行：

```bash
# 检查初始化标记
docker exec openstack-policy-detection ls -la /var/lib/openstack/state/initialized

# 验证Keystone服务可用性
docker exec openstack-policy-detection bash -c "source /opt/openstack/envinfo/admin-openrc.sh && openstack token issue"

# 验证服务列表
docker exec openstack-policy-detection bash -c "source /opt/openstack/envinfo/admin-openrc.sh && openstack service list"

# 验证用户列表
docker exec openstack-policy-detection bash -c "source /opt/openstack/envinfo/admin-openrc.sh && openstack user list"

# 验证项目列表
docker exec openstack-policy-detection bash -c "source /opt/openstack/envinfo/admin-openrc.sh && openstack project list"
```

预期结果：初始化标记应该存在，Keystone服务应该可用，并且应该能够列出服务、用户和项目。

## 7. 服务状态持久化验证

验证服务状态是否正确持久化到主机：

```bash
# 检查服务状态目录
ls -la /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker/server\ state

# 检查Keystone配置持久化
ls -la /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker/server\ state/keystone
```

预期结果：服务状态目录应该存在，并且包含Keystone等服务的配置文件。

## 8. 凭据和配置文件验证

验证凭据和配置文件是否正确创建：

```bash
# 检查basic_info文件
cat /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker/envinfo/basic_info

# 检查admin-openrc.sh文件
cat /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker/envinfo/admin-openrc.sh

# 检查clouds.yaml文件
cat /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker/envinfo/clouds.yaml
```

预期结果：所有文件都应该存在，并且包含正确的凭据和配置信息。

## 9. 构建和运行容器

验证容器是否可以成功构建和运行：

```bash
# 构建容器
cd /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker
docker-compose build

# 运行容器
docker-compose up -d

# 检查容器状态
docker ps | grep openstack-policy-detection
```

预期结果：容器应该成功构建和运行，并且状态为"Up"。

## 10. Doctor组件验证

验证Keystone Doctor组件是否可用：

```bash
# 进入容器
docker exec -it openstack-policy-detection bash

# 激活环境变量
source /opt/openstack/envinfo/admin-openrc.sh

# 测试Doctor组件
keystone-manage doctor
```

预期结果：Doctor组件应该能够正常运行，并显示诊断信息。

## 总结

如果上述所有验证步骤都通过，则表明OpenStack权限错误配置检测环境已经正确配置。现在您可以开始扩展Doctor组件，使其能够读取policy.yaml配置并检测错误配置。
