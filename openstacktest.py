#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 Python OpenStack SDK 创建用户
需要安装: pip install openstacksdk
"""

from openstack import connection
from openstack.identity.v3 import user
import sys

def create_openstack_user(auth_config, username, password, email, description=None, enabled=True):
    """
    创建 OpenStack 用户
    
    参数:
        auth_config: 认证配置字典，包含认证信息
        username: 用户名
        password: 密码
        email: 邮箱
        description: 用户描述（可选）
        enabled: 是否启用用户（默认 True）
    
    返回:
        创建的用户对象
    """
    try:
        # 创建 OpenStack 连接
        conn = connection.Connection(**auth_config)
        
        # 创建用户
        user_obj = conn.identity.create_user(
            name=username,
            password=password,
            email=email,
            description=description or f"User created via Python SDK: {username}",
            enabled=enabled
        )
        
        print(f"✓ 成功创建用户: {username}")
        print(f"  用户 ID: {user_obj.id}")
        print(f"  用户邮箱: {user_obj.email}")
        print(f"  启用状态: {user_obj.is_enabled}")
        
        return user_obj
        
    except Exception as e:
        print(f"✗ 创建用户失败: {str(e)}", file=sys.stderr)
        return None


def create_user_with_roles(auth_config, username, password, email, project_name, role_names):
    """
    创建用户并分配角色到项目
    
    参数:
        auth_config: 认证配置
        username: 用户名
        password: 密码
        email: 邮箱
        project_name: 项目名称
        role_names: 角色名称列表，如 ['member', 'reader']
    """
    try:
        conn = connection.Connection(**auth_config)
        
        # 创建用户
        user_obj = conn.identity.create_user(
            name=username,
            password=password,
            email=email,
            enabled=True
        )
        
        # 查找项目
        project = conn.identity.find_project(project_name)
        if not project:
            print(f"✗ 项目 '{project_name}' 不存在")
            return None
        
        # 分配角色
        for role_name in role_names:
            role = conn.identity.find_role(role_name)
            if role:
                conn.identity.assign_project_role_to_user(
                    project=project.id,
                    user=user_obj.id,
                    role=role.id
                )
                print(f"✓ 已分配角色 '{role_name}' 到用户 '{username}'")
            else:
                print(f"✗ 角色 '{role_name}' 不存在")
        
        return user_obj
        
    except Exception as e:
        print(f"✗ 操作失败: {str(e)}", file=sys.stderr)
        return None


# 使用示例
if __name__ == "__main__":
    # 方式 1: 使用认证信息字典
    auth_config = {
        'auth_url': 'http://localhost:5000/v3',
        'project_name': 'admin',
        'username': 'admin',
        'password': 'admin',
        'user_domain_name': 'Default',
        'project_domain_name': 'Default'
    }
    
    
    # 创建用户
    new_user = create_openstack_user(
        auth_config=auth_config,
        username='test_user',
        password='SecurePassword123!',
        email='test_user@example.com',
        description='测试用户'
    )
    
    # 创建用户并分配角色
    if new_user:
        user_with_roles = create_user_with_roles(
            auth_config=auth_config,
            username='test_user2',
            password='SecurePassword456!',
            email='test_user2@example.com',
            project_name='demo',
            role_names=['member']
        )