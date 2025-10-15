#!/bin/bash
set -e

# 创建日志目录
mkdir -p /var/log/openstack
mkdir -p /opt/openstack/envinfo

# 确保服务状态目录存在
mkdir -p /var/lib/openstack/state

# 尝试恢复服务状态
if [ -f "/opt/openstack/scripts/restore-state.sh" ]; then
    echo "尝试恢复服务状态..."
    bash /opt/openstack/scripts/restore-state.sh
fi

# 检查是否已初始化
if [ -f "/var/lib/openstack/state/initialized" ]; then
    echo "OpenStack已初始化，跳过初始化步骤"
    exit 0
fi

# 配置MySQL
echo "配置MySQL..."
service mysql start || true
sleep 5

# 设置MySQL root密码
MYSQL_ROOT_PASSWORD="openstack"
mysqladmin -u root password "$MYSQL_ROOT_PASSWORD" || true

# 创建数据库
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS keystone;"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS nova;"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS nova_api;"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS nova_cell0;"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS placement;"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS glance;"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS neutron;"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS cinder;"

# 创建数据库用户并授权
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE USER IF NOT EXISTS 'keystone'@'localhost' IDENTIFIED BY 'keystone';"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'localhost';"

mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE USER IF NOT EXISTS 'nova'@'localhost' IDENTIFIED BY 'nova';"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "GRANT ALL PRIVILEGES ON nova.* TO 'nova'@'localhost';"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "GRANT ALL PRIVILEGES ON nova_api.* TO 'nova'@'localhost';"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "GRANT ALL PRIVILEGES ON nova_cell0.* TO 'nova'@'localhost';"

mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE USER IF NOT EXISTS 'placement'@'localhost' IDENTIFIED BY 'placement';"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "GRANT ALL PRIVILEGES ON placement.* TO 'placement'@'localhost';"

mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE USER IF NOT EXISTS 'glance'@'localhost' IDENTIFIED BY 'glance';"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "GRANT ALL PRIVILEGES ON glance.* TO 'glance'@'localhost';"

mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE USER IF NOT EXISTS 'neutron'@'localhost' IDENTIFIED BY 'neutron';"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "GRANT ALL PRIVILEGES ON neutron.* TO 'neutron'@'localhost';"

mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE USER IF NOT EXISTS 'cinder'@'localhost' IDENTIFIED BY 'cinder';"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "GRANT ALL PRIVILEGES ON cinder.* TO 'cinder'@'localhost';"
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "FLUSH PRIVILEGES;"

# 配置RabbitMQ
echo "配置RabbitMQ..."
service rabbitmq-server start || true
sleep 5
rabbitmqctl add_user openstack openstack || true
rabbitmqctl set_permissions openstack ".*" ".*" ".*" || true

# 配置Memcached
echo "配置Memcached..."
service memcached start || true

# 配置Keystone
echo "配置Keystone..."
# 生成Keystone配置文件
cat > /etc/keystone/keystone.conf << EOF
[DEFAULT]
log_dir = /var/log/keystone
use_stderr = true

[database]
connection = mysql+pymysql://keystone:keystone@localhost/keystone

[token]
provider = fernet

[cache]
backend = dogpile.cache.memcached
enabled = true
memcache_servers = localhost:11211
EOF

# 初始化Keystone数据库
su -s /bin/bash keystone -c "keystone-manage db_sync"

# 初始化Fernet密钥
keystone-manage fernet_setup --keystone-user keystone --keystone-group keystone
keystone-manage credential_setup --keystone-user keystone --keystone-group keystone

# 设置管理员密码和相关信息
ADMIN_PASS="admin"
DEMO_PASS="demo"
SERVICE_PASS="service"
ADMIN_URL="http://localhost:5000/v3"
PUBLIC_URL="http://localhost:5000/v3"
INTERNAL_URL="http://localhost:5000/v3"
REGION="RegionOne"

# 执行bootstrap
keystone-manage bootstrap --bootstrap-password "$ADMIN_PASS" \
  --bootstrap-admin-url "$ADMIN_URL" \
  --bootstrap-internal-url "$INTERNAL_URL" \
  --bootstrap-public-url "$PUBLIC_URL" \
  --bootstrap-region-id "$REGION"

# 重启Apache服务
service apache2 restart

# 设置环境变量
export OS_USERNAME=admin
export OS_PASSWORD="$ADMIN_PASS"
export OS_PROJECT_NAME=admin
export OS_USER_DOMAIN_NAME=Default
export OS_PROJECT_DOMAIN_NAME=Default
export OS_AUTH_URL="$ADMIN_URL"
export OS_IDENTITY_API_VERSION=3
export OS_IMAGE_API_VERSION=2

# 创建服务项目
openstack project create --domain default --description "Service Project" service

# 创建demo项目和用户
openstack project create --domain default --description "Demo Project" demo
openstack user create --domain default --password "$DEMO_PASS" demo
openstack role create user
openstack role add --project demo --user demo user

# 创建OpenStack服务
openstack service create --name keystone --description "OpenStack Identity" identity
openstack service create --name nova --description "OpenStack Compute" compute
openstack service create --name placement --description "OpenStack Placement" placement
openstack service create --name glance --description "OpenStack Image" image
openstack service create --name neutron --description "OpenStack Networking" network
openstack service create --name cinder --description "OpenStack Block Storage" volume

# 创建服务端点
openstack endpoint create --region "$REGION" identity public "$PUBLIC_URL"
openstack endpoint create --region "$REGION" identity internal "$INTERNAL_URL"
openstack endpoint create --region "$REGION" identity admin "$ADMIN_URL"

# 创建其他服务的端点（简化版本）
for service in compute placement image network volume; do
  openstack endpoint create --region "$REGION" "$service" public "http://localhost:8000/$service"
  openstack endpoint create --region "$REGION" "$service" internal "http://localhost:8000/$service"
  openstack endpoint create --region "$REGION" "$service" admin "http://localhost:8000/$service"
done

# 创建admin-openrc.sh文件
cat > /opt/openstack/envinfo/admin-openrc.sh << EOF
export OS_USERNAME=admin
export OS_PASSWORD=$ADMIN_PASS
export OS_PROJECT_NAME=admin
export OS_USER_DOMAIN_NAME=Default
export OS_PROJECT_DOMAIN_NAME=Default
export OS_AUTH_URL=$ADMIN_URL
export OS_IDENTITY_API_VERSION=3
export OS_IMAGE_API_VERSION=2
EOF

# 创建demo-openrc.sh文件
cat > /opt/openstack/envinfo/demo-openrc.sh << EOF
export OS_USERNAME=demo
export OS_PASSWORD=$DEMO_PASS
export OS_PROJECT_NAME=demo
export OS_USER_DOMAIN_NAME=Default
export OS_PROJECT_DOMAIN_NAME=Default
export OS_AUTH_URL=$PUBLIC_URL
export OS_IDENTITY_API_VERSION=3
export OS_IMAGE_API_VERSION=2
EOF

# 创建clouds.yaml文件
cat > /opt/openstack/envinfo/clouds.yaml << EOF
clouds:
  openstack:
    auth:
      auth_url: $ADMIN_URL
      username: admin
      password: $ADMIN_PASS
      project_name: admin
      project_domain_name: Default
      user_domain_name: Default
    region_name: $REGION
    identity_api_version: 3
    image_api_version: 2
EOF

# 创建basic_info文件，包含所有用户和密码信息
cat > /opt/openstack/envinfo/basic_info << EOF
# 容器用户信息
容器root密码: openstack
容器openstack用户密码: 无密码 (sudo无需密码)

# OpenStack用户信息
管理员用户: admin
管理员密码: $ADMIN_PASS
演示用户: demo
演示用户密码: $DEMO_PASS
服务用户密码: $SERVICE_PASS

# 数据库信息
MySQL root密码: $MYSQL_ROOT_PASSWORD
Keystone数据库用户: keystone
Keystone数据库密码: keystone
Nova数据库用户: nova
Nova数据库密码: nova
Placement数据库用户: placement
Placement数据库密码: placement
Glance数据库用户: glance
Glance数据库密码: glance
Neutron数据库用户: neutron
Neutron数据库密码: neutron
Cinder数据库用户: cinder
Cinder数据库密码: cinder

# RabbitMQ信息
RabbitMQ用户: openstack
RabbitMQ密码: openstack

# 项目信息
admin项目: 管理项目
service项目: 服务项目
demo项目: 演示项目

# 服务信息
已创建的服务: keystone, nova, placement, glance, neutron, cinder

# 角色信息
admin: 管理员角色
user: 普通用户角色
EOF

# 标记初始化完成
touch /var/lib/openstack/state/initialized
echo "OpenStack初始化完成"

# 复制重要配置文件到持久化存储
cp -r /etc/keystone /var/lib/openstack/state/
cp -r /etc/nova /var/lib/openstack/state/
cp -r /etc/glance /var/lib/openstack/state/
cp -r /etc/neutron /var/lib/openstack/state/
cp -r /etc/cinder /var/lib/openstack/state/

exit 0
