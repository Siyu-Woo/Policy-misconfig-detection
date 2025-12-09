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
  **如果非首次启动容器**
   ```bash
   docker start openstack-policy-detection
   '''
  
  **首次启动容器**
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

## Neo4j图数据库

### Neo4j服务管理

1. **检查Neo4j状态**：
   ```bash
   neo4j status
   ```

2. **启动Neo4j服务**：
   ```bash
   neo4j start
   ```

3. **停止Neo4j服务**：
   ```bash
   neo4j stop
   ```

4. **重启Neo4j服务**：
   ```bash
   neo4j restart
   ```

### Neo4j连接信息

- **HTTP接口**: http://localhost:7474
- **Bolt协议端口**: 7687
- **用户名**: neo4j
- **密码**: Password

### Neo4j使用方式

1. **Web界面访问**：
   - 在浏览器中打开: http://localhost:7474
   - 使用用户名`neo4j`和密码`Password`登录

2. **命令行访问**：
   ```bash
   cypher-shell -u neo4j -p Password
   ```

3. **基本查询示例**：
   ```bash
   # 查询节点总数
   cypher-shell -u neo4j -p Password "MATCH (n) RETURN count(n) as node_count;"
   
   # 查询数据库信息
   cypher-shell -u neo4j -p Password "CALL db.info();"
   
   # 查询所有标签
   cypher-shell -u neo4j -p Password "CALL db.labels();"
   ```

4. **Python连接示例**：
   ```python
   from neo4j import GraphDatabase
   
   driver = GraphDatabase.driver("bolt://localhost:7687", 
                                auth=("neo4j", "Password"))
   
   with driver.session() as session:
       result = session.run("MATCH (n) RETURN count(n) as count")
       print(result.single()["count"])
   
   driver.close()
   ```

### Neo4j数据库状态

- **数据库ID**: 67BC46AAA0BFF16C2ADFB7D70D42C6744B1FAC79EB65DA1ADD819BC3E850FA4C
- **数据库名称**: neo4j
- **创建时间**: 2025-08-07T09:46:37.279Z
- **当前节点数**: 70个节点

## fileparser目录脚本说明

`fileparser/` 目录提供了策略解析、API 抽取、策略与 API 匹配以及知识图谱生成的全部脚本，可配合上面的 Neo4j 环境直接运行。

- **策略解析链路**  
  - `policypreprocess.py`：读取原始策略 YAML/行文本、展开 `rule:` 引用并输出标准字典。  
  - `policy_parser.py`：依赖 `oslo.policy` 和 `keystone.cmd.doctor` 内置数据库，将策略表达式转换为 DNF，并可写入本地策略数据库。  
  - 针对各组件的策略爬虫（`cinderpolicy.py`、`glancepolicy.py`、`neutronpolicy.py`、`nova_policy.py`、`keystonepolicy.py`）会从 docs.openstack.org 拉取策略文档，生成包含 Default/Operations/描述的 Excel，便于后续处理。

- **API 抽取与匹配**  
  - `cinderapi.py`、`glanceapi.py`、`neutronapi.py`、`novaapi.py`、`keystoneapi.py` 使用 `requests + BeautifulSoup + pandas` 抓取官方 API Reference，并将 HTTP 方法与 URL 导出为 Excel。  
  - `cindermerge.py`、`glancemerge.py`、`neutronmerge.py`、`novamerge.py`、`keystonemerge.py` 将前一步 API 表与策略 Operations 对齐，输出“已匹配”“未匹配 API”“未匹配策略”三类结果，同时用 `openpyxl` 美化单元格，方便快速排查缺失策略。

- **知识图谱构建**  
  - `openstackgraph.py`：通过 `keystoneauth1` / `python-keystoneclient` 读取当前环境中的用户、项目、角色等关系，并借助 `neo4j` 驱动把节点关系写入 Neo4j。脚本内的 `OS_CONFIG` 和 `NEO4J_*` 常量可按需要修改，还提供清理测试数据、生成示例数据和推送写入的完整流程。  
  - `openstackpolicygraph.py`：`PolicyGraphCreator` 根据策略字典（可直接来自 `policy_parser` 或前述 Excel）生成策略节点及条件节点，自动去重、归一化表达式并写入 Neo4j，可作为策略知识图谱的落地脚本。

- **依赖安装**  
  上述脚本需要额外的 Python 库，请在容器内（或虚拟环境中）安装：
  ```bash
  pip install requests beautifulsoup4 pandas openpyxl pyyaml oslo.policy keystoneauth1 python-keystoneclient neo4j
  ```
  （如果使用 `policypreprocess.py` 的 `policy_split` 辅助函数，请同时确保该模块已放入 `PYTHONPATH`。）

## 注意事项

1. **配置文件修改**：如果调整或补充挂载文件，更新、新增、删减用户，调整密码等、调整端口等信息，需要同步更新上述基本信息serverinfo.md。

2. **任务记录**：每次执行任务后，都应更新记录Task.md。

3. **策略文件**：当前Keystone使用的策略文件位于`/etc/keystone/policy.yaml/policy.yaml`，而不是直接位于`/etc/keystone/policy.yaml`。这是因为挂载配置的特殊性，在代码中需要注意这一点。

4. **Nova API僵尸进程**：~~当前Nova API存在一些僵尸进程，这可能是由于服务配置问题导致的。如果影响使用，可能需要进一步调查和修复。~~ ✅ 已解决

5. **Apache重启**：Apache服务重启可能会失败，但服务实际上仍在运行。如果需要重启Apache，可能需要先停止服务，然后再启动。这是容器环境的正常行为。

6. **Neo4j图数据库**：Neo4j服务已启动并运行正常，可用于构建OpenStack权限关系图谱和策略分析。
