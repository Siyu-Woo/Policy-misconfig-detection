# Tools 目录说明

本目录提供多种辅助脚本，供策略解析/检测流水线调用。

## 1. CheckOutput.py
- **功能**：统一的错误输出模块，通过 `PolicyCheckReporter` 按照固定格式输出 `fault policy rule / fault type / fault info / recommendation`。
- **输入**：`report(error_code, policy_name=..., suggestion=..., target=...)` 等关键字参数；错误编码 1/2/3 分别表示重复策略（相同/不同规则）与重复规则，可在 `ERROR_TEMPLATES` 中扩展。
- **输出**：根据模板打印到终端，用于 `run_graph_pipeline.py` 等脚本的策略检查结果。
- **路径**：`Tools/CheckOutput.py`
- **示例**：
  ```python
  from Tools.CheckOutput import PolicyCheckReporter
  reporter = PolicyCheckReporter()
  reporter.report("1", policy_name="line 10: identity:list_users", target="line 12: identity:list_users")
  ```

## 2. SensiPermiSet.py
- **功能**：维护敏感权限 CSV（`data/assistfile/sensitive_permissions.csv`），支持查看、添加、更新、删除记录。
- **输入**：命令行参数 `view/add/update/delete`，字段包含 `--policy-name`（必填）、`--role`、`--project-name`、`--system-scope` 等，角色/项目/作用域都允许 0 个或多个值。
- **输出**：在终端提示操作结果，同时更新 CSV。
- **路径**：`Tools/SensiPermiSet.py`
- **示例**：
  ```bash
  python Tools/SensiPermiSet.py view
  python Tools/SensiPermiSet.py add --policy-name authorize_request_token \
    --role admin --project-name ProjectA --system-scope all
  python Tools/SensiPermiSet.py update --id 1 --role member --system-scope domain
  python Tools/SensiPermiSet.py delete --id 1
  ```

## 3. StatisticDetect/StatisticCheck.py
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
