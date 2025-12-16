"""
Policy规则解析模块

该模块提供Policy文件解析、规则转换为DNF范式和数据库存储功能。
"""

import os
import re
import logging
import itertools
from typing import Dict, List, Set, Any, Optional, Tuple
from oslo_policy import _parser, _checks

from output_control import general_print as print

try:
    from keystone.cmd.doctor.policy_check_system.policy_database import (
        get_database_instance,
        PolicyDatabase,
    )
except ImportError:  # pragma: no cover - keystone doctor module not available
    class _InMemoryPolicyDB:
        def insert_policy_rule(
            self,
            action=None,
            role=None,
            user=None,
            project=None,
            domain=None,
            system_scope=None,
        ):
            # 最简单的兜底实现，当前上下文只需要成功返回即可
            pass

    def get_database_instance():
        return _InMemoryPolicyDB()

    PolicyDatabase = _InMemoryPolicyDB


class RuleDefinition:
    """规则定义类"""
    
    def __init__(self, name: str, expression: str):
        """
        初始化规则定义
        
        Args:
            name: 规则名称
            expression: 规则表达式
        """
        self.name = name
        self.expression = expression


class PolicyRuleParser:
    """Policy规则解析器类"""
    
    # 定义数据库支持的字段
    VALID_DB_FIELDS = {'domain', 'project', 'role', 'system_scope', 'user'}
    
    # 定义字段名映射
    FIELD_MAPPING = {
        'domain_id': 'domain',
        'project_id': 'project',
        'user_id': 'user',
        'None': None
    }
    
    def __init__(self, db_instance: Optional[PolicyDatabase] = None, debug_mode: bool = False):
        """
        初始化解析器
        
        Args:
            db_instance: 数据库实例，如果为None则使用默认实例
            debug_mode: 是否启用调试模式
        """
        self.logger = logging.getLogger(__name__)
        self.db = db_instance or get_database_instance()
        self.rule_definitions: Dict[str, RuleDefinition] = {}
        self._current_policy_name: Optional[str] = None
        self.debug_mode = debug_mode
        self.total_policies = 0
        self.total_valid_units = 0

    def debug_log(self, message: str) -> None:
        """
        输出调试日志
        
        Args:
            message: 日志消息
        """
        if self.debug_mode:
            self.logger.debug(message)

    def parse_single_policy(self, policy_name: str, expression: str) -> Any:
        """
        解析单个策略
        
        Args:
            policy_name: 策略名称
            expression: 策略表达式
            
        Returns:
            Any: 解析后的规则对象
        """
        # 替换规则引用
        expression = self.substitute_rule_references(expression)
        
        # 解析策略表达式
        parsed_rule = self.parse_policy_expression(expression)
        if parsed_rule is None:
            self.logger.error(f"无法解析策略: {policy_name}")
            return None
            
        return parsed_rule

    def read_policy_file(self, file_path: str) -> Dict[str, str]:
        """
        读取policy文件内容
        
        Args:
            file_path: policy文件路径
            
        Returns:
            Dict[str, str]: 策略名称到策略表达式的映射
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Policy文件不存在: {file_path}")
        
        policies = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 尝试解析YAML格式
            try:
                import yaml
                policies = yaml.safe_load(content)
                if policies:
                    self.logger.info(f"成功读取YAML格式policy文件: {file_path}")
                    return {k: v for k, v in policies.items() if not k.startswith('#')}
            except (yaml.YAMLError, AttributeError):
                pass
                
            # 尝试解析JSON格式
            try:
                import json
                policies = json.loads(content)
                if policies:
                    self.logger.info(f"成功读取JSON格式policy文件: {file_path}")
                    return policies
            except json.JSONDecodeError:
                pass
                
            # 如果前两种格式都失败，尝试按行解析
            policies = self._parse_line_format(content)
            if policies:
                self.logger.info(f"成功读取行格式policy文件: {file_path}")
                return policies
                
            raise ValueError("无法识别的policy文件格式")
                
        except Exception as e:
            self.logger.error(f"读取policy文件失败: {e}")
            raise ValueError(f"无法解析policy文件: {e}")
        
        return policies
    
    def _parse_line_format(self, content: str) -> Dict[str, str]:
        """
        解析行格式的policy内容
        
        Args:
            content: 文件内容
            
        Returns:
            Dict[str, str]: 策略映射
        """
        policies = {}
        lines = content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # 查找冒号分隔符
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    policy_name = parts[0].strip().strip('"\'')
                    policy_expression = parts[1].strip().strip('"\'')
                    policies[policy_name] = policy_expression
                else:
                    self.logger.warning(f"第{line_num}行格式无效: {line}")
            else:
                self.logger.warning(f"第{line_num}行缺少冒号分隔符: {line}")
        
        return policies
    
    def parse_policy_expression(self, expression: str) -> Any:
        """
        使用oslo.policy解析策略表达式
        
        Args:
            expression: 策略表达式
            
        Returns:
            Any: 解析后的策略对象
        """
        try:
            # 使用oslo.policy的parse_rule函数
            parsed_rule = _parser.parse_rule(expression)
            self.debug_log(f"解析结果类型: {type(parsed_rule)}")
            self.debug_log(f"解析结果: {parsed_rule}")
            return parsed_rule
        except Exception as e:
            self.logger.error(f"解析策略表达式失败: {expression}, 错误: {e}")
            return None
    
    def extract_rule_definitions(self, policies: Dict[str, str]) -> None:
        """
        提取规则定义（rule: xxx形式）
        
        Args:
            policies: 策略映射
        """
        self.rule_definitions.clear()
        
        for name, expression in policies.items():
            # 检查是否是规则定义（通常以rule:开头或者表达式较为简单）
            if self._is_rule_definition(name, expression):
                self.rule_definitions[name] = RuleDefinition(name, expression)
                self.debug_log(f"发现规则定义: {name} = {expression}")
    
    def _is_rule_definition(self, name: str, expression: str) -> bool:
        """
        判断是否为规则定义
        
        Args:
            name: 规则名称
            expression: 规则表达式
            
        Returns:
            bool: 是否为规则定义
        """
        # 如果名称以"rule:"开头，则一定是规则定义
        if name.startswith('rule:'):
            return True
            
        # 如果表达式中包含复杂的逻辑操作符，则不是规则定义
        complex_operators = ['and', 'or', 'not']
        for op in complex_operators:
            if f" {op} " in expression.lower():
                return False
        
        # 检查是否是简单的key:value格式
        simple_patterns = [
            r'^role:\w+$',  # role:admin
            r'^user_id:\w+$',  # user_id:xxx
            r'^project_id:\w+$',  # project_id:xxx
            r'^domain_id:\w+$',  # domain_id:xxx
            r'^system_scope:all$',  # system_scope:all
            r'^\w+:\w+$',  # 简单的key:value格式
        ]
        
        for pattern in simple_patterns:
            if re.match(pattern, expression.strip()):
                return True
        
        return False
    
    def substitute_rule_references(self, expression: str) -> str:
        """
        替换表达式中的规则引用
        
        Args:
            expression: 原始表达式
            
        Returns:
            str: 替换后的表达式
        """
        substituted = expression
        
        # 查找所有可能的规则引用
        for rule_name, rule_def in self.rule_definitions.items():
            # 使用正则表达式查找并替换规则引用
            pattern = r'\brule:' + re.escape(rule_name) + r'\b'
            if re.search(pattern, substituted):
                substituted = re.sub(pattern, f"({rule_def.expression})", substituted)
                self.debug_log(f"替换规则引用: {rule_name} -> {rule_def.expression}")
        
        return substituted
    
    def _normalize_field_name(self, field: str) -> Optional[str]:
        """
        标准化字段名
        
        Args:
            field: 原始字段名
            
        Returns:
            str: 标准化后的字段名
        """
        # 如果字段名在映射中，返回映射值
        if field in self.FIELD_MAPPING:
            return self.FIELD_MAPPING[field]
        # 如果字段名已经是标准字段，直接返回
        if field in self.VALID_DB_FIELDS:
            return field
        return None

    def _extract_basic_check(self, check: Any) -> Dict[str, List[str]]:
        """
        从基本检查中提取属性条件
        
        Args:
            check: 基本检查对象
            
        Returns:
            Dict[str, List[str]]: 属性条件字典
        """
        if isinstance(check, _checks.RoleCheck):
            return {'role': [check.match]}
        elif isinstance(check, _checks.GenericCheck):
            # 标准化字段名
            normalized_kind = self._normalize_field_name(check.kind)
            if normalized_kind is None:
                self.logger.warning(
                    f"策略 '{self._current_policy_name}' 包含无效字段 '{check.kind}:{check.match}'，"
                    f"有效字段为: {', '.join(sorted(self.VALID_DB_FIELDS))}"
                )
                return {}
            # 对于GenericCheck，保留原始的%(xxx)s值
            return {normalized_kind: [check.match]}
        elif isinstance(check, _checks.TrueCheck):
            # 对于@或空单元，返回空字典但不视为无效
            return {}
        else:
            try:
                check_str = str(check)
                if ':' in check_str:
                    key, value = check_str.split(':', 1)
                    # 标准化字段名
                    normalized_key = self._normalize_field_name(key)
                    if normalized_key is None:
                        self.logger.warning(
                            f"策略 '{self._current_policy_name}' 包含无效字段 '{key}:{value}'，"
                            f"有效字段为: {', '.join(sorted(self.VALID_DB_FIELDS))}"
                        )
                        return {}
                    return {normalized_key: [value]}
            except Exception as e:
                self.logger.error(f"解析基本条件失败: {e}")
        return {}

    def _combine_conditions(self, conditions_list: List[Dict[str, List[str]]]) -> List[Dict[str, List[str]]]:
        """
        合并多个条件列表，生成所有可能的组合（笛卡尔积）
        
        Args:
            conditions_list: 条件列表
            
        Returns:
            List[Dict[str, List[str]]]: 合并后的条件列表
        """
        if not conditions_list:
            return []
            
        result = [{}]
        for conditions in conditions_list:
            new_result = []
            for base in result:
                for key, values in conditions.items():
                    new_cond = base.copy()
                    if key in new_cond:
                        new_cond[key].extend(values)
                    else:
                        new_cond[key] = values.copy()
                    new_result.append(new_cond)
            result = new_result
            
        return result

    def _extract_minimal_units(self, rule_obj: Any) -> List[Dict[str, List[str]]]:
        """
        递归提取规则中的最小匹配单元
        
        Args:
            rule_obj: 规则对象
            
        Returns:
            List[Dict[str, List[str]]]: 最小匹配单元列表
        """
        self.debug_log(f"处理规则对象: {type(rule_obj)}, {rule_obj}")
        
        if isinstance(rule_obj, _checks.AndCheck):
            # 对于AND操作，需要合并所有子条件（笛卡尔积）
            sub_units_list = []
            for check in rule_obj.rules:
                sub_units = self._extract_minimal_units(check)
                if sub_units:
                    sub_units_list.append(sub_units)
            
            # 生成所有可能的组合
            result = []
            for combination in itertools.product(*sub_units_list):
                merged = {}
                for unit in combination:
                    for key, values in unit.items():
                        if key not in merged:
                            merged[key] = []
                        merged[key].extend(values)
                result.append(merged)
            return result
            
        elif isinstance(rule_obj, _checks.OrCheck):
            # 对于OR操作，创建多个独立的最小匹配单元
            result = []
            for check in rule_obj.rules:
                sub_units = self._extract_minimal_units(check)
                result.extend(sub_units)
            return result
            
        elif isinstance(rule_obj, _checks.NotCheck):
            # 处理NOT操作
            sub_units = self._extract_minimal_units(rule_obj.rule)
            if sub_units:
                result = []
                for unit in sub_units:
                    negated = {}
                    for key, values in unit.items():
                        negated[f"not_{key}"] = values
                    result.append(negated)
                return result
            return []
            
        else:
            # 基本检查条件
            basic_check = self._extract_basic_check(rule_obj)
            return [basic_check] if basic_check else []
    
    def _is_valid_minimal_unit(self, unit: Dict[str, List[str]], policy_name: str) -> bool:
        """
        验证最小匹配单元是否有效
        
        Args:
            unit: 最小匹配单元
            policy_name: 策略名称
            
        Returns:
            bool: 是否有效
        """
        # 检查所有键是否在有效字段列表中
        for key in unit.keys():
            if key not in self.VALID_DB_FIELDS:
                self.logger.warning(
                    f"策略 {policy_name} 的匹配单元包含无效字段 '{key}'，"
                    f"有效字段为: {', '.join(sorted(self.VALID_DB_FIELDS))}"
                )
                return False
        return True

    def store_policy_to_database(self, policy_name: str, minimal_units: List[Dict[str, List[str]]]) -> bool:
        """
        将策略的最小匹配单元存储到数据库
        
        Args:
            policy_name: 策略名称
            minimal_units: 最小匹配单元列表
            
        Returns:
            bool: 存储成功返回True，失败返回False
        """
        try:
            # 如果没有匹配单元，也存储一条空记录
            if not minimal_units:
                self.db.insert_policy_rule(
                    action=policy_name,
                    role=None,
                    user=None,
                    project=None,
                    domain=None,
                    system_scope=None
                )
                return True

            valid_units = 0
            for unit_index, unit in enumerate(minimal_units, 1):
                # 验证最小匹配单元
                if not self._is_valid_minimal_unit(unit, policy_name):
                    self.logger.warning(
                        f"策略 '{policy_name}' 的第 {unit_index} 个匹配单元包含无效字段: {unit}，"
                        f"有效字段为: {', '.join(sorted(self.VALID_DB_FIELDS))}"
                    )
                    continue

                # 从unit中提取各个字段的值，支持多值属性
                role = unit.get('role', [None])[0]  # 角色通常只取第一个
                user = unit.get('user', [None])[0]
                project = unit.get('project', [None])[0]
                # 域ID可能有多个值，用逗号连接
                domain_values = unit.get('domain', [])
                domain = ','.join(domain_values) if domain_values else None
                system_scope = unit.get('system_scope', [None])[0]
                
                # 插入数据库
                self.db.insert_policy_rule(
                    action=policy_name,
                    role=role,
                    user=user,
                    project=project,
                    domain=domain,
                    system_scope=system_scope
                )
                valid_units += 1
                
            return True
            
        except Exception as e:
            self.logger.error(f"存储策略到数据库失败: {e}")
            return False
    
    def process_policy_file(self, file_path: str) -> bool:
        """
        处理policy文件
        
        Args:
            file_path: policy文件路径
            
        Returns:
            bool: 处理成功返回True，失败返回False
        """
        try:
            # 重置计数器
            self.total_policies = 0
            self.total_valid_units = 0
            
            # 读取policy文件
            policies = self.read_policy_file(file_path)
            if not policies:
                self.logger.warning("Policy文件为空")
                return False
                
            # 提取规则定义
            self.extract_rule_definitions(policies)
            
            # 处理每个策略
            for policy_name, expression in policies.items():
                # 跳过注释，但不跳过规则定义
                if policy_name.startswith('#'):
                    continue
                    
                self.total_policies += 1
                self._current_policy_name = policy_name
                
                try:
                    # 解析策略
                    parsed_rule = self.parse_single_policy(policy_name, expression)
                    if parsed_rule is None:
                        continue
                        
                    # 转换为DNF范式的最小匹配单元
                    minimal_units = self._extract_minimal_units(parsed_rule)
                    
                    # 存储到数据库
                    if self.store_policy_to_database(policy_name, minimal_units):
                        self.total_valid_units += len(minimal_units) if minimal_units else 1
                        self.debug_log(f"成功处理策略: {policy_name}")
                    else:
                        self.logger.error(f"存储策略失败: {policy_name}")
                        
                except Exception as e:
                    self.logger.error(f"处理策略 {policy_name} 时出错: {e}")
                    continue
                    
            # 输出统计信息
            self.logger.info(f"总计解析 {self.total_policies} 条策略，生成 {self.total_valid_units} 个有效授权单元")
            return True
            
        except Exception as e:
            self.logger.error(f"处理policy文件失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False


def create_policy_parser(db_path: str = "policy_rules.db") -> PolicyRuleParser:
    """
    创建PolicyRuleParser实例
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        PolicyRuleParser: 解析器实例
    """
    db_instance = get_database_instance(db_path)
    return PolicyRuleParser(db_instance) 
