# Tools 目录说明

本目录提供多种辅助脚本，供策略解析/检测流水线调用。

## 1. CheckOutput.py
- **功能**：统一的错误输出模块，通过 `PolicyCheckReporter` 按照固定格式输出 `fault policy rule / fault type / fault info / recommendation`。统一的策略检查输出模块，调用 `PolicyCheckReporter` 可以把检测到的错误编号、策略名称、错误信息、整改建议打印到终端，用于 run_graph_pipeline.py 中的重复策略告警等场景。
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
- **功能**：维护敏感权限 CSV（默认： `/root/policy-fileparser/data/assistfile/sensitive_permissions.csv`），支持查看、添加、更新、删除记录。
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

## 3. api_requester.py
- **功能**：快速发起指定 OpenStack CLI 命令，支持通过命令行覆盖 OS_* 凭证，默认执行 `openstack user list`。
- **输入**：`--api "openstack project list"` 等；可选 `--username/--password/--project/--user-domain/--project-domain/--auth-url/--region/--token` 用于切换身份。
- **输出**：命令执行结果直接打印到终端。
- **路径**：`Tools/api_requester.py`
- **示例**：
  ```bash
  python Tools/api_requester.py
  python Tools/api_requester.py --api "openstack project list"
  python Tools/api_requester.py --api "openstack user list" \
    --username demo --password secret --project demo \
    --user-domain Default --project-domain Default --auth-url http://127.0.0.1:5000/v3
  ```

## 4. RoleGrantInfo.py
- **功能**：收集用户/项目/角色及授权关系，生成 `userinfo.csv`、`projectinfo.csv`、`roleinfo.csv` 和 `rolegrant.csv`（均位于 `/root/policy-fileparser/data/assistfile/envinfo`）。并且能够检查当前用户是否都有对应的openrc.sh文件
- **输入**：无命令行参数，直接运行依赖当前 OS_* 凭证调用 `openstack` CLI。
- **输出**：CSV 文件写入 `data/assistfile/envinfo` 目录；终端打印总记录数，权限不足时提示使用 admin 凭证。
- **路径**：`Tools/RoleGrantInfo.py`
- **示例**：
  ```bash
  python /root/Tools/RoleGrantInfo.py
  # 生成的文件：userinfo.csv、projectinfo.csv、roleinfo.csv、rolegrant.csv（均位于 data/assistfile/EnvInfo）
  ```

## 5. extract_keystone_rbac.py
- **功能**：从 keystone 日志中提取 RBAC 授权记录，输出 CSV（时间、API、project_name、user_name、用户/项目 ID、system_scope、domain、授权结果）。
- **输入**：默认读取 `/var/log/keystone/keystone.log`，可用 `--log` 指定。
- **输出**：默认写入 `/root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv`，可用 `--output` 指定；末尾附生成时间注释。
- **依赖**：`/root/policy-fileparser/data/assistfile/EnvInfo/userinfo.csv`、`projectinfo.csv`（用于 ID→name 映射，未命中填充 UKUser{n}/UKProj{n}）。
- **路径**：`Tools/extract_keystone_rbac.py`
- **示例**：
  ```bash
  python /root/Tools/extract_keystone_rbac.py
  python /root/Tools/extract_keystone_rbac.py --log /var/log/keystone/keystoneCollect.log --output /root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv
  ```

## 6. Policyset.py
- **功能**：管理 Keystone 策略文件，支持复制策略、添加/合并策略规则、删除策略、导出策略、禁用自定义策略。
- **输入**：子命令模式：
  - `copy --src <file>`：将指定策略文件复制到 `/etc/keystone/keystone_policy.yaml`（默认 src 为 `/root/policy-fileparser/policy.yaml`）。
  - `add --name <policy> [--role <role>] [--project <project_id>]`：为策略新增条件，若已存在则 `(原规则) or (新条件)` 合并。
  - `delete --name <policy>`：删除指定策略条目。
  - `export --dst <path>`：导出 `/etc/keystone/keystone_policy.yaml` 到指定路径（推荐 `/etc/openstack/policies/keystone_policy_export.yaml`）。
  - `disable`：修改 `keystone.conf` 清空 `[oslo_policy] policy_file`，回退默认策略。
- **输出**：终端提示操作结果，结束时提示重启 Keystone（Apache）。
- **路径**：`Tools/Policyset.py`
- **示例**：
  ```bash
  # 复制策略文件
  python /root/Tools/Policyset.py copy --src /root/policy-fileparser/policy.yaml # 默认文件夹下文件
  python /root/Tools/Policyset.py copy --src /etc/openstack/policies/TestPolicyFiles/policyB.yaml # 指定测试文件夹下文件

  # 为策略添加条件
  python /root/Tools/Policyset.py add --name identity:list_projects --role reader --project "%(project_id)s" # 注意有括号在输入命令行时候需要加引号

  # 删除策略
  python /root/Tools/Policyset.py delete --name identity:list_projects

  # 导出策略
  python /root/Tools/Policyset.py export --dst /etc/openstack/policies/keystone_policy_export.yaml

  # 禁用自定义策略，回退默认
  python /root/Tools/Policyset.py disable
  ```
- 注意，如果使用policy版本内容有：DEMO_PROJECT_ID ，需要终端输入一次这个DEMO_PROJECT_ID = b5c386f2b477440ba83fc0ca0500c2bb
