# 本文件为OpenStack Misconfig Detection环境使用手册
# ---------------------------------------------------------------------------------------------------------------------------------------- #
## 使用说明
1. **查阅**：每次使用前，请先查阅本文件，以便了解相关内容。本手册包括：
   - ## 文件基本信息：包括容器配置、环境设置、文件夹、文件挂载情况等
   - ## 操作步骤：包括进入容器后操作步骤（如果使用大模型，一定先了解这块）、容器迁移操作步骤、服务配置相关操作；
   - ## 系统功能模块：介绍每个系统每个功能代码，包括模块功能说明、代码位置（一般代码位置会有一个更具体说明文档）、相关文件说明、输入输出、其他说明（如要求和注意事项）。

2. **文件更新**：如果调整或补充挂载文件，更新、新增、删减用户，调整密码等环境配置、调整端口等容器配置，需要同步更新##文件基本信息 和 ## 操作步骤。

3. **功能更新**：每次使用后，如果涉及新增、删减、调整模块代码，需要更新 ## 系统功能模块

4. **问题处理**：每次有相关问题并被解决了，请填写相同文件夹下的Q&A.md文件

# ---------------------------------------------------------------------------------------------------------------------------------------- #
## 文件基本信息查询
### Openstack
1. 目前Openstack包含组件有：keystone、nova、cinder、glance、placement、neutron

### conda环境
1. 目前主要使用base环境即可，相关依赖：（容器内）/opt/openstack/envinfo/base-env.yaml

### 端口
1. 宿主机代理http端口为20171，容器内端口配置为20179
2. 端口映射：
  -p 5000:5000 -p 8774:8774 -p 8778:8778 -p 9292:9292 \
  -p 9696:9696 -p 8776:8776 -p 80:80 \
  -p 7474:7474 -p 7687:7687 \

### Neo4J
   - Web：http://localhost:7474  
   - Bolt：`bolt://localhost:7687`  
   - 账户：`neo4j` / `Password`

### 挂载目录映射关系
| 主机目录 | 容器目录 | 用途 |
| --- | --- | --- |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/keystone-cmd` | `/usr/lib/python3/dist-packages/keystone/cmd` | 覆盖 Keystone 内置命令，便于调试和扩展 |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/policy file` | `/etc/openstack/policies` | 提供策略文件输入，供 OpenStack 服务及策略解析脚本读取 |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/server state` | `/var/lib/openstack/state` | 承载 Keystone/Nova/Neutron/Placement/Cinder 的 SQLite 数据库及配置快照 |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/envinfo` | `/opt/openstack/envinfo` | 保存 `serverinfo.md`、`admin-openrc.sh` 等环境说明与凭证脚本 |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/data` | `/lib/var/neo4j` | Neo4j 图数据库数据持久化 |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/conf` | `/etc/neo4j` | Neo4j 配置文件（`neo4j.conf` 等） |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/logs` | `/var/log/neo4j` | Neo4j 日志持久化 |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/assistfile` | `/root/policy-fileparser/data/assistfile` | 策略解析/统计检测所需的辅助 CSV/JSON 数据 |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/fileparser` | `/root/policy-fileparser` | 策略/身份解析与图谱脚本（`run_graph_pipeline.py`、`openstackpolicygraph.py` 等） |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/StatisticDetect` | `/root/StatisticDetect` | 统计检测脚本目录（`StatisticCheck.py`、`UnkownStatisticCheck.py`） |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/DynamicDetect` | `/root/DynamicDetect` | 动态检测脚本目录（`Authorization_scope_check.py`） |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/Tools` | `/root/Tools` | 辅助工具脚本目录（`SensiPermiSet.py`、`RoleGrantInfo.py` 等） |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/Web` | `/root/Web` | Web 可视化/服务相关代码 |
| `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/log/keystone` | `/var/log/keystone` | Keystone 日志持久化 |

### 服务信息查询和存储位置
- **服务器信息/凭证**：`env-docker/envinfo/serverinfo.md`、`env-docker/envinfo/admin-openrc.sh`（挂载到容器 `/opt/openstack/envinfo/`）提供系统用户、项目、角色、端点以及 OpenStack CLI 凭证。
- **服务状态/数据库**：`env-docker/server state/databases/`（容器 `/var/lib/openstack/state/databases/`）包含 `nova.sqlite`、`nova_api.sqlite`、`placement.sqlite`、`neutron.sqlite`、`cinder.sqlite` 等 SQLite 数据库，实现服务状态持久化。
- **配置快照**：`env-docker/server state/configs/` 保存 `keystone.conf`、`nova.conf` 等关键配置，可与容器 `/etc/<service>/` 下的实时配置互相对照，必要时覆盖恢复。
- **策略与脚本**：策略文件集中在 `data/policy file/`，fileparser 代码位于 `fileparser/` 并挂载到容器 `/root/policy-fileparser`，执行图谱脚本或查看日志都在该目录下完成。
- **辅助数据与检测输出**：`data/assistfile/` 对应容器 `/root/policy-fileparser/data/assistfile/`，保存 `sensitive_permissions.csv`、`userinfo.csv`、`projectinfo.csv`、`roleinfo.csv`、`rolegrant.csv`、`rbac_audit_keystone.csv`、`role_level.json`、`RoleStatistic*.csv` 等统计/检测中间结果与输出文件。
- **检测脚本位置**：统计检测脚本在 `StatisticDetect/`（容器 `/root/StatisticDetect`），动态检测脚本在 `DynamicDetect/`（容器 `/root/DynamicDetect`），工具脚本在 `Tools/`（容器 `/root/Tools`）。
- **Neo4j 数据/日志**：`data/neo4j/data`、`data/neo4j/conf`、`data/neo4j/logs` 对应容器 `/lib/var/neo4j`、`/etc/neo4j`、`/var/log/neo4j`，覆盖图数据库数据、配置与运行日志。
- **OpenStack 组件日志**：Keystone 日志持久化在宿主机 `log/keystone/`（容器 `/var/log/keystone/`）；其他组件日志仍位于容器内 `/var/log/nova/`、`/var/log/glance/`、`/var/log/neutron/`、`/var/log/cinder/`、`/var/log/apache2/`、`/var/log/mysql/` 等，可按需再挂载宿主机目录做长期留存。
- **服务配置目录**（容器内）：`/etc/keystone/`、`/etc/nova/`、`/etc/glance/`、`/etc/neutron/`、`/etc/cinder/`、`/etc/openstack-dashboard/`，遇到配置漂移时与 `server state/configs/` 中的快照同步即可。

# --------------------------------------------------------------------------------------------------------------------------------------- #
## 容器初始化操作步骤
### 进入容器启动项目（已有容器）
1. **宿主机初始化**
```bash
   # 切换项目路径
cd /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection
   # 宿主机网络设置（用于容器/远程服务器）
sudo apt-get update && sudo apt-get install -y socat #宿主机安装socat
sudo nohup socat TCP-LISTEN:20179,fork,reuseaddr TCP:127.0.0.1:20171 >/tmp/socat-20179.log 2>&1 & # 开启20179监听
sudo ss -lntp | grep 20179 # 验证显示有20179
   # 启动容器
export DOCKER_HOST=unix:///var/run/docker.sock # 设置Docker环境变量
sudo docker start openstack-policy-detection # 启动容器
```

```bash
ssh -L 8081:localhost:80 -L 7474:localhost:7474 -L 7689:localhost:7687 wusy@58.206.232.230 #macos远程到宿主机时候需要在mac的terminal进行ssh
```

2. **进入容器**
```bash
sudo docker exec -it openstack-policy-detection bash #进入容器
```

3. **容器内初始化**
```bash
   # 容器网络环境变量设置：
echo 'export http_proxy="http://172.17.0.1:20179"' >> ~/.bashrc # 用于和宿主机VPN代理协同
echo 'export https_proxy="http://172.17.0.1:20179"' >> ~/.bashrc 
echo 'export no_proxy="localhost,127.0.0.1,::1"' >> ~/.bashrc #用于openstack服务端点绕开
source ~/.bashrc # 网络设置立即生效
env | grep proxy # 检查确认：是否出现上述设置内容，没有的话重新source
   # 加载openstack身份环境变量
source /opt/openstack/envinfo/admin-openrc.sh #加载admin用户
env | grep ^OS_   # 查看加载情况
   # 检查openstack组件运行情况
ps aux | grep -E 'keystone|nova|glance|neutron|cinder|placement|apache|mysql|rabbitmq|memcached' # 检查服务是否启动
service mysql status # 如果没有运行中，则service mysql restart
service rabbitmq-server status # 如果没有运行中，则service rabbitmq-server restart
service apache2 status # 如果没有running，则进行start
ss -lntp | grep 5000 # 显示在监听5000,则service apache2 restart
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/v3 # 返回200，如果不是200，查看5. **故障处理方法**的5.1
   # 检查当前身份是否正常运行
openstack project list
openstack user list #仅有project list不够
   # 初始化依赖
conda activate base # 初始化环境
neo4j start 
neo4j status #查看neo4j状态，如果未运行则重启：neo4j restart
```

4. **如果容器已经启动需要中止**
```bash
sudo docker stop openstack-policy-detection #停止容器
sudo docker rm openstack-policy-detection # rm后跟需要删除容器以释放端口/名字
```

5. **故障处理方法**
   **5.1 Apache/keystone状态不对，重启Apache/keystone服务**
      # （1）结束进程
      ```bash
      service supervisor stop 2>/dev/null || true #守护进程关闭
      service apache2 stop
      ```
      # （2）注意，此时会自动退出容器，在宿主机终端start再进入容器
      ```bash
      export DOCKER_HOST=unix:///var/run/docker.sock 
      sudo docker start openstack-policy-detection openstack-policy-detection
      sudo docker exec -it openstack-policy-detection bash
      ```
      # （3）然后重新执行3. **容器内初始化**初始化过程
      # （4）如果完成上述后还是不行，再执行清空apache2进程
      ```bash
      service apache2 stop
      rm -f /var/run/apache2/apache2.pid
      rm -f /var/run/apache2/apache2.pid
      pkill -9 -f apache2ctl
      pkill -9 -f apache2
         # 再确认apache状态，如果清空了apache2相关的pid，则在启动一下
      service apache2 status
      service apache2 start
      ```
      # (5)方案3:可能权限问题：
      ```bash
      # 容器内执行
      grep -R "WSGIDaemonProcess .*keystone" -n /etc/apache2 
      chown -R keystone:keystone /var/log/keystone
      chmod 750 /var/log/keystone
      chmod 640 /var/log/keystone/keystone.log

      ```

   **5.2 pip install显示connection失败：重新设置网络**
      # （1）查看本地机器的联网是否正确
      # （2）重新设置宿主机网络：重新执行1. **宿主机初始化**
      # （3）重写source网络
      ```bash
         # 容器网络环境变量设置：
      echo 'export http_proxy="http://172.17.0.1:20179"' >> ~/.bashrc # 用于和宿主机VPN代理协同
      echo 'export https_proxy="http://172.17.0.1:20179"' >> ~/.bashrc 
      echo 'export no_proxy="localhost,127.0.0.1,::1"' >> ~/.bashrc #用于openstack服务端点绕开
      source ~/.bashrc # 网络设置立即生效
      env | grep proxy # 检查确认：是否出现上述设置内容，没有的话重新source
      ```

   **5.3 远程Neo4j时，本地机器无法链接**
      # （1）重新执行宿主机初始化
      # （2）查看neo4j状态，必要时重启
      ```bash
      neo4j start
      neo4j status
      cypher-shell -u neo4j -p Password 'RETURN 1' # 命令行测试
      ```
      # （3）重新执行： **6.3 远程查看Neo4j图数据库**

6. **其他操作**
   **6.1 conda操作**
   ```bash
   source /opt/miniconda/etc/profile.d/conda.sh #conda初始化
   conda env list # 查看环境
   conda activate base #启动环境
   conda create -n {conda_env_name} python=3.10 # 创建环境
   ```

   **6.2 安装依赖：按照缺失的安装**
   ```bash
   pip install pyyaml
      # ...
      # 所有依赖可见/opt/openstack/envinfo/base-env.yaml
   ```

   **6.3 远程查看Neo4j图数据库**
      # （1）在服务器neo4j位置配置如下内容
      ```bash
      nano etc/neo4j/neo4j.conf
      # 找到：#dbms.connector.bolt.listen_address=:7687
      # 修改为：dbms.connector.bolt.listen_address=0.0.0.0:7687
      # 找到：#dbms.connector.http.listen_address=:7474
      # 修改为：dbms.connector.http.listen_address=0.0.0.0:7474
      ```
      # （2）本地机器重新运行：
      ```bash
         ssh -L 7474:localhost:7474 -L 7687:localhost:7687 wusy@58.206.232.230
      ```
      # （3）浏览器输入：http://localhost:7474  

   **6.4 测试Openstack基本服务**
   ```bash
   openstack token issue
   openstack user list
   openstack project list
   openstack service list
   openstack endpoint list
   ```

   **6.5 Python链接图数据库并查询**
      # python链接
      ```python
      from neo4j import GraphDatabase
      driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "Password"))  
      with driver.session() as session:
         result = session.run("MATCH (n) RETURN count(n) as count")
         print(result.single()["count"])
      driver.close()
      ```
      # 基本查询示例**：
      ```bash
      cypher-shell -u neo4j -p Password "MATCH (n) RETURN count(n) as node_count;" # 查询节点总数 
      cypher-shell -u neo4j -p Password "CALL db.info();" 
      cypher-shell -u neo4j -p Password "CALL db.labels();" # 查询所有标签
      ```

### 容器迁移后挂载
1. **旧宿主机打包镜像**
   ```bash
   docker save openstack-policy-detection:conda-neo4j -o openstack-policy-detection.tar
   ```
2. **新宿主机迁移镜像和相关文件夹**
   ```bash
   cd /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker # 切换到工作路径
   docker load -i openstack-policy-detection.tar # 解压惊喜
   docker build -t openstack-policy-detection:conda-neo4j .
      # 根据挂载需求创建文件夹（注意需要把原文件夹对应路径下文件copy过来
   sudo mkdir -p \
     "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/data" \
     "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/conf" \
     "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/logs"
     # 注1：...其他命令
     # 注2:首次迁移时，可通过 `docker cp openstack-policy-detection:/var/lib/neo4j/. data/neo4j/data` 等命令同步数据、配置和日志。
   
      # 根据挂载需求，赋予读写权限
   sudo chown -R 109:112 "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/server state"
   sudo chmod -R 775 "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/server state"

3. **首次启动容器（需要进行挂载和端口映射）**
   ```bash
         cd /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/env-docker # 切换到项目路径下

         export DOCKER_HOST=unix:///var/run/docker.sock # 链接Docker守护进程

         # 挂载和端口映射
         sudo docker run -d --name openstack-policy-detection \
      -p 5000:5000 -p 8774:8774 -p 8778:8778 -p 9292:9292 \
      -p 9696:9696 -p 8776:8776 -p 80:80 \
      -p 7474:7474 -p 7687:7687 \
      -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/keystone-cmd:/usr/lib/python3/dist-packages/keystone/cmd" \
      -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/policy file:/etc/openstack/policies" \
      -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/server state:/var/lib/openstack/state" \
      -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/env-docker/envinfo:/opt/openstack/envinfo" \
      -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/data:/lib/var/neo4j" \
      -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/conf:/etc/neo4j" \
      -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/neo4j/logs:/var/log/neo4j" \
      -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/assistfile:/root/policy-fileparser/data/assistfile" 
      -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/fileparser:/root/policy-fileparser" \
      -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/StatisticDetect:/root/StatisticDetect" \
      -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/DynamicDetect:/root/DynamicDetect" \
      -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/Tools:/root/Tools" \
      -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/Web:/root/Web" \
      -v "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/log/keystone:/var/log/keystone" \
      openstack-policy-detection:policyparser \
      /usr/bin/supervisord -c /etc/supervisor/conf.d/openstack.conf
   ```

4. **容器提交**
   ```bash
   sudo docker ps # 查看当前容器名（宿主机）
   sudo docker commit openstack-policy-detection openstack-policy-detection:policyparser  # 提交
      # 注：后面openstack-policy-detection:policyparser需要改为当前的容器名
   ```

# --------------------------------------------------------------------------------------------------------------------------------------- #
## 核心运行流程
### 图数据库解析
1. **图数据库解析policy***
```bash
   #完整命令
python   /root/policy-fileparser/run_graph_pipeline.py \ 
   # 补充命令行信息
    --policy-files /etc/openstack/policies/keystone-policy.yaml \ # 指定策略文件，此处默认为keystone读取路径
    --neo4j-uri bolt://localhost:7687 \ # 指定图数据库
    --neo4j-user neo4j \
    --neo4j-password Password \
    --skip-identity \ # 表示仅加载策略子图，跳过身份子图
    --show-check-report \ # 仅打印策略检测结果
    --show-token-info \ # 输出读取 token 及生成映射时的详细信息。
    --show-policy-debug \ # 在解析每条策略时打印原始表达式及解析结果。
    --show-check-report \ # 打印策略重复/冲突检查的详细报告（默认只记录计数）。
    --show-policy-statistic \ # 写入策略子图后打印 Neo4j 中的节点/关系统计。

```
2. **生成或导出当前Policy**
   ```bash
      # 图数据库导出为csv文件
   python /root/policy-fileparser/PolicyGen.py graph-to-csv \
      --neo4j-uri bolt://localhost:7687 \
      --neo4j-user neo4j \
      --neo4j-password Password \
      --output-dir "/etc/openstack/policies"
   ```

   ```bash
      # CSV生成YAML
   python /root/policy-fileparser/PolicyGen.py csv-to-yaml \
      --csv-files "/etc/openstack/policies/NowPermit.csv" "/etc/openstack/policies/NowPermitinadmin.csv" \
      --projects none admin \
      --output "/etc/openstack/policies/PolicyFromCsv.yaml"
   ```

   ```bash
      # 图数据库生成YAML
   python /root/policy-fileparser/PolicyGen.py graph-to-yaml \
      --neo4j-uri bolt://localhost:7687 \
      --neo4j-user neo4j \
      --neo4j-password Password \
      --output "/etc/openstack/policies/PolicyFromGraph.yaml"
   ```

3. **其他相关代码模块见fileparser.md**

### 检查代码
1. **静态已知错误配置检查**
```bash
# 错误码1-3，在图数据库解析时进行检查
python   /root/policy-fileparser/run_graph_pipeline.py
# 错误码4-7，需要前置运行数据库
python /root/StatisticDetect/StatisticCheck.py 
```

2. **静态未知错误配置检查**
```bash
# 错误码 12、13，需要前置运行数据库
python /root/StatisticDetect/UnkownStatisticCheck.py check
```

3. **动态位置错误配置检查**
```bash
# 错误码 10、11，需要前置运行extract_keystone_rbac.py
python /root/DynamicDetect/Authorization_scope_check.py
```

### Tools 工具代码（完整见tools.md）
1. **SensiPermiSet：维护敏感权限库**
```bash
   python /root/Tools/SensiPermiSet.py view # 查看敏感权限列表
   # 默认读取文件路径：/root/policy-fileparser/data/assistfile/sensitive_permissions.csv
```
2. **api_requester：快速发起Openstack CLI请求**
```bash
  python /root/Tools/api_requester.py --api "openstack project list"
```

3. **RoleGrantInfo 获取当前容器内的用户、角色、域信息以及授权情况**
```bash
  python /root/Tools/RoleGrantInfo.py
  # 生成的文件位于 /root/policy-fileparser/data/assistfile）
```

4. **extract_keystone_rbac：将keystone授权日志解析为动态检测输入需要的csv**
```bash
  python /root/Tools/extract_keystone_rbac.py
  # 结果文件：/root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv
  ```

5. **Policyset 将配置文件放到Policy策略读取生效文件夹**
 ```bash
  # 将指定策略文件导入生效文件夹
  python /root/Tools/Policyset.py copy --src /etc/openstack/policies/policy.yaml
  # 导出策略文件
  python /root/Tools/Policyset.py export --dst /etc/openstack/policies/keystone_policy_export.yaml
```



## Web交互
1. **安装依赖**
```bash
pip install flask
wget -O neovis.js https://unpkg.com/neovis.js@2.0.0/dist/neovis.js --no-check-certificate
```

2. **注意，需要修改apache端口，释放80端口**
```bash
sed -i 's/^Listen 80/#Listen 80/g' /etc/apache2/ports.conf # 注释掉 ports.conf 中的 Listen 80
   # 禁用可能占用 80 端口的默认站点配置 (如果有的话)，这一步是为了防止重启 apache 时报警
if [ -f /etc/apache2/sites-enabled/000-default.conf ]; then
    rm /etc/apache2/sites-enabled/000-default.conf
fi
if [ -f /etc/apache2/sites-enabled/openstack-dashboard.conf ]; then
    mv /etc/apache2/sites-enabled/openstack-dashboard.conf /etc/apache2/sites-available/openstack-dashboard.conf
fi
service apache2 restart # 重启服务
openstack token issue # 验证释放后服务正常
netstat -tulpn | grep :80 # 显示为空，确认80端口释放了
```

3. **启动web**
```bash
python /root/Web/app.py
```


2. 容器内部配置

#### OpenStack服务相关操作
1. 设置环境变量（首次使用或新会话时需要执行）：
   ```bash
 
   ```
   **或者使用环境变量文件（推荐方式**


