import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

def extract_keystone_apis(url):
    """
    从OpenStack官方文档中提取Keystone API信息
    
    Args:
        url: OpenStack Keystone API文档的URL
    
    Returns:
        list: 包含API信息的字典列表
    """
    # 发送HTTP请求获取页面内容
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    
    apis = []
    
    # 查找所有的operation-grp容器
    operation_groups = soup.find_all('div', class_='operation-grp container')
    
    print(f"找到 {len(operation_groups)} 个API操作组")
    
    for idx, group in enumerate(operation_groups, 1):
        # 提取API名称
        api_name_tag = group.find('p', class_='url-subtitle')
        if not api_name_tag:
            print(f"  组 {idx}: 未找到API名称")
            continue
        api_name = api_name_tag.get_text(strip=True)
        
        # 提取HTTP方法 - 查找class包含"label-"的span标签
        method_tag = group.find('span', class_=re.compile(r'badge\s+label-'))
        if not method_tag:
            print(f"  组 {idx}: 未找到HTTP方法 ({api_name})")
            continue
        
        # 从class中提取方法名，例如从"badge label-HEAD"中提取"HEAD"
        method_classes = method_tag.get('class', [])
        method = None
        for cls in method_classes:
            if cls.startswith('label-'):
                method = cls.replace('label-', '').upper()
                break
        
        if not method:
            method = method_tag.get_text(strip=True).upper()
        
        # 提取endpoint URL
        endpoint_tag = group.find(class_='endpoint-url')
        if not endpoint_tag:
            print(f"  组 {idx}: 未找到endpoint URL ({api_name})")
            continue
        endpoint = endpoint_tag.get_text(strip=True)
        
        # 合并HTTP方法和endpoint
        api_endpoint = f"{method} {endpoint}"
        
        apis.append({
            'API名称': api_name,
            'API端点': api_endpoint,
            'HTTP方法': method,
            'URL路径': endpoint
        })
        
        print(f"  组 {idx}: {method} {endpoint} - {api_name}")
    
    return apis

def save_to_excel(apis, filename='keystone_apis.xlsx'):
    """
    将API信息保存到Excel文件
    
    Args:
        apis: API信息列表
        filename: 输出的Excel文件名
    """
    if not apis:
        print("没有数据可保存")
        return
    
    df = pd.DataFrame(apis)
    
    # 创建Excel writer对象
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Keystone APIs')
        
        # 自动调整列宽
        worksheet = writer.sheets['Keystone APIs']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(col)
            ) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = max_length
    
    print(f"\n成功保存 {len(apis)} 个API到 {filename}")

def main():
    # OpenStack Keystone API文档URL
    # 请根据实际情况修改URL
    keystone_api_url = "https://docs.openstack.org/api-ref/identity/v3/"
    
    print(f"正在从 {keystone_api_url} 提取API信息...\n")
    
    try:
        apis = extract_keystone_apis(keystone_api_url)
        
        if apis:
            print(f"\n共提取到 {len(apis)} 个API")
            print("\n前3个API示例:")
            for i, api in enumerate(apis[:3], 1):
                print(f"\n{i}. {api['API名称']}")
                print(f"   端点: {api['API端点']}")
            
            # 保存到Excel
            save_to_excel(apis, 'keystone_apis.xlsx')
        else:
            print("\n未找到任何API信息，请检查URL和HTML结构")
    
    except requests.RequestException as e:
        print(f"请求失败: {e}")
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()