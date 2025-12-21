import requests
from bs4 import BeautifulSoup
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

def extract_nova_apis(url):
    """
    从OpenStack Nova官方文档提取API信息
    
    Args:
        url: Nova API文档的URL
    
    Returns:
        list: 包含API信息的字典列表
    """
    # 获取网页内容
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers)
    response.encoding = 'utf-8'
    
    # 解析HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 存储API信息
    api_list = []
    
    # 查找所有的operation-grp container
    operation_groups = soup.find_all('div', class_='operation-grp container')
    
    for group in operation_groups:
        # 提取API名称
        api_name_tag = group.find('p', class_='url-subtitle')
        if api_name_tag:
            api_name = api_name_tag.get_text(strip=True)
        else:
            continue
        
        # 提取HTTP方法和endpoint URL
        endpoint_tag = group.find(class_='endpoint-url')
        if endpoint_tag:
            # 通常HTTP方法在endpoint-url的前面或里面
            method_tag = group.find(class_='method')
            if method_tag:
                http_method = method_tag.get_text(strip=True).upper()
            else:
                # 尝试从endpoint-url的兄弟元素或父元素中查找
                method_tags = group.find_all(['span', 'strong', 'b'])
                http_method = 'GET'  # 默认值
                for tag in method_tags:
                    text = tag.get_text(strip=True).upper()
                    if text in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                        http_method = text
                        break
            
            endpoint_url = endpoint_tag.get_text(strip=True)
            full_endpoint = f"{http_method} {endpoint_url}"
        else:
            full_endpoint = "N/A"
        
        # 添加到列表
        api_list.append({
            'API名称': api_name,
            'Endpoint': full_endpoint,
            'HTTP方法': http_method if 'http_method' in locals() else '',
            'URL路径': endpoint_url if 'endpoint_url' in locals() else ''
        })
    
    return api_list

def save_to_excel(api_list, output_file='nova_apis.xlsx'):
    """
    将API信息保存到Excel文件
    
    Args:
        api_list: API信息列表
        output_file: 输出文件名
    """
    # 创建DataFrame
    df = pd.DataFrame(api_list)
    
    # 保存到Excel
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Nova APIs')
        
        # 获取工作表
        workbook = writer.book
        worksheet = writer.sheets['Nova APIs']
        
        # 设置列宽
        worksheet.column_dimensions['A'].width = 40
        worksheet.column_dimensions['B'].width = 50
        worksheet.column_dimensions['C'].width = 15
        worksheet.column_dimensions['D'].width = 40
        
        # 设置标题行样式
        for cell in worksheet[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
    
    print(f"✅ 成功提取 {len(api_list)} 个API，已保存到 {output_file}")

def main():
    # OpenStack Nova API文档URL
    # 请替换为实际的文档URL
    nova_api_url = 'https://docs.openstack.org/api-ref/compute/'
    
    print(f"🔍 正在从 {nova_api_url} 提取API信息...")
    
    try:
        api_list = extract_nova_apis(nova_api_url)
        
        if api_list:
            save_to_excel(api_list)
            
            # 打印前5个API作为示例
            print("\n📋 提取的API示例（前5个）：")
            for i, api in enumerate(api_list[:5], 1):
                print(f"{i}. {api['API名称']} - {api['Endpoint']}")
        else:
            print("⚠️  未找到任何API信息，请检查URL或HTML结构")
            
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()