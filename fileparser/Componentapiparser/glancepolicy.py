import requests
from bs4 import BeautifulSoup
import pandas as pd

def debug_html_structure(url):
    """
    调试 HTML 结构
    """
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 找到第一个策略条目
    dt_tags = soup.find_all('dt')
    
    for dt in dt_tags[:3]:  # 只查看前3个
        policy_name_tag = dt.find('code', class_='docutils literal notranslate')
        if not policy_name_tag:
            continue
        
        policy_name = policy_name_tag.get_text(strip=True)
        print(f"\n{'='*80}")
        print(f"策略名称: {policy_name}")
        print(f"{'='*80}")
        
        dd = dt.find_next_sibling('dd')
        if dd:
            print("\ndd 标签的完整 HTML:")
            print(dd.prettify()[:2000])  # 只打印前2000字符
            print("\n" + "="*80)

def extract_glance_policy(url):
    """
    从 OpenStack Glance policy 文档中提取策略信息
    """
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    
    policy_data = []
    dt_tags = soup.find_all('dt')
    
    print(f"找到 {len(dt_tags)} 个 dt 标签\n")
    
    for idx, dt in enumerate(dt_tags, 1):
        policy_name_tag = dt.find('code', class_='docutils literal notranslate')
        if not policy_name_tag:
            continue
            
        policy_name = policy_name_tag.get_text(strip=True)
        print(f"[{idx}] 处理策略: {policy_name}")
        
        dd = dt.find_next_sibling('dd')
        if not dd:
            continue
        
        default_value = 'N/A'
        operations = []
        scope_types = []
        description = 'N/A'
        
        # 查找 field-list
        field_list = dd.find('dl', class_='field-list')
        
        if field_list:
            # 获取所有的 dt 和 dd 对
            field_items = field_list.find_all('dt', recursive=False)
            
            for field_dt in field_items:
                field_text = field_dt.get_text(strip=True)
                field_dd = field_dt.find_next_sibling('dd')
                
                if not field_dd:
                    continue
                
                # 提取 Default
                if 'Default' in field_text:
                    p_tag = field_dd.find('p')
                    if p_tag:
                        code_tag = p_tag.find('code')
                        if code_tag:
                            default_value = code_tag.get_text(strip=True)
                        else:
                            default_value = p_tag.get_text(strip=True)
                    print(f"  Default: {default_value[:100]}")
                
                # 提取 Operations
                elif 'Operations' in field_text or 'Operation' in field_text:
                    ul_tag = field_dd.find('ul')
                    if ul_tag:
                        li_tags = ul_tag.find_all('li')
                        for li in li_tags:
                            op_text = li.get_text(strip=True)
                            operations.append(op_text)
                            print(f"  Operation: {op_text}")
                
                # 提取 Scope Types
                elif 'Scope' in field_text:
                    ul_tag = field_dd.find('ul')
                    if ul_tag:
                        li_tags = ul_tag.find_all('li')
                        for li in li_tags:
                            scope_text = li.get_text(strip=True)
                            scope_types.append(scope_text)
                            print(f"  Scope Type: {scope_text}")
        
        # 提取描述 - 查找 dd 下直接的 p 标签（不在 field-list 中的）
        for p_tag in dd.find_all('p', recursive=False):
            if not p_tag.find_parent('dl'):
                description = p_tag.get_text(strip=True)
                break
        
        # 如果上面没找到，尝试查找 field-list 后面的 p 标签
        if description == 'N/A' and field_list:
            next_elem = field_list.find_next_sibling()
            while next_elem:
                if next_elem.name == 'p':
                    description = next_elem.get_text(strip=True)
                    break
                next_elem = next_elem.find_next_sibling()
        
        print(f"  描述: {description[:100]}")
        
        scope_types_str = ', '.join(scope_types) if scope_types else 'N/A'
        
        if not operations:
            policy_data.append({
                '策略名称': policy_name,
                'Default': default_value,
                'Operations': 'N/A',
                'Scope Types': scope_types_str,
                '描述': description
            })
        else:
            for operation in operations:
                policy_data.append({
                    '策略名称': policy_name,
                    'Default': default_value,
                    'Operations': operation,
                    'Scope Types': scope_types_str,
                    '描述': description
                })
    
    return pd.DataFrame(policy_data)

def main():
    url = 'https://docs.openstack.org/glance/latest/configuration/glance_policy.html'
    
    print("首先调试 HTML 结构:")
    print("="*80)
    debug_html_structure(url)
    
    print("\n\n开始提取数据:")
    print("="*80)
    
    try:
        df = extract_glance_policy(url)
        
        if len(df) == 0:
            print("\n警告: 未提取到任何策略信息")
            return
        
        output_file = 'glance_policy_list.xlsx'
        df.to_excel(output_file, index=False, engine='openpyxl')
        
        print(f"\n成功提取 {len(df)} 条策略记录")
        print(f"数据已保存到 {output_file}")
        print("\n前5条记录:")
        print(df.head(5).to_string())
        
    except Exception as e:
        print(f"\n提取失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()