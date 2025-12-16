import yaml
from typing import Dict, Any, List
import re
from policy_split import split_all_or_expressions
from output_control import general_print as print


def _find_unquoted_colon(line: str) -> int:
    """返回未被引号包裹的第一个冒号位置，找不到则返回-1"""
    in_single = False
    in_double = False
    escaped = False

    for idx, ch in enumerate(line):
        if escaped:
            escaped = False
            continue

        if ch == '\\':
            escaped = True
            continue

        if ch == "'" and not in_double:
            in_single = not in_single
            continue

        if ch == '"' and not in_single:
            in_double = not in_double
            continue

        if ch == ':' and not in_single and not in_double:
            return idx

    return -1

def read_yaml_and_split_by_colon(file_path: str) -> Dict[str, str]:
    """
    读取YAML文件，使用第一个冒号分割每一行，返回字典
    """
    result = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            yaml_content = yaml.safe_load(file)
            
            if yaml_content and isinstance(yaml_content, dict):
                return {str(k): str(v) for k, v in yaml_content.items()}
    
    except yaml.YAMLError:
        pass
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                
                if not line or line.startswith('#'):
                    continue
                
                colon_index = _find_unquoted_colon(line)
                if colon_index == -1:
                    continue
                key = line[:colon_index].strip().strip('"\'')
                value = line[colon_index + 1:].strip().strip('"\'')
                result[key] = value
    
    except Exception as e:
        print(f"错误: 读取文件时发生异常: {e}")
    
    return result

def resolve_rule_references(policy_dict: Dict[str, str]) -> Dict[str, str]:
    """
    解析字典中的 rule: 引用，将其替换为对应key的value
    
    Args:
        policy_dict: 包含策略规则的字典
        
    Returns:
        Dict[str, str]: 解析后的字典
    """
    # 创建结果字典的副本
    resolved_dict = policy_dict.copy()
    
    # 用于检测循环引用
    resolving_stack = set()
    
    def resolve_value(key: str, value: str, depth: int = 0) -> str:
        """
        递归解析单个value中的rule引用
        
        Args:
            key: 当前正在解析的key（用于检测循环引用）
            value: 要解析的value
            depth: 递归深度（防止无限递归）
            
        Returns:
            str: 解析后的value
        """
        if depth > 50:  # 防止无限递归
            print(f"警告: 递归深度过深，可能存在循环引用: {key}")
            return value
        
        if key in resolving_stack:
            print(f"警告: 检测到循环引用: {key}")
            return value
        
        # 查找所有 rule: 引用
        rule_pattern = r'rule:(\w+)'
        matches = re.findall(rule_pattern, value)
        
        if not matches:
            return value
        
        resolving_stack.add(key)
        resolved_value = value
        
        for rule_key in matches:
            if rule_key in policy_dict:
                # 递归解析引用的规则
                referenced_value = resolve_value(rule_key, policy_dict[rule_key], depth + 1)
                
                # 替换 rule:rule_key 为实际的值
                # 使用括号包围替换的内容以保持逻辑正确性
                replacement = f"({referenced_value})"
                resolved_value = re.sub(f'rule:{rule_key}\\b', replacement, resolved_value)
            else:
                print(f"警告: 未找到引用的规则: {rule_key}")
        
        resolving_stack.discard(key)
        return resolved_value
    
    # 解析所有规则
    for key, value in policy_dict.items():
        resolved_dict[key] = resolve_value(key, value)
    
    return resolved_dict

def extract_policy_entries(file_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    扫描策略文件，记录每个策略键出现的行号及原始表达式
    """
    entry_map: Dict[str, List[Dict[str, Any]]] = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    continue
                colon_index = _find_unquoted_colon(line)
                if colon_index == -1:
                    continue
                key = line[:colon_index].strip().strip('"\'')
                value = line[colon_index + 1:].strip().strip('"\'')
                if key:
                    entry_map.setdefault(key, []).append({
                        'line': line_num,
                        'value': value
                    })
    except Exception as e:
        print(f"警告: 无法读取策略文件行号信息 {file_path}: {e}")
    return entry_map

def process_policy_file(file_path: str) -> Dict[str, Dict[str, Any]]:
    """
    处理策略文件：读取并解析rule引用
    
    Args:
        file_path: YAML文件路径
        
    Returns:
        Dict[str, str]: 处理后的策略字典
    """
    # 读取原始字典
    policy_dict = read_yaml_and_split_by_colon(file_path)
    
    print(f"读取了 {len(policy_dict)} 个策略规则")
    entry_map = extract_policy_entries(file_path)
    
    # 解析rule引用
    resolved_dict = resolve_rule_references(policy_dict)
    
    enriched_result: Dict[str, Dict[str, Any]] = {}
    for key, expression in resolved_dict.items():
        entries = entry_map.get(key, [])
        enriched_result[key] = {
            'expression': expression,
            'file': file_path,
            'lines': [item['line'] for item in entries],
            'raw_entries': entries
        }
    
    return enriched_result

# 使用示例
if __name__ == "__main__":

    # 测试用例
    yaml_file_path = "small.yaml"  
    
    # 读取并分割
    test_policy = read_yaml_and_split_by_colon(yaml_file_path)

    print("原始策略:")
    for key, value in test_policy.items():
        print(f"  {key}: {value}")
    
    print("\n=== 解析结果 ===")
    resolved = resolve_rule_references(test_policy)
    
    print("解析后的策略:")
    for key, value in resolved.items():
        print(f"  {key}: {value}")

    for key, value in resolved.items():
        split_values = split_all_or_expressions(value)
        print(f"\n策略键: {key}")
        print("分割后的表达式:")
        for expr in split_values:
            print(f"  {expr}")
        resolved[key]  = split_values

    print(resolved)
    

    
