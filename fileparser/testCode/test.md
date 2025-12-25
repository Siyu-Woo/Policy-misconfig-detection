# testCode 目录说明

## 1. 脚本功能、输入输出与命令行

### AuthorizationScopeCheck.py
- **功能**：基于 RBAC 审计日志与图数据库策略子图，检测“授权范围未被使用”的规则。
- **输入**：
  - RBAC 解析日志 CSV（默认 `/root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv`）
  - rolegrant.csv（默认 `/root/policy-fileparser/data/assistfile/rolegrant.csv`）
  - projectinfo.csv（默认 `/root/policy-fileparser/data/assistfile/projectinfo.csv`）
  - Neo4j 图数据库
- **输出**：终端输出风险项或 baseline；
- **命令行**：
  ```bash
  python /root/policy-fileparser/testCode/AuthorizationScopeCheck.py \
    --policy /etc/openstack/policies/TestPolicyFiles/policyB.yaml \
    --parsed-logs /root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv \
    --output console
  ```

### PolicyDoctor.py
- **功能**：已知错误配置检测（仅错误码 4/5/7/8 的检查）。
- **输入**：Neo4j 策略子图、`sensitive_permissions.csv`。
- **输出**：终端输出风险项，或 baseline：`read n policy rules，all Meet configure safety baseline`。
- **命令行**：
  ```bash
  python /root/policy-fileparser/testCode/PolicyDoctor.py --output console
  ```

### RoleMisConfigcheck.py
- **功能**：低权限 API 错配给高权限角色（错误码 12）。
- **输入**：Neo4j 策略子图、`role_level.json`、`projectinfo.csv`。
- **输出**：终端输出风险项或 baseline：`read n policy rules，all APIs has proper assigned to Roles`。
- **命令行**：
  ```bash
  python /root/policy-fileparser/testCode/RoleMisConfigcheck.py \
    --policy /etc/openstack/policies/PolicySet/policyC.yaml \
    --output console
  ```

### SensitivePermissionCheck.py
- **功能**：敏感权限授予低权限角色（错误码 13）。
- **输入**：Neo4j 策略子图、`role_level.json`、`projectinfo.csv`。
- **输出**：终端输出风险项或 baseline：`read n policy rules，all APIs has proper assigned to Roles`。
- **命令行**：
  ```bash
  python /root/policy-fileparser/testCode/SensitivePermissionCheck.py \
    --policy /etc/openstack/policies/PolicySet/policyD.yaml \
    --output console
  ```

### PolicyGraphParser.py
- **功能**：策略子图构建（与 run_graph_pipeline.py 同逻辑）。
- **输入**：策略文件、Neo4j 连接信息。
- **输出**：写入 Neo4j；按需要输出统计信息。
- **命令行**：
  ```bash
  python /root/policy-fileparser/testCode/PolicyGraphParser.py \
    --policy-files /etc/openstack/policies/TestPolicyFiles/policyB.yaml \
    --neo4j-uri bolt://localhost:7687 \
    --neo4j-user neo4j \
    --neo4j-password Password \
    --skip-identity
  ```

### ResultPrint.py
- **功能**：testCode 目录下简化的错误输出模块（错误码 4/5/7/8）。
- **输入**：错误码与策略信息。
- **输出**：终端格式化输出。

### extract_keystone_rbac.py
- **功能**：解析 Keystone 日志生成 RBAC 审计 CSV。
- **输入**：默认 `/var/log/keystone/keystoneCollect.log`。
- **输出**：`/root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv`，终端输出 `File parsing completed`。
- **命令行**：
  ```bash
  python /root/policy-fileparser/testCode/extract_keystone_rbac.py
  ```

### KnowDetectTime.sh
- **功能**：对 PolicyDoctor.py 进行 10 次计时并输出平均耗时。
- **输出**：`/root/policy-fileparser/testCode/test_results/performance_single.csv`。
- **命令行**：
  ```bash
  /root/policy-fileparser/testCode/KnowDetectTime.sh
  ```

### UnkownDetectTime.sh
- **功能**：对 AuthorizationScopeCheck.py 进行 10 次计时并输出平均耗时。
- **输出**：`/root/policy-fileparser/testCode/test_results/performance_unknown_single.csv`。
- **命令行**：
  ```bash
  /root/policy-fileparser/testCode/UnkownDetectTime.sh
  ```

### UnkownStatisticCheck.py
- **功能**：统计高低权限角色占比与错配（包含错误码 12/13 的原始实现）。
- **输入**：Neo4j 策略子图、`projectinfo.csv`、`role_level.json`。
- **输出**：CSV 统计结果与终端输出。

## 2. 三个检测脚本覆盖的 ErrorCode
- **PolicyDoctor.py**：错误码 4、5、7、8
- **RoleMisConfigcheck.py**：错误码 12
- **SensitivePermissionCheck.py**：错误码 13

## 3. 测试数据说明
- **重要**：测试时尽量不要刷新 rolegrant 与 projectinfo，使用固定版本。备份版本如下：
  - `data/assistfile/rolegrant Authbackup.csv`
  - `data/assistfile/projectinfo Authbackup.csv`

## 4. 测试用例与日志
- 策略文件：
  - `data/policy file/PolicySet/policyA.yaml`
  - `data/policy file/PolicySet/policyB.yaml`
  - `data/policy file/PolicySet/policyC.yaml`
  - `data/policy file/PolicySet/policyD.yaml`
- 日志文件：
  - `/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/log/keystone/keystoneCollect.log`
- 解析文件：
  -`rbac_audit_keystone.csv`

## 关键文件路径映射
- 日志文件："/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/policy file:/etc/openstack/policies" 
- log文件："/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/log/keystone:/var/log/keystone" 
- 辅助文件："/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/assistfile:/root/policy-fileparser/data/assistfile" 
- 代码文件："/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/assistfile:/root/policy-fileparser/data/assistfile" 