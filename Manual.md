# 本文件为OpenStack Misconfig Detection环境使用手册
# ------------------------------------------------------------------------------------------ #
## 使用说明
1. **查阅**：每次使用前，请先查阅本文件，以便了解相关内容。本手册包括：
   - ## 文件基本信息：包括容器配置、环境设置、文件夹、文件挂载情况等
   - ## 操作步骤：包括进入容器后操作步骤（如果使用大模型，一定先了解这块）、容器迁移操作步骤、服务配置相关操作；
   - ## 系统功能模块：介绍每个系统每个功能代码，包括模块功能说明、代码位置（一般代码位置会有一个更具体说明文档）、相关文件说明、输入输出、其他说明（如要求和注意事项）。

2. **文件更新**：如果调整或补充挂载文件，更新、新增、删减用户，调整密码等环境配置、调整端口等容器配置，需要同步更新##文件基本信息 和 ## 操作步骤。

3. **功能更新**：每次使用后，如果涉及新增、删减、调整模块代码，需要更新 ## 系统功能模块

4. **问题处理**：每次有相关问题并被解决了，请填写相同文件夹下的Q&A.md文件

# ------------------------------------------------------------------------------------------ #
## 文件基本信息
### Openstack
1. 目前Openstack包含组件有：keystone、nova、cinder、glance、placement、neutron

### conda环境
1. 目前主要使用base环境即可，相关依赖已安装在base环境内

### 端口
1. 宿主机代理http端口为20171，容器内端口配置为20179
2. 端口映射：
  -p 5000:5000 -p 8774:8774 -p 8778:8778 -p 9292:9292 \
  -p 9696:9696 -p 8776:8776 -p 80:80 \
  -p 7474:7474 -p 7687:7687 \

### Neo4J
1. 默认账号 `neo4j`、密码 `Password`
2. 通过 `7474/7687` 端口提供 HTTP/Bolt 接口。

### 挂载目录映射关系
| 主机目录 | 容器目录 | 用途 |
| --- | --- | --- |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/keystone-cmd` | `/usr/lib/python3/dist-packages/keystone/cmd` | 覆盖 Keystone 内置命令，便于调试和扩展 |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/policy file` | `/etc/openstack/policies` | 提供策略文件输入，供 OpenStack 服务及策略解析脚本读取 |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/server state` | `/var/lib/openstack/state` | 承载 Keystone/Nova/Neutron/Placement/Cinder 的 SQLite 数据库及配置快照 |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/envinfo` | `/opt/openstack/envinfo` | 保存 `serverinfo.md`、`admin-openrc.sh` 等环境说明与凭证脚本 |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/data` | `/var/lib/neo4j` | Neo4j 图数据库数据持久化 |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/conf` | `/etc/neo4j` | Neo4j 配置文件（`neo4j.conf` 等） |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/logs` | `/var/log/neo4j` | Neo4j 日志持久化 |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/fileparser` | `/root/policy-fileparser` | 策略/身份解析与图谱脚本（`run_graph_pipeline.py`、`openstackpolicygraph.py` 等） |

### 服务信息查询和存储位置
- **服务器信息/凭证**：`env-docker/envinfo/serverinfo.md`、`env-docker/envinfo/admin-openrc.sh`（挂载到容器 `/opt/openstack/envinfo/`）提供系统用户、项目、角色、端点以及 OpenStack CLI 凭证。
- **服务状态/数据库**：`env-docker/server state/databases/`（容器 `/var/lib/openstack/state/databases/`）包含 `nova.sqlite`、`nova_api.sqlite`、`placement.sqlite`、`neutron.sqlite`、`cinder.sqlite` 等 SQLite 数据库，实现服务状态持久化。
- **配置快照**：`env-docker/server state/configs/` 保存 `keystone.conf`、`nova.conf` 等关键配置，可与容器 `/etc/<service>/` 下的实时配置互相对照，必要时覆盖恢复。
- **策略与脚本**：策略文件集中在 `data/policy file/`，fileparser 代码位于 `fileparser/` 并挂载到容器 `/root/policy-fileparser`，执行图谱脚本或查看日志都在该目录下完成。
- **Neo4j 数据/日志**：`data/neo4j/data`、`data/neo4j/conf`、`data/neo4j/logs` 对应容器 `/var/lib/neo4j`、`/etc/neo4j`、`/var/log/neo4j`，覆盖图数据库数据、配置与运行日志。
- **OpenStack 组件日志**（容器内）：`/var/log/keystone/`、`/var/log/nova/`、`/var/log/glance/`、`/var/log/neutron/`、`/var/log/cinder/`、`/var/log/apache2/`、`/var/log/mysql/` 等，可按需再挂载宿主机目录做长期留存。
- **服务配置目录**（容器内）：`/etc/keystone/`、`/etc/nova/`、`/etc/glance/`、`/etc/neutron/`、`/etc/cinder/`、`/etc/openstack-dashboard/`，遇到配置漂移时与 `server state/configs/` 中的快照同步即可。

# ------------------------------------------------------------------------------------------ #
## 操作步骤
### 进入容器启动项目
1. **进入项目目录**
   ```bash
   cd /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker
   ```

2. **设置Docker环境变量（如果使用Docker Desktop）**
   ```bash
   export DOCKER_HOST=unix:///var/run/docker.sock
   ```

3. **启动容器（如果非首次启动容器，无需进行挂载）**
   ```bash
   docker start openstack-policy-detection
   ```
  
  **（如果首次启动容器）需要进行挂载和端口映射**
   ```bash
   docker run -d --name openstack-policy-detection \
  -p 5000:5000 -p 8774:8774 -p 8778:8778 -p 9292:9292 \
  -p 9696:9696 -p 8776:8776 -p 80:80 \
  -p 7474:7474 -p 7687:7687 \
  -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/keystone-cmd:/usr/lib/python3/dist-packages/keystone/cmd" \
  -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/policy file:/etc/openstack/policies" \
  -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/server state:/var/lib/openstack/state" \
  -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/envinfo:/opt/openstack/envinfo" \
  -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/data:/var/lib/neo4j" \
  -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/conf:/etc/neo4j" \
  -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/logs:/var/log/neo4j" \
  -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/fileparser:/root/policy-fileparser" \
  openstack-policy-detection:conda-neo4j /usr/bin/supervisord -c /etc/supervisor/conf.d/openstack.conf
   ```

4. **进入容器**
   ```bash
   docker exec -it openstack-policy-detection bash
   ```

5. **网络环境变量配置**
   ```bash
   # 注意，宿主机需要有v2ray这类的代理，且需要安装socat
   echo 'export http_proxy="http://172.17.0.1:20179"' >> ~/.bashrc
   echo 'export https_proxy="http://172.17.0.1:20179"' >> ~/.bashrc 
   # 前两个用于和本地代理VPN协同，第三个用于openstack服务端点绕开
   echo 'export no_proxy="localhost,127.0.0.1,::1"' >> ~/.bashrc
   # 立即生效
   source ~/.bashrc
   # 检查确认
   env | grep proxy
   ```

6. **加载admin环境变量（openstack admin账号）**
   ```bash
   source /opt/openstack/envinfo/admin-openrc.sh
   ```

7. **服务状态检查**
   **检查openstack组件运行状态**
   ```bash
   ps aux | grep -E 'keystone|nova|glance|neutron|cinder|placement|apache|mysql|rabbitmq|memcached'
   ```

   **检查MySQL服务**
   ```bash
   service mysql status
   ```

   **检查RabbitMQ服务**
   ```bash
   service rabbitmq-server status
   ```

   **检查Apache服务**
   ```bash
   service apache2 status
   ```

   **检查openstack keystone相关服务正常认证监听**
   ```bash
   openstack project list # 正常返回参数
   curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/v3 # 返回200而不是503
      # 如果503，可能需要：（1）环境变量是否正常导入；（2）apache2是否正常监听5000端口
   ```

8. **启动conda**
   **检查conda是否安装**
   ```bash
   conda env list
   ```
   
   **启动conda环境**
   ```bash
   conda activate base
   ```

   **安装依赖（按需）**
   ```bash
   pip install pyyaml
   pip install oslo_policy
   pip install neo4j
   pip install keystoneauth1
   pip install python-keystoneclient
   pip install requests beautifulsoup4 pandas openpyxl 
   ```

9. **启动 Neo4j**
**启动和查看状态**
```bash
neo4j start
neo4j status
```
**默认登录信息**
   - Web：http://localhost:7474  
   - Bolt：`bolt://localhost:7687`  
   - 账户：`neo4j` / `Password`

**命令行测试**
```bash
cypher-shell -u neo4j -p Password 'RETURN 1
```

### 容器迁移后挂载
1. **旧宿主机打包镜像**
   ```bash
   docker save openstack-policy-detection:conda-neo4j -o openstack-policy-detection.tar
   ```
2. **新宿主机解压镜像**
   ```bash
   docker load -i openstack-policy-detection.tar
   ```

2. **构建镜像（如需在新宿主机重建）**  
   ```bash
   cd /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker
   docker build -t openstack-policy-detection:conda-neo4j .
   ```

3. **需要配置宿主机挂载的权限**
   ```bash
   sudo chown -R 109:112 "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/server state"
   sudo chmod -R 775 "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/server state"
   ```

4. **准备宿主机挂载目录**  
   ```bash
   mkdir -p \
     "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/data" \
     "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/conf" \
     "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/logs"
   ```
   首次迁移时，可通过 `docker cp openstack-policy-detection:/var/lib/neo4j/. data/neo4j/data` 等命令同步数据、配置和日志。

**启动容器及后续可参考“进入容器启动项目”**

#### 容器其他操作
1. **退出容器**
   ```bash
   exit
   ```

2. **停止容器**
   ```bash
   docker stop openstack-policy-detection
   ```

3. **删除容器**
   ```bash
   docker rm openstack-policy-detection
   ```

### 其他操作（按需执行）
#### OpenStack服务相关操作
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
   **或者使用环境变量文件（推荐方式**
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

#### Conda/Miniconda 环境
**容器已预装 Miniconda，进入容器后按以下步骤管理 Python 依赖**
1. 初始化：`source /opt/miniconda/etc/profile.d/conda.sh`
2. 激活默认 base 环境：`conda activate base`
3. 创建/启用自定义环境（示例）：  
   
   conda create -n openstack python=3.10
   conda activate openstack
   ```
4. 需要停用时执行 `conda deactivate`。如不想登录即进入 base，可编辑 `~/.bashrc` 注释自动激活行。

##### apache2调试
1. **确认apache状态**
```bash
service apache2 status
ss -lntp | grep 80
# 显示在监听5000，且running
```

2. **如果不满足上述状态，则重新启动apache2**
```bash
rm -f /var/run/apache2/apache2.pid
pkill -9 -f apache2ctl
pkill -9 -f apache2
# 然后再确认apache状态，如果清空了apache2相关的pid，则在启动一下
```

3. **重启apache服务**
```bash
service apache2 stop
rm -f /var/run/apache2/apache2.pid
service apache2 start
```

#### Neo4j服务管理

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

5. Neo4j连接信息

- **HTTP接口**: http://localhost:7474
- **Bolt协议端口**: 7687
- **用户名**: neo4j
- **密码**: Password

#### 本地使用远程服务器的neo4j
0. **在服务器配置如下内容**
   ```bash
   nano etc/neo4j/neo4j.conf
      # 找到：#dbms.connector.bolt.listen_address=:7687
      # 修改为：dbms.connector.bolt.listen_address=0.0.0.0:7687
      # 找到：#dbms.connector.http.listen_address=:7474
      # 修改为：dbms.connector.http.listen_address=0.0.0.0:7474
   ```

1. **Web界面访问**：
   - 在浏览器中打开: http://localhost:7474
   - connect URL：bolt://localhost:7687
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
   
   driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "Password"))
   
   with driver.session() as session:
       result = session.run("MATCH (n) RETURN count(n) as count")
       print(result.single()["count"])
   
   driver.close()
   ```

## 系统功能模块   

### 解析模块
#### 功能
1. **API提取**：提取openstack API名称，并和策略名匹配
2. **策略解析**：用于解析API-role规则，形成授权子图；解析user、role和token关系，形成身份子图；

#### 文件代码说明
- **fileparser解析**
`fileparser/` 目录提供了策略解析、API 抽取、策略与 API 匹配以及知识图谱生成的全部脚本，可配合Neo4j 环境直接运行。

- **策略解析链路**  
  - `run_graph_pipeline.py`提供了策略解析的 一键处理脚本
  - `policypreprocess.py`：读取原始策略 YAML/行文本、展开 `rule:` 引用并输出标准字典。  
  - `policy_parser.py`：依赖 `oslo.policy` 和 `keystone.cmd.doctor` 内置数据库，将策略表达式转换为 DNF，并可写入本地策略数据库。  
  - 针对各组件的策略爬虫（`cinderpolicy.py`、`glancepolicy.py`、`neutronpolicy.py`、`nova_policy.py`、`keystonepolicy.py`）会从 docs.openstack.org 拉取策略文档，生成包含 Default/Operations/描述的 Excel，便于后续处理。

- **API 抽取与匹配**  
  - `cinderapi.py`、`glanceapi.py`、`neutronapi.py`、`novaapi.py`、`keystoneapi.py` 使用 `requests + BeautifulSoup + pandas` 抓取官方 API Reference，并将 HTTP 方法与 URL 导出为 Excel。  
  - `cindermerge.py`、`glancemerge.py`、`neutronmerge.py`、`novamerge.py`、`keystonemerge.py` 将前一步 API 表与策略 Operations 对齐，输出“已匹配”“未匹配 API”“未匹配策略”三类结果，同时用 `openpyxl` 美化单元格，方便快速排查缺失策略。

- **知识图谱构建**  
  - `openstackgraph.py`：通过 `keystoneauth1` / `python-keystoneclient` 读取当前环境中的用户、项目、角色等关系，并借助 `neo4j` 驱动把节点关系写入 Neo4j。脚本内的 `OS_CONFIG` 和 `NEO4J_*` 常量可按需要修改，还提供清理测试数据、生成示例数据和推送写入的完整流程。  
  - `openstackpolicygraph.py`：`PolicyGraphCreator` 根据策略字典（可直接来自 `policy_parser` 或前述 Excel）生成策略节点及条件节点，自动去重、归一化表达式并写入 Neo4j，可作为策略知识图谱的落地脚本。

#### 其他说明
1. `fileparser/` 文件夹已挂载到容器内部，位置为：
