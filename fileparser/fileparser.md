# fileparser 模块说明

本文档概述 `fileparser` 目录中与图构建相关的六个脚本：`policypreprocess.py`、`policy_parser.py`、`openstackpolicygraph.py`、`openstackgraph.py`、`run_graph_pipeline.py` 与 `PolicyGen.py`，并整理它们的输入/输出、依赖关系、Neo4j 的数据结构以及策略文件路径。

## 1. 关键脚本的功能、输入与输出

### policypreprocess.py
- **功能**：读取 OpenStack policy 文件，展开 `rule:<alias>` 引用，并记录每条策略在原始文件中的来源，以便后续图谱节点附带文件/行号信息。
- **输入**：策略文件路径（YAML/行格式均可）。
- **输出**：字典 `{policy_name: {"expression": expanded_expression, "file": path, "lines": [...]}}`，其中 `expression` 是展开后的逻辑串，`file` 记录文件路径，`lines` 记录策略在文件中的行号（可多行）。

### policy_parser.py
- **功能**：使用 `oslo.policy` 解析器将字符串表达式转换为 AST，提取最小授权单元（近似 DNF），并可写入策略数据库。
- **输入**：来自预处理模块的字典项（策略名 + 展开后的表达式）。
- **输出**：每条策略的最小匹配单元 `List[Dict[str, List[str]]]`，字段限制于 `{domain, project, role, system_scope, user}`，可通过 `store_policy_to_database` 逐条落库。

### openstackpolicygraph.py
- **功能**：把解析后的策略结果写入 Neo4j，形成“策略子图”。自动复用重复规则节点，并为不同条件类型生成对应标签与 `REQUIRES_*` 关系。
- **输入**：策略字典 `Dict[str, List[str]]`，每个值是该策略的规则表达式列表（来自 policy_parser 的结果或直接传入的字符串）。
- **输出**：在 Neo4j 中创建 `PolicyNode`、`RuleNode`、`ConditionNode` 三类节点以及 `HAS_RULE`、`REQUIRES_*` 关系。`get_graph_statistics()` 可回读统计信息。

### openstackgraph.py
- **功能**：使用 Keystone Admin API 读取当前 OpenStack 环境的用户、角色、项目及角色分配，基于 `role_assignments` 合成 Token 层（支持共享 / 独享 token），并把 system scope 也拆成节点写入 Neo4j，形成“身份子图”。提供清理、生成测试数据等附加能力。
- **输入**：OpenStack 管理员凭据（在文件顶部 `OS_CONFIG` 配置）和 Neo4j 连接信息。
- **输出**：`User`、`Token`、`Role`、`SystemScope` 节点，以及 `HAS_TOKEN`、`GRANTS`、`HAS_SYSTEM_SCOPE` 关系；控制台还会输出 token-role-scope 映射及共享统计。

### run_graph_pipeline.py
- **功能**：统一入口脚本，串联 CLI 调用、身份子图构建与策略子图构建，并内置策略重复检测模块。
- **输入**：命令行参数（服务列表、策略文件路径、Neo4j 连接、是否跳过身份/策略阶段、输出控制开关等）。
- **输出**：调用 OpenStack CLI 进行凭证检查；若未跳过则先执行 `openstackgraph` 写入身份子图，再调用 `policypreprocess + policy_parser + openstackpolicygraph` 写入策略子图；同时输出策略重复/冲突检测报告及统计信息（可通过命令行开关控制显示）。
- **策略重复检查**：脚本在建图前会检测（1）同一个 API 是否被多条策略重复定义；（2）单个策略内部是否包含重复规则。若发现问题，会通过 `Tools/CheckOutput.py` 模块输出对应的错误码、问题策略以及合并建议，便于后续修订策略文件。

### PolicyGen.py
- **功能**：提供三类生成能力：（1）从图数据库导出当前策略矩阵 CSV；（2）从 CSV 生成策略 YAML；（3）从图数据库直接生成策略 YAML。
- **输入**：
  - graph-to-csv：Neo4j 连接参数，项目映射 `data/assistfile/projectinfo.csv`（可自定义路径）。
  - csv-to-yaml：多个 CSV 文件及对应 project 名称列表（允许最多一个 project 为空）；读取 `data/assistfile/projectinfo.csv` 将 project_name 转换为 UUID。
  - graph-to-yaml：Neo4j 连接参数；读取 `data/assistfile/projectinfo.csv` 将表达式中的 `project:<name>` 转换为 UUID。
- **输出**：
  - graph-to-csv：输出 `NowPermit.csv` 与 `NowPermitin{project_name}.csv`；第一列为 api_name，第一行是 role。
  - csv-to-yaml / graph-to-yaml：输出 `Policy{时间}.yaml`（或指定文件名）。
- **注意事项**：
  - `csv-to-yaml` 要求所有 CSV 的 API 行与 role 列一致，否则报错。
  - `csv-to-yaml` 只能有一个 CSV 不指定 project。
  - 若 `data/assistfile/projectinfo.csv` 中不存在指定 project_name，会直接报错。

## 2. 文件之间的依赖关系
1. `run_graph_pipeline.py` 调用 `policypreprocess.process_policy_file()` 读取并展开策略。
2. 其结果被 `policy_parser.PolicyRuleParser` 读取：`extract_rule_definitions()` 先记录别名，再对非别名策略调用 `parse_single_policy()` 与 `_extract_minimal_units()`，生成多条逻辑表达式。
3. `openstackpolicygraph.PolicyGraphCreator` 消耗这些表达式列表，构建策略子图。
4. 同一脚本根据参数决定是否调用 `openstackgraph.OpenStackNeo4jManager`，读取实际用户/角色并生成身份子图。
5. 两个子图写入的是同一个 Neo4j 实例，因此策略约束与真实身份可在后续查询中进行路径关联。`run_graph_pipeline.py` 即是整个流程的 orchestrator，其他脚本则是被动模块。

## 3. 图数据库中的数据结构与样例
### 节点类型
- `PolicyNode`：`{id: 'identity:list_users', type: 'identity', name: 'list_users', policyfile: '/etc/.../keystone-policy.yaml', policyline: [42]}`。
- `RuleNode`：`{id: 'rule:rule12', name: 'rule12', expression: 'role:reader and system_scope:all', normalized_expression: 'role:reader and system_scope:all'}`。
- `ConditionNode`：标签随条件类型变化（如 `RoleCondition`、`SystemScopeCondition`），属性 `{id: 'role:reader', type: 'role', name: 'reader'}`。
- `User`：`{id: 'ad7d...', name: 'alice', email: 'alice@example.com'}`。
- `Token`：`{id: '8c2f-uuid', shared: False}`；共享 token 会设置 `shared: True`，且可连接多个用户。
- `Role`：`{id: '9b69...', name: 'member'}`。
- `SystemScope`：`{name: 'all'}` 或 `{'name': 'domain'}` 等，表示 token 被授予的 system-level 作用域。

### 关系类型
- `(:PolicyNode)-[:HAS_RULE]->(:RuleNode)`
- `(:RuleNode)-[:REQUIRES_ROLE|REQUIRES_PROJECT|...]->(:ConditionNode)`
- `(:User)-[:HAS_TOKEN]->(:Token)`
- `(:Token)-[:GRANTS]->(:Role)`
- `(:Token)-[:HAS_SYSTEM_SCOPE]->(:SystemScope)`

### 样例结构
```
(:PolicyNode:PolicyIdentity {id: 'identity:list_users'})
  -[:HAS_RULE]->(:RuleNode {id: 'rule:rule5'})
    -[:REQUIRES_ROLE]->(:ConditionNode:RoleCondition {id: 'role:reader'})
    -[:REQUIRES_SYSTEM_SCOPE]->(:ConditionNode:SystemScopeCondition {id: 'system_scope:all'})
(:User {id: 'f3c...'})-[:HAS_TOKEN]->(:Token {id: '1a2b...', shared: false})
  -[:GRANTS]->(:Role {id: 'd8e...', name: 'reader'})
  -[:HAS_SYSTEM_SCOPE]->(:SystemScope {name: 'all'})
```
该样例展示了策略 list_users 对应的逻辑条件与某个真实用户通过 token 拥有 reader 角色，两条路径可在 Neo4j 中组合查询以验证访问链路。

## 4. Policy 文件路径
- `policypreprocess.process_policy_file()` 接受任意给定路径；`run_graph_pipeline.py` 的 `--policy-files` 参数默认值为 `/etc/openstack/policies/keystone-policy.yaml`，可通过逗号分隔传入多个策略文件。
- 仓库内提供了示例 `fileparser/keystone-policy.yaml`，可直接用作本地调试或在 `--policy-files` 中引用（例如：`python run_graph_pipeline.py --policy-files ./fileparser/keystone-policy.yaml`）。
- 若部署在容器中，请保证上述路径在容器的 `/etc/openstack/policies/` 下被挂载，或在运行脚本时传入真实的策略文件绝对路径。

## 5. 运行命令示例
- **指定策略文件解析**  
  在仓库根目录运行：  
  ```bash
  python fileparser/run_graph_pipeline.py \
    --policy-files ./fileparser/keystone-policy.yaml \
    --neo4j-uri bolt://localhost:7687 \
    --neo4j-user neo4j \
    --neo4j-password Password \
    --skip-identity
  ```  
  其中 `--policy-files` 可替换成任意绝对/相对路径，`--skip-identity` 表示仅加载策略子图；如需连同身份子图一起写入，则去掉该参数并保证 OpenStack Admin 凭据可用。

- **清空 / 加载 / 读取图数据库**  
  ```bash
  # 1) 清空 Neo4j（仅 Policy 子图） 
  python - <<'PY'
  from openstackpolicygraph import PolicyGraphCreator
  graph = PolicyGraphCreator("bolt://localhost:7687", "neo4j", "Password")
  graph.clear_database()
  graph.close()
  PY

  # 2) 重新加载（运行完整脚本）
  python fileparser/run_graph_pipeline.py --policy-files ./fileparser/keystone-policy.yaml

  # 3) 读取统计信息
  python - <<'PY'
  from openstackpolicygraph import PolicyGraphCreator
  graph = PolicyGraphCreator("bolt://localhost:7687", "neo4j", "Password")
  print(graph.get_graph_statistics())
  graph.close()
  PY
  ```
  
  根据需要也可以把 URI/用户名/密码替换成远程 Neo4j 的连接参数；若想专门清理 / 重新导入身份子图，可直接运行 `python /root/policy-fileparser/openstackgraph.py --cleanup` 或 `python /root/policy-fileparser/openstackgraph.py`（读取 Keystone 数据、生成 token、创建包含 SystemScope 节点的身份子图）。
- **仅输出策略检测结果**  
  ```bash
  python /root/policy-fileparser/run_graph_pipeline.py \
    --policy-files /etc/openstack/policies/keystone-policy.yaml \
    --show-check-report
  ```
  该命令会执行完整解析流程，但只打印“策略重复检测”报告与步骤提示；若需额外查看 token 状态或策略解析详情，可叠加 `--show-token-info`、`--show-policy-debug`、`--show-policy-statistic` 等开关。

## 6. 命令行输出控制
`run_graph_pipeline.py` 默认会输出完整的执行日志；为了只关注特定阶段，可额外添加下列开关来开启或关闭不同的详尽信息（未打开某个开关时，该阶段只会打印“第 X 步开始/完成”）：

- `--show-token-info`：输出读取 token 及生成映射时的详细信息。
- `--show-policy-debug`：在解析每条策略时打印原始表达式及解析结果。
- `--show-check-report`：打印策略重复/冲突检查的详细报告（默认只记录计数）。
- `--show-policy-statistic`：写入策略子图后打印 Neo4j 中的节点/关系统计。

例如仅关注错误检测，可运行：
```bash
python /root/policy-fileparser/run_graph_pipeline.py --show-check-report
```
如需同时查看 token 摘要，可叠加 `--show-token-info`，其它阶段命令类似。

- **PolicyGen.py 生成 CSV / YAML**  
  ```bash
  # 1) 图数据库 -> CSV
  python /root/policy-fileparser/PolicyGen.py graph-to-csv \
    --neo4j-uri bolt://localhost:7687 \
    --neo4j-user neo4j \
    --neo4j-password Password \
    --output-dir "/etc/openstack/policies"

  # 2) CSV -> YAML（允许最多一个 project 为空）
  python /root/policy-fileparser/PolicyGen.py csv-to-yaml \
    --csv-files "/etc/openstack/policies/NowPermit.csv" "/etc/openstack/policies/NowPermitinadmin.csv" \
    --projects none admin \
    --output "/etc/openstack/policies/PolicyFromCsv.yaml"

  # 3) 图数据库 -> YAML
  python /root/policy-fileparser/PolicyGen.py graph-to-yaml \
    --neo4j-uri bolt://localhost:7687 \
    --neo4j-user neo4j \
    --neo4j-password Password \
    --output "/etc/openstack/policies/PolicyFromGraph.yaml"
  ```
