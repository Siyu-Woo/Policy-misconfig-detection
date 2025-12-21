# 错误码说明文档

## 错误码 1 - repeat policy
1. **错误说明**  
   同一个 API 被多个策略重复定义且规则完全一致（例如同一 `policy` 被复制到不同位置，表达式没有任何差异）。  

2. **修改建议**  
   删除重复策略中的后续条目，仅保留一条有效策略，避免维护成本及潜在冲突。  

3. **检测代码**  
   `fileparser/run_graph_pipeline.py` 中的重复策略检测逻辑（使用 `CheckOutput` 输出错误码 1）。  

4. **错误样例**  
   `line 10: identity:list_users -> role:reader and system_scope:all`  
   `line 12: identity:list_users -> role:reader and system_scope:all`（规则完全相同）  

---

## 错误码 2 - repeat policy
1. **错误说明**  
   同一个 API 名称存在多条策略，且规则（表达式）不一致，导致策略重复且相互冲突，需要人工合并。  

2. **修改建议**  
   根据检测结果提供的建议，将多个策略的条件合并为 `xx or xx` 的形式，确保一个 API 仅维护一份策略。  

3. **检测代码**  
   `fileparser/run_graph_pipeline.py` 中的重复策略检测逻辑（规则不同的部分输出错误码 2）。  

4. **错误样例**  
   `line 15: identity:list_application_credentials -> role:reader and system_scope:all`  
   `line 20: identity:list_application_credentials -> user_id:%(user_id)s`（两个 rule 需要合并）  

---

## 错误码 3 - repeat rule
1. **错误说明**  
   单个策略解析出的多个 rule 单元中，出现了条件完全一致的组合（无论表达式写法如何），即同一条 policy 节点在图谱中生成了重复的 `ConditionNode` 组合。  

2. **修改建议**  
   根据检测输出的 `fault info` 提供的重复单元（`unit`），整理并合并策略表达式，确保每个独立的条件组合只定义一次。  

3. **检测代码**  
   `fileparser/run_graph_pipeline.py` 中的 rule 单元签名检测逻辑（根据 `_extract_minimal_units` 生成的 `unit_signature` 判断重复）。  

4. **错误样例**  
   `identity:create_user` 中拆解获得的 rule 单元包含两个完全一致的组合：  
   - unit: `role:admin AND system_scope:all`  
   - unit: `role:admin AND system_scope:all`（虽来自不同表达式片段，但组合条件相同）。  

---

## 错误码 4 - allow all role
1. **错误说明**  
   Policy 条件中允许所有角色（使用 `*`/`all` 通配符或已涵盖所有 RoleCondition），导致任何角色都能满足该策略。  

2. **修改建议**  
   精确配置 `role` 条件，限制到指定角色集合。  

3. **检测代码**  
   `StatisticDetect/StatisticCheck.py` 中 `check_wildcards` 的角色检测逻辑。  

4. **错误样例**  
   `line 25: identity:list_users -> role:*`。  

---

## 错误码 5 - No rule
1. **错误说明**  
   RuleNode 没有连接任何 ConditionNode，表示策略未设置任何限制（等价于允许所有请求）。  

2. **修改建议**  
   在策略里显式配置角色或作用域条件，避免无约束放行。  

3. **检测代码**  
   `StatisticDetect/StatisticCheck.py` 中 `check_empty_rules`。  

4. **错误样例**  
   `line 50: identity:list_service_providers` rule 为空字符串。  

---

## 错误码 6 - Scope has no restriction（敏感权限）
1. **错误说明**  
   高级别权限列表声明该 API 必须在 `system_scope` 上做限制，但策略在图中没有任何 `SystemScopeCondition`。即使策略中存在其他限制，也会被视为不符合敏感权限要求。  

2. **修改建议**  
   直接在检测输出中提供“(原始 rule 表达式) and system_scope:all”，将策略整体包裹后追加 `system_scope:all` 条件即可。  

3. **检测代码**  
   `StatisticDetect/StatisticCheck.py` 的 `check_sensitive_scopes` 方法（基于敏感权限 CSV，逐个策略确认是否存在 `REQUIRES_SYSTEM_SCOPE` 关系）。  

4. **错误样例**  
   `identity:authorize_request_token` 在 CSV 中要求 `system_scope:all`，但策略没有任何 `system_scope` 相关条件，因此输出 `fault info: system scope should setting all`，并给出 `(原策略) and system_scope:all` 的修复建议。  

---

## 错误码 7 - project has no restriction
1. **错误说明**  
   敏感权限 CSV 要求该 API 需要限定特定项目（例如 `%(project_id)s` 或具体项目名），但策略缺少 `ProjectIdCondition`，或存在与要求不匹配的其他 `project_id` 条件。  

2. **修改建议**  
   检测结果将按 `(原 rule 表达式) and project_id:%(project_id)s` 的形式给出建议，直接将输出复制到策略里即可。  

3. **检测代码**  
   `StatisticDetect/StatisticCheck.py` 的 `check_sensitive_projects` 方法，会收集 CSV 中所有 project 限制并验证策略的 `REQUIRES_PROJECT_ID` 关系是否在允许集合内。  

4. **错误样例**  
   `identity:get_project` 在 CSV 中要求 `project_id:%(project_id)s`，但当前策略未设置任何 `project_id` 条件，因此被判定为“project has no restriction”，推荐 `(role:reader) and project_id:%(project_id)s`。  

---

## 错误码 8 - {API} privileges to regular role
1. **错误说明**  
   敏感权限列表要求该 API 只能由特定角色访问，但策略未设置任何 `RoleCondition`，或存在超出白名单的角色。  

2. **修改建议**  
   根据输出提示的“Policy xxx should limit roles to [...]”限制角色集合，确保只保留 CSV 中列出的角色。  

3. **检测代码**  
   `StatisticDetect/StatisticCheck.py` 的 `check_sensitive_roles` 方法。  

4. **错误样例**  
   `identity:create_domain_config` 预期只允许 `role:admin`，当前策略未设置任何角色，检测结果提示“Policy identity:create_domain_config should limit roles to [admin]”，并输出错误码 8。  

---

## 错误码 9 - Repeat Condition
1. **错误说明**  \
   同一 Policy 节点下存在两个 Rule，其中一个 Rule 的条件集合（按 type+name 匹配）是另一个 Rule 条件集合的子集，属于冗余重复。  \

2. **修改建议**  \
   删除被判定为子集的那条 Rule，保留条件更完整的 Rule。检测输出会给出冗余 Rule 的表达式。  \

3. **检测代码**  \
   `StatisticDetect/StatisticCheck.py` 中的 `check_rule_subsets`，遍历每个 Policy 的所有 Rule 条件集合，发现子集关系即输出错误码 9。  \

4. **错误样例**  \
   `identity:list_projects` 下有两条规则：`role:admin and project_id:%(project_id)s` 与 `role:admin`。后者条件集合是前者的子集，被判定为冗余，建议删除 `role:admin` 这一条（错误码 9）。  

---

## 错误码 10 - Role or Scope Over Authorization
1. **错误说明**  
   某个 Policy 的 Rule 没有被审计日志统计到的 `{api, role, project}` 组合匹配到，说明存在“已授权但未被实际使用”的 Rule，可能授权过宽。  

2. **修改建议**  
   删除未被匹配到的 Rule（输出会给出该 Rule 的表达式）。  

3. **检测代码**  
   `DynamicDetect/Authorization_scope_check.py` 中 `check_unused_rules`。  

4. **错误样例**  
   `identity:list_users` 有两条规则，其中一条未被任何 `{role, project}` 组合匹配到，输出错误码 10 并建议删除该 Rule。  

---

## 错误码 11 - API Over Authorization
1. **错误说明**  
   某个 API 在图数据库中存在 PolicyNode，但审计日志统计结果中完全未出现该 API，说明该 API 未被实际使用但仍保留策略。  

2. **修改建议**  
   删除该 API 的完整策略（输出会给出完整策略表达式）。  

3. **检测代码**  
   `DynamicDetect/Authorization_scope_check.py` 中 `check_untracked_policies`。  

4. **错误样例**  
   `identity:list_domains` 从未在日志出现，但图中存在对应策略，输出错误码 11 并建议删除整条策略。  

---

## 错误码 12 - 高低权限错配
1. **错误说明**  
   在同一 `{API, project}` 组合下，低权限角色占比 ≥ 80% 且 < 100%，但仍包含高权限角色，说明角色层级被混用。  

2. **修改建议**  
   删除该项目中被检测到的高权限角色，并仅保留低权限角色（或重新创建低权限用户用于该 API）。  

3. **检测代码**  
   `StatisticDetect/UnkownStatisticCheck.py` 中的高低权限比例统计逻辑（错误码 12）。  

4. **错误样例**  
   `identity:list_users` 在 `demo-project` 中 80% 以上为 member，但仍包含 manager 角色。  

---

## 错误码 13 - 敏感权限错配
1. **错误说明**  
   在同一 `{API, project}` 组合下，高权限角色占比 ≥ 80% 且 < 100%，但仍包含低权限角色，说明敏感权限被授予低权限角色。  

2. **修改建议**  
   检查该 API 是否应授予低权限角色，若不应授予则移除该低权限角色。  

3. **检测代码**  
   `StatisticDetect/UnkownStatisticCheck.py` 中的高低权限比例统计逻辑（错误码 13）。  

4. **错误样例**  
   `identity:delete_user` 在 `admin` 项目中 80% 以上为 manager，但仍包含 member。  
