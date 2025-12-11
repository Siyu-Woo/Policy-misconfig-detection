from neo4j import GraphDatabase
from typing import Dict, List, Set, Tuple
import re
import hashlib

class PolicyGraphCreator:
    def __init__(self, uri: str, user: str, password: str):
        """
        初始化Neo4j连接
        
        Args:
            uri: Neo4j数据库URI (例如: "bolt://localhost:7687")
            user: 用户名
            password: 密码
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.rule_counter = 0
        self.rule_expression_map = {}  # 用于跟踪规则表达式到规则ID的映射
    
    def close(self):
        """关闭数据库连接"""
        self.driver.close()
    
    def clear_database(self):
        """清空数据库"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("数据库已清空")
    
    def normalize_expression(self, expr: str) -> str:
        """
        规范化表达式，用于比较是否相同
        移除多余空格，统一大小写
        
        Args:
            expr: 原始表达式
            
        Returns:
            str: 规范化后的表达式
        """
        # 移除多余空格
        expr = re.sub(r'\s+', ' ', expr.strip())
        # 统一 and/or 为小写
        expr = re.sub(r'\band\b', 'and', expr, flags=re.IGNORECASE)
        expr = re.sub(r'\bor\b', 'or', expr, flags=re.IGNORECASE)
        return expr
    
    def get_or_create_rule_id(self, rule_expr: str) -> Tuple[str, bool]:
        """
        获取或创建规则ID
        
        Args:
            rule_expr: 规则表达式
            
        Returns:
            Tuple[str, bool]: (规则ID, 是否是新创建的)
        """
        # 规范化表达式
        normalized_expr = self.normalize_expression(rule_expr)
        
        # 检查是否已存在
        if normalized_expr in self.rule_expression_map:
            return self.rule_expression_map[normalized_expr], False
        
        # 创建新的规则ID
        self.rule_counter += 1
        rule_id = f"rule{self.rule_counter}"
        self.rule_expression_map[normalized_expr] = rule_id
        
        return rule_id, True
    
    def parse_node_from_string(self, text: str) -> Tuple[str, str]:
        """
        从字符串中解析节点类型和名称
        
        Args:
            text: 输入字符串，格式为 "type:name"
            
        Returns:
            Tuple[str, str]: (类型, 名称)，如果没有冒号返回 (None, None)
        """
        text = text.strip()
        if ':' in text:
            parts = text.split(':', 1)
            node_type = parts[0].strip()
            node_name = parts[1].strip()
            return node_type, node_name
        return None, None
    
    def parse_rule_expression(self, rule_expr: str) -> List[Tuple[str, str]]:
        """
        解析规则表达式，提取所有的节点
        
        Args:
            rule_expr: 规则表达式，例如 "role:reader and system_scope:all"
            
        Returns:
            List[Tuple[str, str]]: 节点列表，每个元素为 (类型, 名称)
        """
        # 移除括号
        rule_expr = rule_expr.replace('(', '').replace(')', '')
        
        # 按 and/or 分割
        tokens = re.split(r'\s+(?:and|or)\s+', rule_expr, flags=re.IGNORECASE)
        
        nodes = []
        for token in tokens:
            node_type, node_name = self.parse_node_from_string(token)
            if node_type and node_name:
                nodes.append((node_type, node_name))
        
        return nodes
    
    def get_condition_label(self, condition_type: str) -> str:
        """
        根据条件类型生成节点标签
        
        Args:
            condition_type: 条件类型，如 'role', 'user_id', 'system_scope'
            
        Returns:
            str: Neo4j节点标签
        """
        # Neo4j 标签不能包含特殊字符（如 '.'），统一做清洗
        sanitized = re.sub(r'[^0-9a-zA-Z]+', ' ', condition_type)
        parts = [word for word in sanitized.strip().split() if word]
        label = ''.join(word.capitalize() for word in parts) or 'Generic'
        return f"{label}Condition"
    
    def create_policy_graph(self, policy_dict: Dict[str, List[str]]):
        """
        根据策略字典创建Neo4j图
        
        Args:
            policy_dict: 策略字典，key为策略名，value为规则列表
        """
        with self.driver.session() as session:
            self.rule_counter = 0
            self.rule_expression_map = {}
            
            # 用于跟踪已创建的节点（按类型分组）
            created_nodes_by_type = {}
            created_rules = set()  # 跟踪已创建的规则节点
            
            # 统计重复规则
            rule_usage_count = {}
            
            for policy_key, rules in policy_dict.items():
                # 解析根节点（策略节点）
                root_type, root_name = self.parse_node_from_string(policy_key)
                
                if not root_type or not root_name:
                    print(f"警告: 无法解析策略键 '{policy_key}'，跳过")
                    continue
                
                # 创建根节点（策略节点）
                root_label = self.get_condition_label(root_type).replace('Condition', 'Policy')
                root_node_id = f"{root_type}:{root_name}"
                
                if root_node_id not in created_nodes_by_type.get(root_type, set()):
                    session.run(
                        f"""
                        MERGE (n:PolicyNode:{root_label} {{
                            id: $id, 
                            type: $type, 
                            name: $name
                        }})
                        """,
                        id=root_node_id,
                        type=root_type,
                        name=root_name
                    )
                    if root_type not in created_nodes_by_type:
                        created_nodes_by_type[root_type] = set()
                    created_nodes_by_type[root_type].add(root_node_id)
                    print(f"创建策略节点 [{root_label}]: {root_name}")
                
                # 处理每个规则
                for rule_idx, rule_expr in enumerate(rules, 1):
                    # 获取或创建规则ID
                    rule_name, is_new = self.get_or_create_rule_id(rule_expr)
                    rule_node_id = f"rule:{rule_name}"
                    normalized_expr = self.normalize_expression(rule_expr)
                    
                    # 统计规则使用次数
                    if normalized_expr not in rule_usage_count:
                        rule_usage_count[normalized_expr] = {'rule_name': rule_name, 'count': 0, 'policies': []}
                    rule_usage_count[normalized_expr]['count'] += 1
                    rule_usage_count[normalized_expr]['policies'].append(root_name)
                    
                    # 只在首次创建规则节点
                    if rule_node_id not in created_rules:
                        session.run(
                            """
                            MERGE (r:RuleNode {
                                id: $id, 
                                name: $name, 
                                expression: $expr,
                                normalized_expression: $normalized_expr
                            })
                            """,
                            id=rule_node_id,
                            name=rule_name,
                            expr=rule_expr,
                            normalized_expr=normalized_expr
                        )
                        created_rules.add(rule_node_id)
                        print(f"  创建规则节点: {rule_name} - {rule_expr}")
                        
                        # 只在创建规则节点时解析并创建条件关系
                        rule_nodes = self.parse_rule_expression(rule_expr)
                        
                        for node_type, node_name in rule_nodes:
                            node_id = f"{node_type}:{node_name}"
                            node_label = self.get_condition_label(node_type)
                            
                            # 创建条件节点（如果不存在）
                            if node_id not in created_nodes_by_type.get(node_type, set()):
                                session.run(
                                    f"""
                                    MERGE (n:ConditionNode:{node_label} {{
                                        id: $id, 
                                        type: $type, 
                                        name: $name
                                    }})
                                    """,
                                    id=node_id,
                                    type=node_type,
                                    name=node_name
                                )
                                if node_type not in created_nodes_by_type:
                                    created_nodes_by_type[node_type] = set()
                                created_nodes_by_type[node_type].add(node_id)
                                print(f"    创建条件节点 [{node_label}]: {node_name}")
                            
                            # 创建从规则到条件节点的关系
                            rel_key = re.sub(r'[^0-9a-zA-Z]+', '_', node_type).upper()
                            if not rel_key:
                                rel_key = "GENERIC"
                            relationship_name = f"REQUIRES_{rel_key}"
                            session.run(
                                f"""
                                MATCH (rule:RuleNode {{id: $rule_id}})
                                MATCH (cond:ConditionNode:{node_label} {{id: $cond_id}})
                                MERGE (rule)-[:{relationship_name}]->(cond)
                                """,
                                rule_id=rule_node_id,
                                cond_id=node_id
                            )
                    else:
                        print(f"  复用已存在的规则节点: {rule_name} - {rule_expr}")
                    
                    # 创建从策略节点到规则节点的关系（每次都创建，因为不同策略可能使用相同规则）
                    session.run(
                        f"""
                        MATCH (policy:PolicyNode:{root_label} {{id: $policy_id}})
                        MATCH (rule:RuleNode {{id: $rule_id}})
                        MERGE (policy)-[:HAS_RULE]->(rule)
                        """,
                        policy_id=root_node_id,
                        rule_id=rule_node_id
                    )
            
            # 统计信息
            total_nodes = sum(len(nodes) for nodes in created_nodes_by_type.values())
            print(f"\n图创建完成！")
            print(f"总共创建了 {total_nodes} 个唯一节点")
            print(f"创建了 {len(created_rules)} 个唯一规则节点")
            
            # 显示重复的规则
            duplicated_rules = {k: v for k, v in rule_usage_count.items() if v['count'] > 1}
            if duplicated_rules:
                print(f"\n发现 {len(duplicated_rules)} 个被多个策略共享的规则:")
                for expr, info in sorted(duplicated_rules.items(), key=lambda x: x[1]['count'], reverse=True):
                    print(f"  {info['rule_name']} (使用 {info['count']} 次): {expr}")
                    print(f"    被以下策略使用: {', '.join(info['policies'][:5])}" + 
                          (f" 等{len(info['policies'])}个" if len(info['policies']) > 5 else ""))
            
            print(f"\n各类型节点统计:")
            for node_type, nodes in created_nodes_by_type.items():
                print(f"  {node_type}: {len(nodes)} 个节点")
    
    def get_graph_statistics(self):
        """获取图的统计信息"""
        with self.driver.session() as session:
            # 统计节点数量
            policy_count = session.run("MATCH (n:PolicyNode) RETURN count(n) as count").single()['count']
            rule_count = session.run("MATCH (n:RuleNode) RETURN count(n) as count").single()['count']
            condition_count = session.run("MATCH (n:ConditionNode) RETURN count(n) as count").single()['count']
            
            # 统计各类型条件节点
            condition_types = session.run("""
                MATCH (n:ConditionNode)
                RETURN DISTINCT n.type as type, count(*) as count
                ORDER BY count DESC
            """).data()
            
            # 统计关系数量
            has_rule_count = session.run("MATCH ()-[r:HAS_RULE]->() RETURN count(r) as count").single()['count']
            
            # 统计被多个策略使用的规则
            shared_rules = session.run("""
                MATCH (p:PolicyNode)-[:HAS_RULE]->(r:RuleNode)
                WITH r, count(DISTINCT p) as policy_count, collect(DISTINCT p.name) as policies
                WHERE policy_count > 1
                RETURN r.name as rule_name, 
                       r.expression as rule_expr, 
                       policy_count, 
                       policies
                ORDER BY policy_count DESC
            """).data()
            
            # 统计各类型的REQUIRES关系
            requires_by_type = session.run("""
                MATCH ()-[r]->(:ConditionNode)
                WHERE type(r) STARTS WITH 'REQUIRES_'
                RETURN type(r) as relationship_type, count(*) as count
                ORDER BY count DESC
            """).data()
            
            return {
                'policy_nodes': policy_count,
                'rule_nodes': rule_count,
                'condition_nodes': condition_count,
                'condition_types': condition_types,
                'has_rule_relationships': has_rule_count,
                'requires_relationships': requires_by_type,
                'shared_rules': shared_rules
            }
    
    def query_shared_rules(self):
        """查询被多个策略共享的规则"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:PolicyNode)-[:HAS_RULE]->(r:RuleNode)
                WITH r, count(DISTINCT p) as usage_count, collect(DISTINCT p.name) as policies
                WHERE usage_count > 1
                RETURN r.name as rule_name, 
                       r.expression as expression,
                       usage_count,
                       policies
                ORDER BY usage_count DESC
            """)
            
            return result.data()

# 使用示例
def main():
    # 示例策略字典 - 包含重复的规则
    policy_dict = {
        'identity:get_application_credential': [
            'role:reader and system_scope:all',
            'user_id:%(user_id)s'
        ],
        'identity:list_application_credentials': [
            'role:reader and system_scope:all',  # 与上面的规则相同
            'user_id:%(user_id)s'  # 与上面的规则相同
        ],
        'identity:create_user': [
            'role:admin and system_scope:all',
            'role:admin and domain_id:%(target.domain.id)s'
        ],
        'identity:update_user': [
            'role:admin and system_scope:all',  # 与create_user的第一个规则相同
            'role:admin and domain_id:%(target.domain.id)s',  # 与create_user的第二个规则相同
            'user_id:%(user_id)s and user_id:%(target.user.id)s'
        ],
        'identity:delete_user': [
            'role:admin and system_scope:all',  # 再次重复
            'role:admin and domain_id:%(target.domain.id)s'  # 再次重复
        ],
        'identity:create_instance': [
            'role:admin or role:member',
            'project_id:%(target.project.id)s'
        ]
    }
    
    # 创建Neo4j连接
    graph_creator = PolicyGraphCreator(
        uri="bolt://58.206.232.230:7687",
        user="neo4j",
        password="Password"
    )
    
    try:
        # 清空数据库
        graph_creator.clear_database()
        
        # 创建图
        print("="*60)
        print("开始创建策略图...")
        print("="*60)
        graph_creator.create_policy_graph(policy_dict)
        
        # 获取统计信息
        print("\n" + "="*60)
        print("图统计信息:")
        print("="*60)
        stats = graph_creator.get_graph_statistics()
        print(f"策略节点数: {stats['policy_nodes']}")
        print(f"规则节点数: {stats['rule_nodes']} (去重后)")
        print(f"条件节点数: {stats['condition_nodes']}")
        
        print(f"\n各类型条件节点:")
        for cond_type in stats['condition_types']:
            print(f"  {cond_type['type']}: {cond_type['count']} 个")
        
        print(f"\nHAS_RULE关系数: {stats['has_rule_relationships']}")
        
        # 显示共享的规则
        if stats['shared_rules']:
            print(f"\n被多个策略共享的规则 ({len(stats['shared_rules'])} 个):")
            for rule in stats['shared_rules']:
                print(f"\n  {rule['rule_name']}: {rule['rule_expr']}")
                print(f"    被 {rule['policy_count']} 个策略使用:")
                for policy in rule['policies']:
                    print(f"      - {policy}")
    
    finally:
        graph_creator.close()

if __name__ == "__main__":
    main()
