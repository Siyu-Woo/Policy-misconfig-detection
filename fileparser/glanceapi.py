import requests
from bs4 import BeautifulSoup
import pandas as pd

def extract_cinder_api(url):
    """
    从 OpenStack Cinder 文档中提取 API 信息
    
    Args:
        url: Cinder API 文档的 URL
    
    Returns:
        DataFrame 包含 API 名称、HTTP 方法和端点 URL
    """
    # 发送请求获取页面内容
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 存储提取的数据
    api_data = []
    
    # 查找所有的 operation-grp container
    operation_groups = soup.find_all('div', class_='operation-grp container')
    
    for group in operation_groups:
        # 提取 HTTP 方法 (在 operation div 里面的 span badge)
        http_method_tag = group.find('span', class_=lambda x: x and 'badge label-' in x)
        http_method = http_method_tag.get_text(strip=True) if http_method_tag else 'N/A'
        
        # 提取端点 URL (在 endpoint-url div 里)
        endpoint_tag = group.find('div', class_='endpoint-url')
        endpoint_url = endpoint_tag.get_text(strip=True) if endpoint_tag else 'N/A'
        
        # 提取 API 名称 (在 url-subtitle p 标签里)
        api_name_tag = group.find('p', class_='url-subtitle')
        api_name = api_name_tag.get_text(strip=True) if api_name_tag else 'N/A'
        
        # 合并 HTTP 方法和端点 URL
        full_endpoint = f"{http_method} {endpoint_url}"
        
        # 添加到列表
        api_data.append({
            'API名称': api_name,
            'HTTP方法': http_method,
            '端点URL': endpoint_url,
            '完整端点': full_endpoint
        })
    
    return pd.DataFrame(api_data)

def main():
    # OpenStack Cinder API 文档 URL
    url = 'https://docs.openstack.org/api-ref/image/v2/'
    
    print(f"正在从 {url} 提取 API 信息...")
    
    try:
        # 提取 API 数据
        df = extract_cinder_api(url)
        
        # 输出到 Excel 文件
        output_file = 'glance_apis.xlsx'
        df.to_excel(output_file, index=False, engine='openpyxl')
        
        print(f"成功提取 {len(df)} 个 API")
        print(f"数据已保存到 {output_file}")
        
        # 打印前几条记录预览
        print("\n前5条记录预览:")
        print(df.head().to_string())
        
    except Exception as e:
        print(f"提取失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()