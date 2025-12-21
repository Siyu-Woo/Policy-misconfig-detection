import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

def extract_policy_info(url):
    """
    从OpenStack Keystone policy文档中提取策略信息
    
    Args:
        url: Keystone policy文档的URL
    
    Returns:
        list: 包含策略信息的字典列表
    """
    # 发送HTTP请求获取页面内容
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    
    policies = []
    
    # 查找所有包含策略名称的dt标签
    policy_dts = soup.find_all('dt')
    
    # 过滤出包含identity:开头的策略名称的dt标签
    filtered_dts = []
    for dt in policy_dts:
        code_tag = dt.find('code', class_='docutils literal notranslate')
        if code_tag:
            text = code_tag.get_text(strip=True)
            if text.startswith('identity:'):
                filtered_dts.append(dt)
    
    print(f"找到 {len(filtered_dts)} 个策略定义")
    
    # 如果没找到，输出调试信息
    if len(filtered_dts) == 0:
        print("\n调试信息：")
        print(f"总共找到 {len(policy_dts)} 个dt标签")
        return policies
    
    for idx, dt in enumerate(filtered_dts, 1):
        # 提取策略名称
        code_tag = dt.find('code', class_='docutils literal notranslate')
        if not code_tag:
            continue
        
        policy_name = code_tag.get_text(strip=True)
        
        # 查找对应的dd标签（紧跟在dt后面）
        dd = dt.find_next_sibling('dd')
        if not dd:
            print(f"  策略 {idx}: {policy_name} - 未找到详细信息")
            continue
        
        # 提取Default值
        default_value = ""
        # 在dd内查找class为field-list的dl标签
        field_list = dd.find('dl', class_='field-list')
        if field_list:
            # 查找所有的field dt标签
            field_dts = field_list.find_all('dt', class_='field-odd') + field_list.find_all('dt', class_='field-even')
            
            for field_dt in field_dts:
                field_name = field_dt.get_text(strip=True)
                field_dd = field_dt.find_next_sibling('dd')
                
                # 提取Default
                if 'Default' in field_name:
                    if field_dd:
                        default_p = field_dd.find('p')
                        if default_p:
                            default_code = default_p.find('code')
                            if default_code:
                                default_value = default_code.get_text(strip=True)
                            else:
                                default_value = default_p.get_text(strip=True)
        
        # 提取Operations
        operations = []
        if field_list:
            field_dts = field_list.find_all('dt', class_='field-odd') + field_list.find_all('dt', class_='field-even')
            
            for field_dt in field_dts:
                field_name = field_dt.get_text(strip=True)
                field_dd = field_dt.find_next_sibling('dd')
                
                # 提取Operations
                if 'Operations' in field_name:
                    if field_dd:
                        operation_items = field_dd.find_all('li')
                        for item in operation_items:
                            # 提取HTTP方法和URL
                            item_p = item.find('p')
                            if item_p:
                                strong = item_p.find('strong')
                                code = item_p.find('code')
                                if strong and code:
                                    method = strong.get_text(strip=True)
                                    url_path = code.get_text(strip=True)
                                    operations.append(f"{method} {url_path}")
                                else:
                                    # 尝试直接从p标签提取
                                    text = item_p.get_text(strip=True)
                                    if text:
                                        operations.append(text)
                            else:
                                # 如果没有p标签，直接从li提取
                                text = item.get_text(strip=True)
                                if text:
                                    operations.append(text)
        
        # 提取Scope Types
        scope_types = []
        if field_list:
            field_dts = field_list.find_all('dt', class_='field-odd') + field_list.find_all('dt', class_='field-even')
            
            for field_dt in field_dts:
                field_name = field_dt.get_text(strip=True)
                field_dd = field_dt.find_next_sibling('dd')
                
                # 提取Scope Types
                if 'Scope Types' in field_name or 'Scope Type' in field_name:
                    if field_dd:
                        # 查找所有li标签
                        scope_items = field_dd.find_all('li')
                        for item in scope_items:
                            item_p = item.find('p')
                            if item_p:
                                strong = item_p.find('strong')
                                if strong:
                                    scope_types.append(strong.get_text(strip=True))
                                else:
                                    scope_types.append(item_p.get_text(strip=True))
                            else:
                                # 直接从li提取
                                text = item.get_text(strip=True)
                                if text:
                                    scope_types.append(text)
        
        scope_types_str = ", ".join(scope_types) if scope_types else ""
        
        # 提取描述（dd标签中直接的p标签，不在field-list内的）
        description = ""
        for child in dd.children:
            if child.name == 'p':
                description = child.get_text(strip=True)
                break
        
        # 如果有多个Operations，每个占一行
        if operations:
            for operation in operations:
                policies.append({
                    '策略名称': policy_name,
                    'Default': default_value,
                    'Operations': operation,
                    'Scope Types': scope_types_str,
                    '描述': description
                })
        else:
            # 如果没有Operations，也添加一条记录
            policies.append({
                '策略名称': policy_name,
                'Default': default_value,
                'Operations': "",
                'Scope Types': scope_types_str,
                '描述': description
            })
        
        print(f"  策略 {idx}: {policy_name}")
        print(f"    Default: {default_value}")
        print(f"    Operations: {len(operations)} 个")
        print(f"    Scope Types: {scope_types_str}")
    
    return policies

def save_to_excel(policies, filename='keystone_policies.xlsx'):
    """
    将策略信息保存到Excel文件
    
    Args:
        policies: 策略信息列表
        filename: 输出的Excel文件名
    """
    if not policies:
        print("没有数据可保存")
        return
    
    df = pd.DataFrame(policies)
    
    # 创建Excel writer对象
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Keystone Policies')
        
        # 自动调整列宽
        worksheet = writer.sheets['Keystone Policies']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(col)
            ) + 2
            # Excel列索引从A开始
            col_letter = chr(65 + idx) if idx < 26 else f"A{chr(65 + idx - 26)}"
            worksheet.column_dimensions[col_letter].width = min(max_length, 50)
    
    print(f"\n成功保存 {len(policies)} 条策略记录到 {filename}")

def main():
    # Keystone policy文档URL
    policy_url = "https://docs.openstack.org/keystone/latest/configuration/policy.html"
    
    print(f"正在从 {policy_url} 提取策略信息...\n")
    
    try:
        policies = extract_policy_info(policy_url)
        
        if policies:
            print(f"\n共提取到 {len(policies)} 条策略记录")
            print("\n前3条策略示例:")
            for i, policy in enumerate(policies[:3], 1):
                print(f"\n{i}. {policy['策略名称']}")
                print(f"   Default: {policy['Default']}")
                print(f"   Operations: {policy['Operations']}")
                print(f"   Scope Types: {policy['Scope Types']}")
                print(f"   描述: {policy['描述']}")
            
            # 保存到Excel
            save_to_excel(policies, 'keystone_policies.xlsx')
        else:
            print("\n未找到任何策略信息，请检查URL和HTML结构")
    
    except requests.RequestException as e:
        print(f"请求失败: {e}")
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()