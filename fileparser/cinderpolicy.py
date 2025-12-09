import requests
from bs4 import BeautifulSoup
import pandas as pd

def extract_cinder_policy(url):
    """
    从 OpenStack Cinder policy 文档中提取策略信息
    
    Args:
        url: Cinder policy 文档的 URL
    
    Returns:
        DataFrame 包含策略名称、Default、Operations 和描述
    """
    # 发送请求获取页面内容
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 存储提取的数据
    policy_data = []
    
    # 查找所有的 dt 标签（包含策略名称）
    dt_tags = soup.find_all('dt')
    
    for dt in dt_tags:
        # 提取策略名称
        policy_name_tag = dt.find('code', class_='docutils literal notranslate')
        if not policy_name_tag:
            continue
            
        policy_name = policy_name_tag.get_text(strip=True)
        
        # 找到对应的 dd 标签（包含详细信息）
        dd = dt.find_next_sibling('dd')
        if not dd:
            continue
        
        # 提取 Default 值
        default_value = 'N/A'
        field_list = dd.find('dl', class_='field-list')
        if field_list:
            default_dt = field_list.find('dt', string='Default')
            if default_dt:
                default_dd = default_dt.find_next_sibling('dd')
                if default_dd:
                    default_code = default_dd.find('code')
                    if default_code:
                        default_value = default_code.get_text(strip=True)
        
        # 提取 Operations
        operations = []
        if field_list:
            operations_dt = field_list.find('dt', string='Operations')
            if operations_dt:
                operations_dd = operations_dt.find_next_sibling('dd')
                if operations_dd:
                    # 查找所有的 li 标签
                    li_tags = operations_dd.find_all('li')
                    for li in li_tags:
                        # 提取 HTTP 方法和路径
                        operation_text = li.get_text(strip=True)
                        operations.append(operation_text)
        
        # 提取描述（在 field-list 之后的 p 标签）
        description = 'N/A'
        description_p = dd.find('p', recursive=False)
        if description_p:
            description = description_p.get_text(strip=True)
        else:
            # 如果没有直接的 p 标签，查找 field-list 后面的 p 标签
            if field_list:
                next_p = field_list.find_next_sibling('p')
                if next_p:
                    description = next_p.get_text(strip=True)
        
        # 如果没有 Operations，添加一条记录
        if not operations:
            policy_data.append({
                '策略名称': policy_name,
                'Default': default_value,
                'Operations': 'N/A',
                '描述': description
            })
        else:
            # 每个 Operation 单独占一行
            for operation in operations:
                policy_data.append({
                    '策略名称': policy_name,
                    'Default': default_value,
                    'Operations': operation,
                    '描述': description
                })
    
    return pd.DataFrame(policy_data)

def main():
    # OpenStack Cinder policy 文档 URL
    url = 'https://docs.openstack.org/cinder/2023.1/configuration/block-storage/policy.html'
    
    print(f"正在从 {url} 提取策略信息...")
    print("-" * 80)
    
    try:
        # 提取策略数据
        df = extract_cinder_policy(url)
        
        if len(df) == 0:
            print("\n警告: 未提取到任何策略信息，请检查页面结构")
            return
        
        # 输出到 Excel 文件
        output_file = 'cinder_policy_list.xlsx'
        df.to_excel(output_file, index=False, engine='openpyxl')
        
        print(f"成功提取 {len(df)} 条策略记录")
        print(f"数据已保存到 {output_file}")
        print("-" * 80)
        
        # 打印前几条记录预览
        print("\n前10条记录预览:")
        print(df.head(10).to_string())
        
        # 打印统计信息
        unique_policies = df['策略名称'].nunique()
        print(f"\n共有 {unique_policies} 个不同的策略")
        
    except Exception as e:
        print(f"\n提取失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()