# OpenStack 策略解析与图谱构建模块说明文档

本文档详细说明了 `fileparser` 目录下各核心脚本的功能、数据交互流程以及最终生成的 Neo4j 图数据库模型。该模块旨在将 OpenStack 的**静态策略配置**与**动态身份/资源状态**转化为统一的图谱结构，以便进行安全路径分析。

## 1. 图数据模型 (Graph Data Schema)

系统在 Neo4j 中构建的图谱包含两个主要子图：**策略定义子图（静态）**和**身份资源子图（动态/环境）**。

graph TD
    %% 定义样式
    classDef static fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef dynamic fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef link fill:#none,stroke:#4caf50,stroke-width:2px,stroke-dasharray: 5 5;

    subgraph "静态策略定义子图 (Static Policy Graph)"
        PolicyNode("PolicyNode<br>(API动作: identity:list_users)"):::static
        RuleNode("RuleNode<br>(逻辑表达式)"):::static
        ConditionNode("ConditionNode<br>(原子条件: role:admin)"):::static
        
        PolicyNode -- "HAS_RULE" --> RuleNode
        RuleNode -- "REQUIRES_{TYPE}" --> ConditionNode
    end

    subgraph "动态身份资源子图 (Dynamic Identity Graph)"
        User("User<br>(实际用户)"):::dynamic
        Token("Token<br>(模拟/会话)"):::dynamic
        Role("Role<br>(实际角色)"):::dynamic
        
        User -- "HAS_TOKEN" --> Token
        Token -- "GRANTS" --> Role
    end

    %% 逻辑连接
    ConditionNode -. "逻辑匹配 (Logical Match)" .-> Role
    linkStyle 4 stroke:#4caf50,stroke-width:2px,fill:none;

### 1.1 策略定义子图 (Static Policy Graph)
由 `openstackpolicygraph.py` 构建，描述 `policy.yaml` 中的规则逻辑。

* **节点 (Nodes)**
    * **`PolicyNode`**: 代表具体的 API 策略动作。
        * *Labels*: `:PolicyNode`, `:Policy{Type}` (如 `:PolicyIdentity`)
        * *Properties*: `name` (如 "identity:list_users"), `type` ("identity")
    * **`RuleNode`**: 代表策略背后的逻辑规则表达式。
        * *Labels*: `:RuleNode`
        * *Properties*: `expression` (原始表达式), `normalized_expression` (归一化表达式)
    * **`ConditionNode`**: 代表规则中的最小原子条件。
        * *Labels*: `:ConditionNode`, `:{Type}Condition` (如 `:RoleCondition`, `:SystemScopeCondition`)
        * *Properties*: `type` (如 "role"), `name` (如 "admin", "reader")

* **关系 (Relationships)**
    * `(:PolicyNode)-[:HAS_RULE]->(:RuleNode)`: 策略受限于某条规则。
    * `(:RuleNode)-[:REQUIRES_{TYPE}]->(:ConditionNode)`: 规则的具体要求。
        * 例如: `[:REQUIRES_ROLE]`, `[:REQUIRES_SYSTEM_SCOPE]`, `[:REQUIRES_PROJECT]`

### 1.2 身份资源子图 (Identity & Resource Graph)
由 `openstackgraph.py` 构建，描述 OpenStack 环境中的实际用户、角色和模拟的令牌关系。

* **节点 (Nodes)**
    * **`User`**: 实际存在的用户。
        * *Properties*: `id`, `name`, `email`
    * **`Role`**: 实际存在的角色。
        * *Properties*: `id`, `name`
    * **`Token`**: (模拟节点) 代表用户持有的访问令牌，用于连接用户与权限。
        * *Properties*: `id` (UUID), `shared` (布尔值，表示是否为共享令牌)

* **关系 (Relationships)**
    * `(:User)-[:HAS_TOKEN]->(:Token)`: 用户拥有某个令牌。
    * `(:Token)-[:GRANTS]->(:Role)`: 该令牌赋予了持有者特定的角色。

---

## 2. 核心文件功能解析

### 2.1 `policypreprocess.py` (策略预处理)
**功能**: 它是解析链的入口，负责处理 `policy.yaml` 中的**引用别名**。OpenStack 策略允许定义别名（如 `"admin_required": "role:admin"`），并在其他规则中通过 `rule:admin_required` 引用。此脚本将这些引用展开为完整的逻辑表达式。

* **输入**: 原始 `policy.yaml` 文件（YAML 或 Key:Value 行格式）。
* **核心逻辑**:
    * `read_yaml_and_split_by_colon`: 读取文件并转为字典。
    * `resolve_rule_references`: 递归查找并替换值中的 `rule:xxx` 字符串，将其替换为被引用规则的实际表达式，并加上括号以保证逻辑优先级。
* **输出**: 解析后的字典 `{policy_name: full_expanded_expression_string}`。

### 2.2 `policy_parser.py` (策略逻辑解析)
**功能**: 它是解析引擎的核心。负责将预处理后的字符串表达式解析为结构化的逻辑单元，并验证字段的合法性。它利用了 OpenStack 原生库 `oslo.policy` 来理解 `and`、`or`、`not` 等逻辑。

* **输入**: 预处理后的策略表达式字符串。
* **核心逻辑**:
    * `parse_policy_expression`: 调用 `_parser.parse_rule` 将字符串转为 AST (抽象语法树) 对象。
    * `_extract_minimal_units`: 将复杂的逻辑树（AND/OR/NOT）转换为 **DNF (析取范式)** 的形式，即提取出“最小满足条件集合”。
        * 例如 `(role:admin or role:member) and system:all` 会被拆解为两个单元：`[{role:admin, system:all}, {role:member, system:all}]`。
    * 验证字段是否属于 `VALID_DB_FIELDS` (domain, project, role, system_scope, user)。
* **输出**: 结构化的最小匹配单元列表 `List[Dict[str, List[str]]]`，可供数据库存储或图谱生成使用。

### 2.3 `openstackpolicygraph.py` (策略图谱构建)
**功能**: 将解析后的策略逻辑写入 Neo4j 数据库，构建**静态策略子图**。

* **输入**: 策略字典（通常来自 `policy_parser` 或预处理结果）。
* **核心逻辑**:
    * 连接 Neo4j 数据库。
    * `create_policy_graph`:
        1.  创建 `PolicyNode`（策略动作）。
        2.  对每个策略的表达式进行归一化（`normalize_expression`）。
        3.  创建 `RuleNode`，并建立 `(:PolicyNode)-[:HAS_RULE]->(:RuleNode)`。
        4.  解析表达式中的原子条件（如 `role:admin`），创建 `ConditionNode`。
        5.  建立 `(:RuleNode)-[:REQUIRES_...]->(:ConditionNode)`。
* **关系**: 下游模块，依赖上游的解析结果来填充数据库。

### 2.4 `openstackgraph.py` (环境数据导入)
**功能**: 连接实时的 OpenStack 环境（通过 Keystone API），读取现有的用户、角色、项目和绑定关系，并在 Neo4j 中构建**身份资源子图**。它还包含生成测试数据的功能。

* **输入**: OpenStack Admin API 凭据。
* **核心逻辑**:
    * `read_data_from_openstack`: 调用 Keystone API 获取 Users, Roles, Projects, Assignments。
    * `generate_tokens_from_assignments`: **关键逻辑**。它不直接画 User->Role 线，而是**模拟 Token**。
        * 如果 User A 在 Project B 拥有 Role C，脚本会生成一个 `Token` 节点。
        * 建立路径：`User A -> HAS_TOKEN -> Token X -> GRANTS -> Role C`。
        * 支持模拟“共享 Token”（多个用户拥有相同权限集合）和“独有 Token”。
    * `create_neo4j_graph`: 将上述节点和关系写入 Neo4j。
* **输出**: Neo4j 中的身份与权限分配数据。

### 2.5 辅助文件 (`*api.py`, `*merge.py`, `*policy.py`)
**功能**: 这是一组爬虫和数据对齐工具，用于建立 **API URL (动态日志)** 与 **Policy Name (静态配置)** 之间的映射关系。

* `*api.py`: 爬取 OpenStack 官方文档，提取 API Endpoint (如 `GET /v3/users`)。
* `*policy.py`: 爬取官方文档，提取 Policy Name (如 `identity:list_users`) 及其默认规则。
* `*merge.py`: 将上述两者进行模糊匹配或正则匹配，生成 Excel 映射表。这是后续进行**日志分析**（将 API 调用日志映射回图谱中的 PolicyNode）的关键数据源。

---

## 3. 模块间数据流向关系图

```mermaid
graph TD
    subgraph "Input Source"
        A[policy.yaml] --> B(policypreprocess.py)
        LiveOS[OpenStack Environment] --> C(openstackgraph.py)
        Docs[OpenStack Docs] --> D(Auxiliary Scrapers)
    end

    subgraph "Parsing & Logic"
        B -- "Expanded Rules" --> E(policy_parser.py)
        E -- "Minimal Units (DNF)" --> F(openstackpolicygraph.py)
        D -- "API List & Policy List" --> G(*merge.py)
    end

    subgraph "Neo4j Graph Database"
        F -- "Writes Static Policy Graph" --> DB[(Neo4j)]
        C -- "Writes Identity Graph" --> DB
    end

    subgraph "Analysis (Future/Todo)"
        G -- "Mapping Table (URL <-> Policy)" --> LogAnalysis[Log Analyzer]
        LogAnalysis -- "Matches Logs to Nodes" --> DB
    end

    style DB fill:#f9f,stroke:#333,stroke-width:2px