import os
import sys
from bs4 import BeautifulSoup
import re
import glob

def analyze_html_file(file_path):
    """分析HTML文件并查找关键元素"""
    print(f"分析文件: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. 基本信息
    title = soup.title.text.strip() if soup.title else "无标题"
    print(f"页面标题: {title}")
    
    # 2. 分析表单
    forms = soup.find_all('form')
    print(f"找到 {len(forms)} 个表单")
    
    for i, form in enumerate(forms):
        form_id = form.get('id', '无ID')
        form_name = form.get('name', '无名称')
        form_action = form.get('action', '无动作')
        form_method = form.get('method', 'GET')
        
        print(f"\n表单 {i+1}: ID={form_id}, 名称={form_name}, 方法={form_method}, 动作={form_action}")
        
        # 分析表单内的输入元素
        inputs = form.find_all('input')
        print(f"  表单 {i+1} 包含 {len(inputs)} 个输入元素")
        
        for j, input_elem in enumerate(inputs):
            input_id = input_elem.get('id', '无ID')
            input_name = input_elem.get('name', '无名称')
            input_type = input_elem.get('type', '无类型')
            input_value = input_elem.get('value', '无默认值')
            input_placeholder = input_elem.get('placeholder', '无占位符')
            
            # 只显示可能是日期相关的输入元素或者隐藏字段
            if 'date' in input_id.lower() or 'date' in input_name.lower() or 'date' in input_placeholder.lower() or input_type == 'hidden':
                print(f"  输入元素 {j+1}: ID={input_id}, 名称={input_name}, 类型={input_type}, 值={input_value}, 占位符={input_placeholder}")
    
    # 3. 查找日期选择器相关元素
    date_selectors = []
    
    # 查找可能的日期相关元素
    for elem in soup.find_all(['input', 'div', 'span', 'a', 'button']):
        elem_id = elem.get('id', '').lower()
        elem_class = ' '.join(elem.get('class', [])).lower()
        elem_name = elem.get('name', '').lower()
        
        # 检查ID、类名或名称是否包含日期相关关键词
        if any(keyword in attr for keyword in ['date', 'calendar', 'datepicker', '日期'] 
               for attr in [elem_id, elem_class, elem_name] if attr):
            date_selectors.append(elem)
    
    print(f"\n找到 {len(date_selectors)} 个可能的日期选择器元素")
    for i, elem in enumerate(date_selectors[:10]):  # 只显示前10个
        elem_tag = elem.name
        elem_id = elem.get('id', '无ID')
        elem_class = ' '.join(elem.get('class', []))
        elem_name = elem.get('name', '无名称')
        elem_type = elem.get('type', '无类型') if elem_tag == 'input' else '非输入元素'
        
        print(f"  日期选择器 {i+1}: 标签={elem_tag}, ID={elem_id}, 类={elem_class}, 名称={elem_name}, 类型={elem_type}")
    
    # 4. 查找JavaScript日期选择器初始化代码
    scripts = soup.find_all('script')
    print(f"\n找到 {len(scripts)} 个脚本标签")
    
    datepicker_code = []
    for script in scripts:
        script_text = script.string if script.string else ''
        if script_text and any(keyword in script_text for keyword in ['datepicker', 'calendar', 'date picker', 'daterangepicker']):
            datepicker_code.append(script_text)
    
    if datepicker_code:
        print("\n找到可能的日期选择器初始化代码片段:")
        for i, code in enumerate(datepicker_code):
            # 显示前200个字符作为预览
            print(f"  代码片段 {i+1}: {code[:200]}...")
    else:
        print("\n未找到日期选择器初始化代码")
    
    # 5. 查找可能的搜索或提交按钮
    buttons = []
    for elem in soup.find_all(['button', 'input', 'a']):
        elem_type = elem.get('type', '').lower()
        elem_value = (elem.get('value', '') or elem.text).lower()
        elem_id = elem.get('id', '').lower()
        elem_class = ' '.join(elem.get('class', [])).lower()
        
        # 检查是否为搜索或提交按钮
        if (elem_type == 'submit' or 
            any(keyword in attr for keyword in ['search', 'submit', '搜索', '查询', '查詢'] 
                for attr in [elem_id, elem_class, elem_value] if attr)):
            buttons.append(elem)
    
    print(f"\n找到 {len(buttons)} 个可能的搜索/提交按钮")
    for i, button in enumerate(buttons[:5]):  # 只显示前5个
        button_tag = button.name
        button_id = button.get('id', '无ID')
        button_class = ' '.join(button.get('class', []))
        button_type = button.get('type', '无类型')
        button_value = button.get('value', '') or button.text.strip()
        
        print(f"  按钮 {i+1}: 标签={button_tag}, ID={button_id}, 类={button_class}, 类型={button_type}, 值/文本={button_value}")
    
    # 6. 查找可能的日历图标
    calendar_icons = []
    for elem in soup.find_all(['i', 'span', 'img']):
        elem_class = ' '.join(elem.get('class', [])).lower()
        elem_src = elem.get('src', '').lower() if elem.name == 'img' else ''
        
        if ('calendar' in elem_class or 'date' in elem_class or 
            'fa-calendar' in elem_class or 
            (elem_src and ('calendar' in elem_src or 'date' in elem_src))):
            calendar_icons.append(elem)
    
    print(f"\n找到 {len(calendar_icons)} 个可能的日历图标")
    for i, icon in enumerate(calendar_icons[:5]):  # 只显示前5个
        icon_tag = icon.name
        icon_id = icon.get('id', '无ID')
        icon_class = ' '.join(icon.get('class', []))
        icon_src = icon.get('src', '无源') if icon.name == 'img' else '非图片'
        
        print(f"  图标 {i+1}: 标签={icon_tag}, ID={icon_id}, 类={icon_class}, 源={icon_src}")

    # 7. 分析iframes（有些表单可能在iframe中）
    iframes = soup.find_all('iframe')
    print(f"\n找到 {len(iframes)} 个iframe")
    for i, iframe in enumerate(iframes):
        iframe_id = iframe.get('id', '无ID')
        iframe_name = iframe.get('name', '无名称')
        iframe_src = iframe.get('src', '无源')
        
        print(f"  iframe {i+1}: ID={iframe_id}, 名称={iframe_name}, 源={iframe_src}")

def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 如果提供了文件路径参数
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            analyze_html_file(file_path)
        else:
            print(f"文件不存在: {file_path}")
    else:
        # 如果没有提供参数，列出所有debug_*.html文件
        html_files = glob.glob("debug_*.html")
        
        if not html_files:
            print("当前目录中找不到debug_*.html文件")
            return
        
        print("可用的HTML文件:")
        for i, file in enumerate(html_files):
            print(f"{i+1}. {file}")
        
        try:
            choice = int(input("\n请选择要分析的文件编号（输入0分析所有文件）: "))
            if choice == 0:
                for file in html_files:
                    analyze_html_file(file)
                    print("\n" + "="*50 + "\n")
            elif 1 <= choice <= len(html_files):
                analyze_html_file(html_files[choice-1])
            else:
                print("无效的选择")
        except ValueError:
            print("请输入有效的数字")

if __name__ == "__main__":
    main() 