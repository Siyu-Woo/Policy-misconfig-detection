## 1. StatisticDetect/StatisticCheck.py
- **功能**：连接 Neo4j 图库，对策略图执行统计检测：包括 role/system_scope 通配符、敏感权限限定范围、敏感权限错误角色等检查，并调用 `CheckOutput` 输出错误码 4~7。
- **输入**：默认连接参数 `bolt://localhost:7687 / neo4j / Password`，可通过 `--neo4j-uri/--neo4j-user/--neo4j-password` 覆盖；高权限列表通过 `--perm-file` 指定（默认 `data/assistfile/sensitive_permissions.csv`）。
- **输出**：命令行提示检测结果、若发现问题则按错误码打印详细说明。
- **示例**：
  ```bash
  python StatisticDetect/StatisticCheck.py \
    --neo4j-uri bolt://localhost:7687 \
    --neo4j-user neo4j \
    --neo4j-password Password
  ```

## 2. UnkownStatisticCheck
 -**(StatisticDetect/UnkownStatisticCheck.py)**：基于策略图统计高/低权限角色占比，输出 `RoleStatistic{时间}.csv` 到 `/root/policy-fileparser/data/assistfile/`。脚本读取 `/root/policy-fileparser/data/assistfile/projectinfo.csv` 将 project_id 映射为 project_name，并默认使用 `/root/policy-fileparser/data/assistfile/role_level.json` 管理高低权限角色集合。  
  - 输入：Neo4j 连接信息；projectinfo.csv；role_level.json（可通过命令行维护）。  
  - 输出：统计 CSV；并输出错误码 12/13（高低权限错配/敏感权限错配）。  
  - 运行命令（容器内）：  
    ```bash
    cd /root/StatisticDetect
    python /root/StatisticDetect/UnkownStatisticCheck.py check \
      --neo4j-uri bolt://localhost:7687 \
      --neo4j-user neo4j \
      --neo4j-password Password
    ```
  - 角色集合管理示例（容器内）：  
    ```bash
    python /root/StatisticDetect/UnkownStatisticCheck.py roles --level high --list
    python /root/StatisticDetect/UnkownStatisticCheck.py roles --level high --add managerF
    python /root/StatisticDetect/UnkownStatisticCheck.py roles --level low --remove memberE
    ```

## 3. Dynamic Detection
- **Authorization_scope_check (DynamicDetect/Authorization_scope_check.py)**：基于 RBAC 审计日志统计 `{api, user, role, project}` 使用情况，生成 `rbac_audit_keystone_temp.csv`，并结合 Neo4j 检测“授权过宽/未被使用”的策略（错误码 10/11）。默认读取 `/root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv` 与 `/root/policy-fileparser/data/assistfile/rolegrant.csv`。  
  - 运行命令（容器内）：  
    ```bash
    cd /root/DynamicDetect
    python Authorization_scope_check.py \
      --neo4j-uri bolt://localhost:7687 \
      --neo4j-user neo4j \
      --neo4j-password Password
    ```