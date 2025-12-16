import os
import sys
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client as keystone_client
from keystoneauth1.exceptions import http as http_exc
from neo4j import GraphDatabase
import uuid
import random

from output_control import general_print as print

_TOKEN_OUTPUT_VERBOSE = False


def set_token_output_verbose(enabled: bool) -> None:
    global _TOKEN_OUTPUT_VERBOSE
    _TOKEN_OUTPUT_VERBOSE = enabled


def _token_log(message: str) -> None:
    if _TOKEN_OUTPUT_VERBOSE:
        print(message)

# OpenStack 配置
OS_CONFIG = {
    'auth_url': 'http://localhost:5000/v3',
    'username': 'admin',
    'password': 'admin',
    'project_name': 'admin',
    'user_domain_name': 'Default',
    'project_domain_name': 'Default'
}

# Neo4j 配置
NEO4J_URI = "bolt://58.206.232.230:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Password"  # 请修改为你的密码


class OpenStackNeo4jManager:
    def __init__(self):
        self.keystone = None
        self.neo4j_driver = None
        self.setup_openstack()
        self.setup_neo4j()
    
    def setup_openstack(self):
        """设置 OpenStack 连接"""
        try:
            auth = v3.Password(
                auth_url=OS_CONFIG['auth_url'],
                username=OS_CONFIG['username'],
                password=OS_CONFIG['password'],
                project_name=OS_CONFIG['project_name'],
                user_domain_name=OS_CONFIG['user_domain_name'],
                project_domain_name=OS_CONFIG['project_domain_name']
            )
            sess = session.Session(auth=auth, timeout=10)
            self.keystone = keystone_client.Client(session=sess)
            
            # 测试连接
            self.keystone.projects.list()
            print("✓ OpenStack 连接成功")
        except Exception as e:
            print(f"✗ OpenStack 连接失败: {e}")
            raise
    
    def setup_neo4j(self):
        """设置 Neo4j 连接"""
        try:
            self.neo4j_driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            # 测试连接
            with self.neo4j_driver.session() as session:
                session.run("RETURN 1")
            print("✓ Neo4j 连接成功")
        except Exception as e:
            print(f"✗ Neo4j 连接失败: {e}")
            print("提示: 请确保 Neo4j 服务正在运行")
            raise
    
    def cleanup_openstack_data(self):
        """清理 OpenStack 中的测试数据"""
        print("\n=== 清理 OpenStack 测试数据 ===")
        
        # 保护的系统资源（不删除）
        protected_users = ['admin', 'glance', 'nova', 'neutron', 'cinder', 'placement', 'keystone']
        protected_projects = ['admin', 'service']
        protected_roles = ['admin', 'member', 'reader']  # 保留常用角色
        
        # 1. 清理用户（先移除角色分配）
        print("\n清理用户...")
        try:
            users = self.keystone.users.list()
            deleted_count = 0
            skipped_count = 0
            
            for user in users:
                if user.name in protected_users:
                    skipped_count += 1
                    continue
                
                try:
                    # 先获取并移除该用户的所有角色分配
                    try:
                        assignments = self.keystone.role_assignments.list(user=user.id)
                        for assignment in assignments:
                            try:
                                if hasattr(assignment, 'role') and hasattr(assignment, 'scope'):
                                    role_id = assignment.role.get('id') if isinstance(assignment.role, dict) else getattr(assignment.role, 'id', None)
                                    
                                    # 获取 project_id
                                    project_id = None
                                    if isinstance(assignment.scope, dict) and 'project' in assignment.scope:
                                        project_id = assignment.scope['project'].get('id')
                                    elif hasattr(assignment.scope, 'project'):
                                        project_id = getattr(assignment.scope.project, 'id', None)
                                    
                                    if role_id and project_id:
                                        self.keystone.roles.revoke(role=role_id, user=user.id, project=project_id)
                            except Exception as e:
                                pass  # 忽略撤销失败
                    except:
                        pass
                    
                    # 删除用户
                    self.keystone.users.delete(user.id)
                    print(f"  ✓ 删除用户: {user.name}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  ✗ 删除用户失败: {user.name}, {e}")
            
            print(f"✓ 用户清理完成 (删除: {deleted_count}, 跳过: {skipped_count})")
        except Exception as e:
            print(f"✗ 清理用户时出错: {e}")
        
        # 2. 清理项目
        print("\n清理项目...")
        try:
            projects = self.keystone.projects.list()
            deleted_count = 0
            skipped_count = 0
            
            for project in projects:
                if project.name in protected_projects:
                    skipped_count += 1
                    continue
                
                try:
                    # 删除项目
                    self.keystone.projects.delete(project.id)
                    print(f"  ✓ 删除项目: {project.name}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  ✗ 删除项目失败: {project.name}, {e}")
            
            print(f"✓ 项目清理完成 (删除: {deleted_count}, 跳过: {skipped_count})")
        except Exception as e:
            print(f"✗ 清理项目时出错: {e}")
        
        # 3. 清理角色（可选，通常保留系统角色）
        print("\n清理自定义角色...")
        try:
            roles = self.keystone.roles.list()
            deleted_count = 0
            skipped_count = 0
            
            for role in roles:
                if role.name in protected_roles:
                    skipped_count += 1
                    continue
                
                # 只删除自定义角色
                if role.name.startswith('test_') or role.name in ['operator']:
                    try:
                        self.keystone.roles.delete(role.id)
                        print(f"  ✓ 删除角色: {role.name}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"  ✗ 删除角色失败: {role.name}, {e}")
                else:
                    skipped_count += 1
            
            print(f"✓ 角色清理完成 (删除: {deleted_count}, 跳过: {skipped_count})")
        except Exception as e:
            print(f"✗ 清理角色时出错: {e}")
        
        print("\n✓ OpenStack 数据清理完成")
    
    def generate_test_data(self):
        """生成测试数据并插入到 OpenStack"""
        print("\n=== 生成并插入测试数据到 OpenStack ===")
        
        # 1. 创建测试用户
        print("\n创建测试用户...")
        test_users = [
            {'name': 'alice', 'email': 'alice@example.com'},
            {'name': 'bob', 'email': 'bob@example.com'},
            {'name': 'charlie', 'email': 'charlie@example.com'},
            {'name': 'david', 'email': 'david@example.com'},
            {'name': 'eve', 'email': 'eve@example.com'}
        ]
        
        created_users = []
        for user_info in test_users:
            try:
                user = self.keystone.users.create(
                    name=user_info['name'],
                    email=user_info['email'],
                    password='test123',
                    domain='default'
                )
                created_users.append(user)
                print(f"✓ 创建用户: {user.name} (ID: {user.id})")
            except Exception as e:
                # 用户可能已存在
                try:
                    users = self.keystone.users.list(name=user_info['name'])
                    if users:
                        created_users.append(users[0])
                        print(f"⚠ 用户已存在: {user_info['name']} (ID: {users[0].id})")
                except:
                    print(f"✗ 创建/获取用户失败: {user_info['name']}, {e}")
        
        # 2. 获取或创建角色
        print("\n获取/创建角色...")
        role_names = ['admin', 'member', 'reader', 'operator']
        roles = []
        
        for role_name in role_names:
            try:
                role = self.keystone.roles.find(name=role_name)
                roles.append(role)
                print(f"✓ 找到角色: {role.name} (ID: {role.id})")
            except Exception:
                try:
                    role = self.keystone.roles.create(name=role_name)
                    roles.append(role)
                    print(f"✓ 创建角色: {role.name} (ID: {role.id})")
                except Exception as e:
                    print(f"✗ 创建角色失败: {role_name}, {e}")
        
        # 3. 获取或创建项目
        print("\n获取/创建项目...")
        project_name = 'test_project'
        try:
            project = self.keystone.projects.find(name=project_name)
            print(f"✓ 找到项目: {project.name} (ID: {project.id})")
        except Exception:
            project = self.keystone.projects.create(
                name=project_name,
                domain='default',
                description='Test project for token management'
            )
            print(f"✓ 创建项目: {project.name} (ID: {project.id})")
        
        # 4. 为用户分配角色（模拟复杂的权限关系）
        print("\n为用户分配角色...")
        for user in created_users:
            # 为每个用户随机分配1-3个角色
            num_roles = random.randint(1, 3)
            user_roles = random.sample(roles, num_roles)
            
            for role in user_roles:
                try:
                    self.keystone.roles.grant(
                        role=role.id,
                        user=user.id,
                        project=project.id
                    )
                    print(f"✓ 为用户 {user.name} 在项目 {project.name} 中分配角色 {role.name}")
                except Exception as e:
                    if "Conflict" in str(e):
                        print(f"⚠ 角色已分配: {user.name} - {role.name}")
                    else:
                        print(f"✗ 分配角色失败: {user.name} - {role.name}, {e}")
        
        print(f"\n✓ 测试数据生成完成")
        print(f"  - 用户数: {len(created_users)}")
        print(f"  - 角色数: {len(roles)}")
        print(f"  - 项目数: 1")
        
        return created_users, roles, project
    
    def read_data_from_openstack(self):
        """从 OpenStack 读取所有相关数据"""
        print("\n=== 从 OpenStack 读取数据 ===")
        
        # 1. 读取所有用户
        print("\n读取用户...")
        users = self.keystone.users.list()
        print(f"✓ 读取到 {len(users)} 个用户")
        for user in users[:10]:  # 只显示前10个
            print(f"  - {user.name} (ID: {user.id})")
        if len(users) > 10:
            print(f"  ... 还有 {len(users) - 10} 个用户")
        
        # 2. 读取所有角色
        print("\n读取角色...")
        roles = self.keystone.roles.list()
        print(f"✓ 读取到 {len(roles)} 个角色")
        for role in roles:
            print(f"  - {role.name} (ID: {role.id})")
        
        # 3. 读取所有项目
        print("\n读取项目...")
        projects = self.keystone.projects.list()
        print(f"✓ 读取到 {len(projects)} 个项目")
        for project in projects[:5]:
            print(f"  - {project.name} (ID: {project.id})")
        
        # 4. 读取角色分配
        print("\n读取角色分配...")
        role_assignments = []
        
        try:
            # 使用 role_assignments API
            assignments = self.keystone.role_assignments.list()
            print(f"✓ 读取到 {len(assignments)} 个角色分配")
            
            for assignment in assignments:
                # 解析分配信息
                if hasattr(assignment, 'user') and hasattr(assignment, 'role') and hasattr(assignment, 'scope'):
                    user_id = assignment.user.get('id') if isinstance(assignment.user, dict) else getattr(assignment.user, 'id', None)
                    role_id = assignment.role.get('id') if isinstance(assignment.role, dict) else getattr(assignment.role, 'id', None)
                    
                    # 获取 project_id
                    project_id = None
                    system_scope = None
                    if isinstance(assignment.scope, dict):
                        if 'project' in assignment.scope:
                            project_id = assignment.scope['project'].get('id')
                        elif 'system' in assignment.scope:
                            scope_data = assignment.scope['system']
                            if isinstance(scope_data, dict):
                                system_scope = next(
                                    (key for key, value in scope_data.items() if value),
                                    'all'
                                )
                            else:
                                system_scope = str(scope_data)
                    elif hasattr(assignment.scope, 'project'):
                        project_id = getattr(assignment.scope.project, 'id', None)
                    elif hasattr(assignment.scope, 'system'):
                        system_attr = getattr(assignment.scope, 'system', None)
                        if isinstance(system_attr, dict):
                            system_scope = next(
                                (key for key, value in system_attr.items() if value),
                                'all'
                            )
                        elif system_attr:
                            system_scope = str(system_attr)
                    
                    if user_id and role_id and (project_id or system_scope):
                        role_assignments.append({
                            'user_id': user_id,
                            'role_id': role_id,
                            'project_id': project_id,
                            'system_scope': system_scope
                        })
            
            print(f"✓ 解析到 {len(role_assignments)} 个有效的角色分配")
            
            # 显示部分分配信息
            for i, assignment in enumerate(role_assignments[:5]):
                user = next((u for u in users if u.id == assignment['user_id']), None)
                role = next((r for r in roles if r.id == assignment['role_id']), None)
                project = next((p for p in projects if p.id == assignment['project_id']), None)
                
                if user and role and project:
                    print(f"  - {user.name} -> {role.name} @ {project.name}")
            
            if len(role_assignments) > 5:
                print(f"  ... 还有 {len(role_assignments) - 5} 个分配")
                
        except Exception as e:
            print(f"⚠ 读取角色分配失败: {e}")
            print("  将使用简化方法读取角色分配...")
            
            # 简化方法：遍历用户和项目
            for user in users:
                for project in projects:
                    try:
                        # 尝试获取用户在该项目中的角色
                        user_roles = self.keystone.roles.list(user=user.id, project=project.id)
                        for role in user_roles:
                            role_assignments.append({
                                'user_id': user.id,
                                'role_id': role.id,
                                'project_id': project.id,
                                'system_scope': None
                            })
                    except:
                        pass
            
            print(f"✓ 使用简化方法读取到 {len(role_assignments)} 个角色分配")
        
        return users, roles, projects, role_assignments
    
    def generate_tokens_from_assignments(self, users, roles, role_assignments):
        """根据角色分配生成 token 映射"""
        _token_log("\n=== 基于角色分配生成 Token 映射 ===")
        
        # 创建用户ID到用户对象的映射
        user_map = {u.id: u for u in users}
        role_map = {r.id: r for r in roles}
        
        # 按用户组织角色分配
        user_roles_map = {}
        for assignment in role_assignments:
            user_id = assignment['user_id']
            role_id = assignment['role_id']
            
            if user_id not in user_roles_map:
                user_roles_map[user_id] = []
            
            if role_id in role_map:
                user_roles_map[user_id].append({
                    'role': role_map[role_id],
                    'project_id': assignment.get('project_id'),
                    'system_scope': assignment.get('system_scope')
                })
        
        # 创建共享 token（按角色）
        _token_log("\n创建共享 Token...")
        role_shared_tokens = {}
        for role in roles:
            # 为每个角色创建1-2个共享token
            num_tokens = random.randint(1, 2)
            role_shared_tokens[role.id] = []
            for _ in range(num_tokens):
                token_id = str(uuid.uuid4())
                role_shared_tokens[role.id].append(token_id)
                _token_log(f"✓ 为角色 {role.name} 创建共享 token {token_id[:8]}...")
        
        # 生成 token 映射
        token_role_mappings = []
        shared_token_users = {}
        
        _token_log("\n为用户生成 Token...")
        for user_id, user_roles in user_roles_map.items():
            if user_id not in user_map:
                continue
            
            user = user_map[user_id]
            user_role_assignments = [assignment.copy() for assignment in user_roles]
            
            def collect_scopes(assignments):
                scopes = sorted({a['system_scope'] for a in assignments if a.get('system_scope')})
                return scopes
            
            # 1. 为每个用户生成2个独有 token
            for i in range(2):
                token_id = str(uuid.uuid4())
                token_role_mappings.append({
                    'user': user,
                    'token_id': token_id,
                    'role_assignments': [assignment.copy() for assignment in user_role_assignments],
                    'shared': False,
                    'system_scopes': collect_scopes(user_role_assignments)
                })
                roles_str = ', '.join([
                    assignment['role'].name + (
                        f"@system({assignment['system_scope']})" if assignment.get('system_scope') else ''
                    )
                    for assignment in user_role_assignments
                ])
                _token_log(f"✓ 用户 {user.name} 的独有 token {token_id[:8]}... -> [{roles_str}]")
            
            # 2. 为用户分配该角色的共享 token
            for assignment in user_role_assignments:
                role = assignment['role']
                if role.id in role_shared_tokens:
                    # 随机选择该角色的一个共享token
                    token_id = random.choice(role_shared_tokens[role.id])
                    
                    # 检查是否已添加
                    if not any(m['user'].id == user.id and m['token_id'] == token_id 
                              for m in token_role_mappings):
                        token_role_mappings.append({
                            'user': user,
                            'token_id': token_id,
                            'role_assignments': [assignment.copy()],
                            'shared': True,
                            'system_scopes': collect_scopes([assignment])
                        })
                        
                        if token_id not in shared_token_users:
                            shared_token_users[token_id] = []
                        shared_token_users[token_id].append(user.name)
        
        # 打印共享 token 统计
        _token_log("\n=== 共享 Token 统计 ===")
        for token_id, user_names in shared_token_users.items():
            # 找到这个token对应的角色
            token_mapping = next((m for m in token_role_mappings if m['token_id'] == token_id), None)
            if token_mapping and token_mapping['role_assignments']:
                role_name = token_mapping['role_assignments'][0]['role'].name
                scope = token_mapping['role_assignments'][0].get('system_scope')
                scope_str = f" (system_scope: {scope})" if scope else ""
                _token_log(f"Token {token_id[:8]}... (角色: {role_name}{scope_str})")
                _token_log(f"  被 {len(user_names)} 个用户使用: {', '.join(user_names)}")

        _token_log(f"\n✓ 共生成 {len(token_role_mappings)} 个 token 映射关系")
        
        # 统计唯一 token 数量
        unique_tokens = set(m['token_id'] for m in token_role_mappings)
        _token_log(f"✓ 唯一 token 数: {len(unique_tokens)}")
        
        return token_role_mappings
    
    def create_neo4j_graph(self, token_role_mappings):
        """创建 Neo4j 图 - User->Token->Role"""
        print("\n=== 创建 Neo4j 图 ===")
        
        with self.neo4j_driver.session() as session:
            # 清空现有数据
            session.run("MATCH (n) DETACH DELETE n")
            print("✓ 清空 Neo4j 数据库")
            
            # 收集所有唯一的用户、token、角色
            users_dict = {}
            tokens_dict = {}
            roles_dict = {}
            
            system_scopes_set = set()
            
            for mapping in token_role_mappings:
                user = mapping['user']
                users_dict[user.id] = user
                tokens_dict[mapping['token_id']] = mapping['shared']
                for scope in mapping.get('system_scopes', []):
                    if scope:
                        system_scopes_set.add(scope)
                for assignment in mapping['role_assignments']:
                    role = assignment['role']
                    roles_dict[role.id] = role
            
            # 1. 创建用户节点
            print(f"\n创建 {len(users_dict)} 个用户节点...")
            for user_id, user in users_dict.items():
                session.run("""
                    MERGE (u:User {id: $user_id})
                    SET u.name = $name, u.email = $email
                """, user_id=user.id, 
                    name=user.name,
                    email=getattr(user, 'email', f'{user.name}@example.com'))
            print("✓ 用户节点创建完成")
            
            # 2. 创建 token 节点
            print(f"\n创建 {len(tokens_dict)} 个唯一 Token 节点...")
            token_name_map = {}
            for idx, (token_id, is_shared) in enumerate(tokens_dict.items(), 1):
                token_name = f"token{idx}"
                token_name_map[token_id] = token_name
                session.run("""
                    MERGE (t:Token {id: $token_id})
                    SET t.shared = $shared,
                        t.name = $name
                """, token_id=token_id, shared=is_shared, name=token_name)
            print("✓ Token 节点创建完成")
            
            # 3. 创建角色节点
            print(f"\n创建 {len(roles_dict)} 个唯一角色节点...")
            for role_id, role in roles_dict.items():
                session.run("""
                    MERGE (r:Role {id: $role_id})
                    SET r.name = $role_name
                """, role_id=role.id, role_name=role.name)
            print("✓ 角色节点创建完成")
            
            # 3.5 创建 system scope 节点
            print(f"\n创建 {len(system_scopes_set)} 个 SystemScope 节点...")
            for scope in system_scopes_set:
                session.run("""
                    MERGE (s:SystemScope {name: $name})
                """, name=scope)
            print("✓ SystemScope 节点创建完成")
            
            # 4. 创建 User -> Token 关系
            print(f"\n创建 User -> Token 关系...")
            for mapping in token_role_mappings:
                session.run("""
                    MATCH (u:User {id: $user_id})
                    MATCH (t:Token {id: $token_id})
                    MERGE (u)-[:HAS_TOKEN]->(t)
                """, user_id=mapping['user'].id,
                    token_id=mapping['token_id'])
            print("✓ User -> Token 关系创建完成")
            
            # 5. 创建 Token -> Role 关系
            print(f"\n创建 Token -> Role 关系...")
            for mapping in token_role_mappings:
                for assignment in mapping['role_assignments']:
                    role = assignment['role']
                    session.run("""
                        MATCH (t:Token {id: $token_id})
                        MATCH (r:Role {id: $role_id})
                        MERGE (t)-[:GRANTS]->(r)
                    """, token_id=mapping['token_id'],
                        role_id=role.id)
            print("✓ Token -> Role 关系创建完成")
            
            # 6. 创建 Token -> SystemScope 关系
            print(f"\n创建 Token -> SystemScope 关系...")
            for mapping in token_role_mappings:
                for scope in mapping.get('system_scopes', []):
                    if not scope:
                        continue
                    session.run("""
                        MATCH (t:Token {id: $token_id})
                        MATCH (s:SystemScope {name: $scope})
                        MERGE (t)-[:HAS_SYSTEM_SCOPE]->(s)
                    """, token_id=mapping['token_id'], scope=scope)
            print("✓ Token -> SystemScope 关系创建完成")
            
            # 验证
            print("\n=== 验证图结构 ===")
            
            # 验证没有 User -> Role 直接连接
            direct_conn = session.run("""
                MATCH (u:User)-[r]->(role:Role)
                RETURN count(r) as count
            """).single()
            
            if direct_conn['count'] == 0:
                print("✓ 验证通过: User 不直接连接到 Role")
            else:
                print(f"⚠ 警告: 发现 {direct_conn['count']} 个 User->Role 直接连接")
            
            # 打印统计信息
            self._print_graph_statistics(session)
    
    def _print_graph_statistics(self, session):
        """打印图统计信息"""
        print("\n=== 图统计信息 ===")
        
        # 总体统计
        stats = session.run("""
            MATCH (u:User) WITH count(u) as users
            MATCH (t:Token) WITH users, count(t) as tokens
            MATCH (r:Role) WITH users, tokens, count(r) as roles
            MATCH (s:SystemScope) WITH users, tokens, roles, count(s) as scopes
            MATCH ()-[rel]->() WITH users, tokens, roles, scopes, count(rel) as relationships
            RETURN users, tokens, roles, scopes, relationships
        """).single()
        
        print(f"\n节点统计:")
        print(f"  User 节点: {stats['users']}")
        print(f"  Token 节点: {stats['tokens']}")
        print(f"  Role 节点: {stats['roles']}")
        print(f"  SystemScope 节点: {stats['scopes']}")
        print(f"  总关系数: {stats['relationships']}")
        
        # 用户的 token 数量
        print(f"\n用户的 Token 数量:")
        result = session.run("""
            MATCH (u:User)-[:HAS_TOKEN]->(t:Token)
            RETURN u.name as user, count(t) as token_count
            ORDER BY token_count DESC
            LIMIT 10
        """)
        for record in result:
            print(f"  {record['user']}: {record['token_count']} 个 tokens")
        
        # 用户通过 token 获得的角色
        print(f"\n用户通过 Token 获得的角色:")
        result = session.run("""
            MATCH (u:User)-[:HAS_TOKEN]->(t:Token)-[:GRANTS]->(r:Role)
            WITH u, collect(DISTINCT r.name) as roles
            RETURN u.name as user, roles, size(roles) as role_count
            ORDER BY role_count DESC
            LIMIT 10
        """)
        for record in result:
            print(f"  {record['user']}: {', '.join(record['roles'])}")
        
        # 共享的 token
        print(f"\n共享的 Tokens:")
        result = session.run("""
            MATCH (u:User)-[:HAS_TOKEN]->(t:Token)-[:GRANTS]->(r:Role)
            WITH t, collect(DISTINCT u.name) as users, collect(DISTINCT r.name) as roles
            WHERE size(users) > 1
            RETURN t.id as token, users, roles, size(users) as user_count
            ORDER BY user_count DESC
        """)
        count = 0
        for record in result:
            print(f"  Token {record['token'][:8]}... -> {', '.join(record['roles'])}")
            print(f"    被 {record['user_count']} 个用户共享: {', '.join(record['users'])}")
            count += 1
        
        if count == 0:
            print("  (无共享 token)")
        
        # 示例路径
        print(f"\n示例路径 (User -> Token -> Role):")
        result = session.run("""
            MATCH (u:User)-[:HAS_TOKEN]->(t:Token)-[:GRANTS]->(r:Role)
            RETURN u.name as user, t.id as token, r.name as role, t.shared as shared
            ORDER BY u.name, t.id
            LIMIT 10
        """)
        for record in result:
            shared = " [共享]" if record['shared'] else ""
            print(f"  {record['user']} -> {record['token'][:8]}...{shared} -> {record['role']}")
    
    def close(self):
        """关闭连接"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
            print("\n✓ Neo4j 连接已关闭")


def main():
    print("=== OpenStack to Neo4j 数据导入工具 ===")
    print("工作流程:")
    print("  1. [可选] 清理 OpenStack 中的测试数据")
    print("  2. [可选] 生成测试数据并插入到 OpenStack")
    print("  3. 通过 API 从 OpenStack 读取数据")
    print("  4. 生成 Token 映射关系")
    print("  5. 创建 Neo4j 图 (User -> Token -> Role)")
    print()
    
    manager = OpenStackNeo4jManager()
    
    try:
        # 模式选择
        if len(sys.argv) > 1 and sys.argv[1] == '--generate':
            # 生成模式：先清理，再生成测试数据
            print("\n[模式: 清理并生成测试数据]")
            
            # 清理现有数据
            manager.cleanup_openstack_data()
            
            # 生成新数据
            manager.generate_test_data()
        elif len(sys.argv) > 1 and sys.argv[1] == '--cleanup':
            # 仅清理模式
            print("\n[模式: 仅清理数据]")
            manager.cleanup_openstack_data()
            print("\n✓ 清理完成")
            return
        
        # 读取并处理数据
        print("\n[模式: 读取并处理数据]")
        
        # 1. 从 OpenStack 读取数据
        users, roles, projects, role_assignments = manager.read_data_from_openstack()
        
        if not users or not roles or not role_assignments:
            print("\n⚠ OpenStack 中数据不足，建议使用 --generate 模式生成测试数据")
            print("   运行: python openstack_to_neo4j.py --generate")
            return
        
        # 2. 生成 token 映射
        token_role_mappings = manager.generate_tokens_from_assignments(users, roles, role_assignments)
        
        # 3. 创建 Neo4j 图
        manager.create_neo4j_graph(token_role_mappings)
        
        print("\n✓ 所有操作完成!")
        print("\n可以在 Neo4j Browser 中查询:")
        print("  MATCH path = (u:User)-[:HAS_TOKEN]->(t:Token)-[:GRANTS]->(r:Role)")
        print("  RETURN path LIMIT 100")
        
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        manager.close()


if __name__ == "__main__":
    main()
