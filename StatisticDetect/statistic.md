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
