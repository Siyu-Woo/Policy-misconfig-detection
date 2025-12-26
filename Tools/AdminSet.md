# 用户信息
更新时间：2025-12-25 11:11:29
- 6a4367ff14a349e69d7730a6229c46b0 (id=admin)
- cabfa0644cd8479389a17af69bea501a (id=newuser)
- f9a617d0b73f471ca54e71c91ca6876b (id=member)
- 53711b1cdc0b4ccfbbd46e0bd3caffdd (id=manager)

# 角色信息
更新时间：2025-12-25 11:11:29
- 073c72cb8ae5460a8724fd635f5f8c44 (id=admin)
- 387599c502094ff1a7a7e35e63bcb617 (id=test2)
- c818d20779d94aaf875ec08f7c9af918 (id=reader)
- e2a5cf69902540db979b80ea3d4b4816 (id=manager)
- faf75e30257d4c6fb7705dcd706888fc (id=member)

# 项目信息
更新时间：2025-12-25 11:11:29
- 938f3a5516bd40a68c730191901007e6 (id=admin)
- c451de2c774640e3a2a6841cc5cc4b6d (id=demo-project)

# 环境变量更新
- admin（密码为 `admin`，默认域 Default，默认项目：admin）
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

- newuser（默认域 Default，默认项目：demo-project）
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

- manager（默认域 Default，默认项目：demo-project）
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

- member（默认域 Default，默认项目：demo-project）
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

