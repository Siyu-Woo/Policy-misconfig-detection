
# 基础脚本
1. **宿主机初始化程序[宿主机执行]**
```bash
cd "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection"
sudo ./Tools/script/HostInitial.sh  # 一定要sudo
```

2. **容器初始化Openstack**
```bash
/root/Tools/script/OpenStackInitial.sh
```

3. **新建、删除、罗列用户**
```bash
/root/Tools/script/UserSet.sh # 新建所有默认用户
/root/Tools/script/UserSet.sh --newuser  # 指定需要新增的用户
/root/Tools/script/UserSet.sh --delete # 删除所有默认用户（除了admin）
/root/Tools/script/UserSet.sh --delete --newuser # 删除指定用户
/root/Tools/script/UserSet.sh --list # 罗列用户
```

4. **新建、删除、罗列角色**
```bash
# 角色
/root/Tools/script/RoleSet.sh --list
/root/Tools/script/RoleSet.sh --role test1 --role test2 # 注意已绑定角色无法删除
/root/Tools/script/RoleSet.sh --delete --role test1
```

5. **新建、删除、罗列域**
```bash
/root/Tools/script/ProjectSet.sh --list
/root/Tools/script/ProjectSet.sh --project test1 --project test2
/root/Tools/script/ProjectSet.sh --delete --project test1
```

5. **在指定project授予、撤销user指定role**
```bash
/root/Tools/script/RoleGrant.sh --add --user newuser --project demo-project --role reader
/root/Tools/script/RoleGrant.sh --remove --user newuser --project demo-project --role reader
/root/Tools/script/RoleGrant.sh --list --user newuser --project demo-project # 汇总当前 user 在指定 project 的 role
```

6. **允许指定当前用户、域，切换信息**
```bash
source /root/Tools/script/CurrentUserSet.sh # 默认切回admin
source /root/Tools/script/CurrentUserSet.sh --user newuser
source /root/Tools/script/CurrentUserSet.sh --user newuser --project demo-project
source /root/Tools/script/CurrentUserSet.sh --project demo-project
env | grep ^OS_ # 验证当前信息
```

7. **导入新Policy文件，重启服务【宿主机执行】**
```bash
sudo /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/Tools/script/PolicySet.sh
```

8. **捕捉日志并解析**
```bash
/root/Tools/script/LogParse.sh # 解析keystone日志
/root/Tools/script/LogParse.sh --clear-log # 清空keystone日志
```

9. **清空 Neo4j 策略图**
```bash
/root/Tools/script/Neo4jClear.sh
```



# 维护脚本
1. **重启Keystone/apache2[宿主机执行]**
```bash
cd "/home/wusy/LabProj/CloudPolicy/Policy misconfig detection"
sudo ./Tools/script/keystoneRestart.sh  # 一定要sudo
```

# 测试脚本
## 项目1
1. **初始化环境**
/root/Tools/script/OpenStackInitial.sh
2. **导入配置文件，解析目录**
