# OpenStack服务器信息

## 系统用户信息

### 容器用户
| 用户名 | 密码 | 权限 |
|-------|------|------|
| root | openstack | 超级管理员 |
| openstack | 无密码 | sudo权限（无需密码） |

## OpenStack用户信息

### 用户
| 用户名 | ID | 密码 | 备注 |
|-------|---|------|------|
| admin | 45b889b99126447ab911c10dd78d59e6 | admin | 管理员用户 |

### 项目
| 项目名 | ID | 描述 |
|-------|---|------|
| admin | 4c305f9eee144766bf404b1f2d41143d | 管理项目 |
| service | f33e85ba0ab54e33945a153f7dce8acd | 服务项目 |

### 角色
| 角色名 | ID | 描述 |
|-------|---|------|
| admin | 96188595fa6d4758a527a619619e4ce3 | 管理员角色 |
| member | a34da152f2194792b3bacd5d5b41082c | 成员角色 |
| reader | bcb31cf63c0e4f008805d5ffe6b9ce6f | 读取角色 |

## OpenStack服务信息

### 服务
| 服务名 | ID | 类型 | 描述 |
|-------|---|------|------|
| keystone | 8875d90e370c408a9d8bc8d2b5738bea | identity | 身份认证服务 |

### 端点
| ID | 区域 | 服务名 | 接口 | URL |
|---|------|-------|------|-----|
| 13dc8906592f43a8b83e574c39841a28 | RegionOne | keystone | internal | http://localhost:5000/v3 |
| 8eb49ca29793422c9aabdaa602e576f2 | RegionOne | keystone | admin | http://localhost:5000/v3 |
| d353a82daf9b4197a42748fc84147b5e | RegionOne | keystone | public | http://localhost:5000/v3 |

## 数据库信息

### MySQL
| 用户名 | 密码 | 权限 |
|-------|------|------|
| root | openstack | 超级管理员 |
| debian-sys-maint | 6onCStiGoaz4tlB8 | 系统维护 |
| keystone | keystone | keystone数据库 |
| nova | nova | nova相关数据库 |
| placement | placement | placement数据库 |
| glance | glance | glance数据库 |
| neutron | neutron | neutron数据库 |
| cinder | cinder | cinder数据库 |

### 数据库列表
- keystone: Keystone身份认证服务数据库
- nova: Nova计算服务数据库
- nova_api: Nova API服务数据库
- nova_cell0: Nova Cell0数据库
- placement: Placement服务数据库
- glance: Glance镜像服务数据库
- neutron: Neutron网络服务数据库
- cinder: Cinder块存储服务数据库

## 消息队列信息

### RabbitMQ
| 用户名 | 密码 | 权限 |
|-------|------|------|
| openstack | openstack | 所有权限 |

## 服务端口映射

| 服务 | 容器端口 | 主机端口 |
|------|---------|---------|
| Keystone | 5000 | 5000 |
| Nova | 8774 | 8774 |
| Placement | 8778 | 8778 |
| Glance | 9292 | 9292 |
| Neutron | 9696 | 9696 |
| Cinder | 8776 | 8776 |
| Horizon | 80 | 80 |

## 服务状态

以下服务已在容器中运行：
- MySQL
- RabbitMQ
- Memcached
- Apache2
- Keystone
- Glance API
- Nova API (存在一些僵尸进程)
- Placement API
- Cinder API

## 配置文件位置

- Keystone: /etc/keystone/
- Nova: /etc/nova/
- Glance: /etc/glance/
- Neutron: /etc/neutron/
- Cinder: /etc/cinder/
- Horizon: /etc/openstack-dashboard/

## Doctor组件位置

- /usr/lib/python3/dist-packages/keystone/cmd/doctor/

## 策略文件位置

- Keystone: /etc/keystone/policy.yaml/policy.yaml
