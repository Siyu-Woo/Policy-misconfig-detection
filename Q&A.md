# 问题1:
Q：这几条 openstack token issue/user list/... 同时报 500，说明 CLI 已经拿到了环境变量，但 Keystone API（http://localhost:5000/v3）在容器内返回内部错误，通常是 Keystone 服务本身没启动好或后端（数据库、memcached、Fernét key）异常，而不是 CLI 配置问题。

A：
   1. wsgi 直接跑出来的错误已经说明根因：/etc/keystone/fernet-keys/ 目录里没有密钥。Keystone 以 Fernet token provider 工作，没有密钥就无法签名/解密 token，Apache 下也就必然返回 500。
   2. 处理步骤：在 Keystone 节点上执行（需以 keystone 用户身份运行，保持目录权限正确）：
   ```bash
      keystone-manage fernet_setup --keystone-user keystone --keystone-group keystone   keystone-manage credential_setup --keystone-user keystone --keystone-group keystone
   ```
   3. 如果之前数据库还没同步完成，一并确认 keystone-manage db_sync 已成功：
   （1）确认 /etc/keystone/fernet-keys/ 与 /etc/keystone/credential-keys/ 中生成了密钥文件，权限应是 keystone:keystone，600 或 700。
   （2）重启 Keystone 的 Apache WSGI（service apache2 restart 或 apachectl graceful），然后再运行 openstack token issue / curl http://localhost:5000/v3 验证，HTTP 500 应该消失。
   （3）若还有其他 500，再按日志继续排查，但至少这一步是必要的，否则 Keystone 无法正常签发 token。


# 问题2：
Q：现在 500 已经消失，Keystone 能正常响应，只是返回了 401，说明客户端（CLI）没带上有效的管理员凭证。检查几件事：

A：
   1. 在运行 MySQL 的那台节点或容器里，直接执行 mysql -u root -p，按提示输入 root 密码即可进入；若密码为空，直接回车。
   2. 要切换到 keystone 库，进入后运行 USE keystone;；其它组件同理（USE nova;、USE glance; 等）。
   3/ keystone 数据库里连 user 表都没有，说明 Keystone 的数据库初始化（keystone-manage db_sync）从未成功执行，或者数据被清空。
   4. 先同步数据库
      ```bash
      keystone-manage db_sync
      ```
   5. 设置 bootstrap 所需环境变量（和你 export 的保持一致）：
      ```bash
      export OS_BOOTSTRAP_USERNAME=admin   export OS_BOOTSTRAP_PASSWORD=admin   export OS_BOOTSTRAP_PROJECT_NAME=admin   export OS_BOOTSTRAP_ROLE_NAME=admin   export OS_BOOTSTRAP_SERVICE_NAME=keystone   export OS_BOOTSTRAP_REGION_ID=RegionOne   export OS_BOOTSTRAP_ADMIN_URL=http://localhost:5000/v3/   export OS_BOOTSTRAP_PUBLIC_URL=http://localhost:5000/v3/   export OS_BOOTSTRAP_INTERNAL_URL=http://localhost:5000/v3/   export OS_USER_DOMAIN_NAME=Default   export OS_PROJECT_DOMAIN_NAME=Default
      ```
   6. 运行 bootstrap
   ```bash
   keystone-manage bootstrap
   ```
   7. 重新加载 admin 凭证并验证
   ```bash
   source /opt/openstack/envinfo/admin-openrc.sh    # 或 Manual 里的 export   openstack token issue
   ```

# 问题3：
Q：Mysql 表依然是空的

A：
   1. 看样子表还是空的，说明 keystone-manage db_sync 依旧在用 SQLite。请再核对 /etc/keystone/keystone.conf 的 [database] 段，确保真的改成了 MySQL，
   2. 确保容器能连到 ip:3306：在 Keystone 容器里执行 nc -vz ip 3306 或 mysql -h ip -ukeystone -p（直接回车），验证网络和账号可用。
   3. 最终改成：
   ```bash
   connection = mysql+pymysql://keystone:@localhost:3306/keystone
   keystone-manage db_sync
   ```

# 问题4：
Q：nova 服务没有注册，Keystone 的 service catalog 只有 identity，所有 CLI 调用 compute/image/network 等服务都会报 “No service … exists” 或 “<interface> endpoint … not found”，导致 openstack server list 等命令无法执行。

A：
   1. 进入容器并加载管理员环境：`docker exec -it openstack-policy-detection bash`，`source /opt/openstack/envinfo/admin-openrc.sh`。
   2. 先在数据库里插入 compute 服务记录（或直接 `openstack service create --name nova --type compute`，若 API 未 500），再对应创建 public/internal/admin 三个端点，例如：
      ```
      openstack endpoint create --region RegionOne compute public   http://localhost:8774/v2.1
      openstack endpoint create --region RegionOne compute internal http://localhost:8774/v2.1
      openstack endpoint create --region RegionOne compute admin    http://localhost:8774/v2.1
      ```
   3. 用同样方式依次注册其它组件：`openstack service create --name glance --type image`、`placement`、`cinder`（volumev3）、`neutron`（network），并为每个服务补齐三个端点（Glance: `http://localhost:9292`，Placement: `http://localhost:8778`，Cinder: `http://localhost:8776/v3/%(project_id)s`，Neutron: `http://localhost:9696`）。
   4. `openstack service list` 与 `openstack endpoint list` 应显示所有组件；若 CLI 仍查不到，重启 memcached（`service memcached restart`）或直接查看 `/var/log/keystone/keystone.log`。


# 问题5:
Q：容器无法使用宿主机代理

A：
   1. 宿主机代理查看一下监听端口；
   2. 宿主机安装socat
   3. 容器配置网络映射实现监听
   4. apt-get验证是否可以正常链接。