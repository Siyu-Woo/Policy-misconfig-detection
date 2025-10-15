# OpenStack权限错误配置检测环境使用手册

## 初始操作步骤

### 容器启动

1. 进入项目目录：
   ```bash
   cd /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker
   ```

2. 设置Docker环境变量（如果使用Docker Desktop）：
   ```bash
   export DOCKER_HOST=unix:///var/run/docker.sock
   ```

3. 启动容器（推荐使用优化后的挂载配置）：
   ```bash
   docker run -d --name openstack-policy-detection \
     -p 5000:5000 -p 8774:8774 -p 8778:8778 -p 9292:9292 \
     -p 9696:9696 -p 8776:8776 -p 80:80 \
     -v /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker/keystone-cmd:/usr/lib/python3/dist-packages/keystone/cmd \
     -v /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/data/policy\ file:/etc/openstack/policies \
     -v /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker/server\ state:/var/lib/openstack/state \
     -v /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker/envinfo:/opt/openstack/envinfo \
     openstack-policy-detection /usr/bin/supervisord -c /etc/supervisor/conf.d/openstack.conf
   ```

   **旧版挂载方式（仍可使用）**：
   ```bash
   docker run -d --name openstack-policy-detection \
     -p 5000:5000 -p 8774:8774 -p 8778:8778 -p 9292:9292 \
     -p 9696:9696 -p 8776:8776 -p 80:80 \
     -v /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker/doctor:/usr/lib/python3/dist-packages/keystone/cmd/doctor \
     -v /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/data/policy\ file:/etc/keystone/policy.yaml \
     -v /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker/server\ state:/var/lib/openstack/state \
     -v /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker/envinfo:/opt/openstack/envinfo \
     openstack-policy-detection /usr/bin/supervisord -c /etc/supervisor/conf.d/openstack.conf
   ```

### 进入容器

```bash
docker exec -it openstack-policy-detection bash
```

### 服务状态检查

1. 检查服务状态：
   ```bash
   ps aux | grep -E 'keystone|nova|glance|neutron|cinder|placement|apache|mysql|rabbitmq|memcached'
   ```

2. 检查MySQL服务：
   ```bash
   service mysql status
   ```

3. 检查RabbitMQ服务：
   ```bash
   service rabbitmq-server status
   ```

4. 检查Apache服务：
   ```bash
   service apache2 status
   ```

### OpenStack服务使用

1. 设置环境变量（首次使用或新会话时需要执行）：
   ```bash
   export OS_USERNAME=admin
   export OS_PASSWORD=admin
   export OS_PROJECT_NAME=admin
   export OS_USER_DOMAIN_NAME=Default
   export OS_PROJECT_DOMAIN_NAME=Default
   export OS_AUTH_URL=http://localhost:5000/v3
   export OS_IDENTITY_API_VERSION=3
   export OS_IMAGE_API_VERSION=2
   ```

   或者使用环境变量文件（推荐方式）：
   ```bash
   source /opt/openstack/envinfo/admin-openrc.sh
   ```

2. 测试OpenStack服务：
   ```bash
   openstack token issue
   openstack user list
   openstack project list
   openstack service list
   openstack endpoint list
   ```

### 退出并关闭容器

1. 退出容器：
   ```bash
   exit
   ```

2. 停止容器：
   ```bash
   docker stop openstack-policy-detection
   ```

3. 删除容器（如果需要）：
   ```bash
   docker rm openstack-policy-detection
   ```

## 挂载目录映射关系

### 推荐配置（优化后）

| 主机目录 | 容器目录 | 用途 |
|---------|---------|------|
| /home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/keystone-cmd | /usr/lib/python3/dist-packages/keystone/cmd | Keystone命令模块（包含doctor） |
| /home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/policy file | /etc/openstack/policies | 所有组件的策略文件 |
| /home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/server state | /var/lib/openstack/state | 服务状态持久化 |
| /home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/envinfo | /opt/openstack/envinfo | 环境信息和凭据 |

### 旧版配置（兼容性）

| 主机目录 | 容器目录 | 用途 |
|---------|---------|------|
| /home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/doctor | /usr/lib/python3/dist-packages/keystone/cmd/doctor | Doctor组件代码 |
| /home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/policy file | /etc/keystone/policy.yaml | 策略文件 |
| /home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/server state | /var/lib/openstack/state | 服务状态持久化 |
| /home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/envinfo | /opt/openstack/envinfo | 环境信息和凭据 |

**注意**：当前Doctor组件的实际位置是`/usr/lib/python3/dist-packages/keystone/cmd/doctor`，而不是`/opt/stack/keystone/keystone/cmd/doctor`。请确保在启动容器时使用正确的挂载路径。

## 服务信息查询和存储位置

服务信息存储在以下位置：

- **服务器信息文件**：`/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/envinfo/serverinfo.md`
  包含系统用户、OpenStack用户、项目、角色、服务、端点、数据库等信息。

- **服务状态持久化**：`/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/server state/`
  - `databases/` - 关键数据库文件
    - `nova.sqlite` - Nova服务数据库
    - `nova_api.sqlite` - Nova API数据库
    - `placement.sqlite` - Placement服务数据库
    - `neutron.sqlite` - Neutron网络服务数据库
    - `cinder.sqlite` - Cinder存储服务数据库
  - `configs/` - 关键配置文件备份
    - `keystone.conf` - Keystone身份认证服务配置
    - `nova.conf` - Nova计算服务配置

- **日志文件**：
  - Keystone日志：`/var/log/keystone/`
  - Nova日志：`/var/log/nova/`
  - Glance日志：`/var/log/glance/`
  - Neutron日志：`/var/log/neutron/`
  - Cinder日志：`/var/log/cinder/`
  - Apache日志：`/var/log/apache2/`
  - MySQL日志：`/var/log/mysql/`

- **配置文件**：
  - Keystone配置：`/etc/keystone/`
  - Nova配置：`/etc/nova/`
  - Glance配置：`/etc/glance/`
  - Neutron配置：`/etc/neutron/`
  - Cinder配置：`/etc/cinder/`
  - Horizon配置：`/etc/openstack-dashboard/`

## 注意事项

1. **配置文件修改**：如果调整或补充挂载文件，更新、新增、删减用户，调整密码等、调整端口等信息，需要同步更新上述基本信息serverinfo.md。

2. **任务记录**：每次执行任务后，都应更新记录Task.md。

3. **策略文件**：当前Keystone使用的策略文件位于`/etc/keystone/policy.yaml/policy.yaml`，而不是直接位于`/etc/keystone/policy.yaml`。这是因为挂载配置的特殊性，在代码中需要注意这一点。

4. **Nova API僵尸进程**：当前Nova API存在一些僵尸进程，这可能是由于服务配置问题导致的。如果影响使用，可能需要进一步调查和修复。

5. **Apache重启**：Apache服务重启可能会失败，但服务实际上仍在运行。如果需要重启Apache，可能需要先停止服务，然后再启动。
