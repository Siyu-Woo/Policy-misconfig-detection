# 用户与环境变量设置说明

## 0. 权限检查
- 运行前先执行 `env | grep ^OS_` 查看当前用户。
- 若当前用户不是 admin，则提示“权限不足，需要切换admin”，无需继续执行后续新建/删除/罗列操作。

## 1. 环境变量示例
- admin（密码为 `admin`，默认域 Default，Keystone 地址 http://127.0.0.1:5000/v3）  
  ```bash
  export OS_PASSWORD=admin
  export OS_PROJECT_NAME=admin
  export OS_USER_DOMAIN_NAME=Default
  export OS_PROJECT_DOMAIN_NAME=Default
  export OS_AUTH_URL=http://localhost:5000/v3
  export OS_IDENTITY_API_VERSION=3
  export OS_IMAGE_API_VERSION=2
  export OS_INTERFACE=internal
  ```
  ```bash
  source /opt/openstack/envinfo/admin-openrc.sh
  ```

- newuser（默认域 Default，示例切到 demo-project）  
  ```bash
  export OS_USERNAME=newuser
  export OS_PASSWORD=MyPass123
  export OS_USER_DOMAIN_NAME=Default
  export OS_PROJECT_NAME=demo-project
  export OS_PROJECT_DOMAIN_NAME=Default
  export OS_AUTH_URL=http://127.0.0.1:5000/v3
  export OS_REGION_NAME=RegionOne
  ```
  ```bash
  source /opt/openstack/envinfo/newuser-openrc.sh
  ```

- manager（默认域 Default，示例切到 demo-project）  
  ```bash
  export OS_AUTH_URL=http://127.0.0.1:5000/v3
  export OS_IDENTITY_API_VERSION=3
  export OS_REGION_NAME=RegionOne
  export OS_INTERFACE=internal
  export OS_USERNAME=manager
  export OS_PASSWORD=MyPass123
  export OS_USER_DOMAIN_NAME=Default
  export OS_PROJECT_NAME=demo-project
  export OS_PROJECT_DOMAIN_NAME=Default
  ```
  ```bash
  source /opt/openstack/envinfo/manager-openrc.sh
  ```

- member（默认域 Default，示例切到 demo-project）  
  ```bash
  export OS_AUTH_URL=http://127.0.0.1:5000/v3
  export OS_IDENTITY_API_VERSION=3
  export OS_REGION_NAME=RegionOne
  export OS_INTERFACE=internal
  export OS_USERNAME=member
  export OS_PASSWORD=MyPass123
  export OS_USER_DOMAIN_NAME=Default
  export OS_PROJECT_NAME=demo-project
  export OS_PROJECT_DOMAIN_NAME=Default
  ```
  ```bash
  source /opt/openstack/envinfo/member-openrc.sh
  ```

## 2. 切换用户与查看当前身份
- 切换：设置（或 source 对应 openrc）新的 `OS_USERNAME/OS_PASSWORD/OS_PROJECT_NAME/...` 环境变量。
- 查看当前 OS_*：`env | grep ^OS_`
- 查看当前 token/用户/项目：`openstack token issue -f json | grep -E '"(user_id|project_id|user_name|project_name)"'`

## 3. 常见报错说明
- HTTP 401 The request you have made requires authentication：凭证无效或缺失（密码/作用域/URL 错误、token 过期、未设置 OS_*）。
- HTTP 403 Policy doesn't allow / failed scope check：策略或作用域不满足要求（需要 system/domain 作用域或角色不足）。

## 4. 用户/项目/角色常用命令
- 新建用户：`openstack user create --domain Default --password <pwd> <user>`
- 新建项目：`openstack project create --domain Default <project>`
- 给用户在项目赋角色：`openstack role add --user <user> --project <project> <role>`
- 撤销用户在项目的角色：`openstack role remove --user <user> --project <project> <role>`
- 删除用户：`openstack user delete <user>`

## 5 设定 DynamicPolicy 环境
- 将 policyDynamic.yaml 应用为 Keystone 策略：
  ```bash
  # 在容器内
  python /root/Tools/Policyset.py copy --src "/etc/openstack/policies/policyDynamic.yaml"
  service supervisor stop 2>/dev/null || true 
  service apache2 stop
  ```

- 重启容器：
  ```bash
  sudo docker start openstack-policy-detection
  sudo docker exec -it openstack-policy-detection bash
  source /opt/openstack/envinfo/admin-openrc.sh
  ```

- 为新用户在两个项目设置 reader 角色：
  ```bash
  openstack role add --user newuser --project admin reader
  openstack role assignment list --user newuser --project admin --names # 检查是否赋予角色
  openstack token issue
  openstack role add --user newuser --project demo-project reader
  openstack role assignment list --user newuser --project demo-project --names # 检查是否赋予角色
  ```

- 检查是否给newuser赋予角色：
  ```bash
 
  openstack role assignment list --user newuser --project demo-project --names # 检查是否赋予角色

  ```

- 运行建图、授权信息获取函数：
  ```bash
  neo4j start
  source /opt/openstack/envinfo/admin-openrc.sh # RoleGrantInfo 需要 admin 凭证
  python /root/Tools/RoleGrantInfo.py
  cd /root/policy-fileparser
  python run_graph_pipeline.py --policy-file "/etc/openstack/policies/policyDynamic_graphparser.yaml"
  ```  

- 编辑conf文件；
nano /etc/keystone/keystone.conf
# 如果注释policy路径中相关的三行（policy文件路径两行），让policy不生效
# 千万不要启动enforce_scope


## 6 测试自建manager 环境
- 将 test1221.yaml 应用为 Keystone 策略：
  ```bash
  # 在容器内
  python /root/Tools/Policyset.py copy --src "/etc/openstack/policies/test1221.yaml"
  service supervisor stop 2>/dev/null || true 
  service apache2 stop
  ```

- 重启容器：
  ```bash
  sudo docker start openstack-policy-detection
  sudo docker exec -it openstack-policy-detection bash
  source /opt/openstack/envinfo/admin-openrc.sh
  env | grep ^OS_ # 查看当前用户
  openstack role assignment list --user manager --project demo-project --names # 查看是否赋予用户manager的角色manager（应该会显示）
  neo4j start  # 其他需要更新的
  ```

- 切换用户manager：
  ```bash
  export OS_AUTH_URL=http://127.0.0.1:5000/v3
  export OS_IDENTITY_API_VERSION=3
  export OS_REGION_NAME=RegionOne
  export OS_INTERFACE=internal
  export OS_USERNAME=manager
  export OS_PASSWORD=MyPass123
  export OS_USER_DOMAIN_NAME=Default
  export OS_PROJECT_NAME=demo-project
  export OS_PROJECT_DOMAIN_NAME=Default
  openstack token issue
  ```

- 对比测试一下，切换newuser：
  ```bash
  export OS_USERNAME=newuser
  export OS_PASSWORD=MyPass123
  export OS_USER_DOMAIN_NAME=Default
  export OS_PROJECT_NAME=demo-project
  export OS_PROJECT_DOMAIN_NAME=Default
  export OS_AUTH_URL=http://127.0.0.1:5000/v3
  export OS_REGION_NAME=RegionOne
  openstack token issue

  ```

source /opt/openstack/envinfo/admin-openrc.sh
python /root/Tools/Policyset.py copy --src "/etc/openstack/policies/LevelMisConf.yaml"
python /root/policy-fileparser/run_graph_pipeline.py --policy-file "/etc/openstack/policies/LevelMisConf.yaml"
