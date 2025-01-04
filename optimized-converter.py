import sys
import re
from bs4 import BeautifulSoup
import html

def process_inline_code(element):
    """处理内联代码块，将code标签转换为markdown的内联代码格式"""
    result = []
    for content in element.contents:
        if content.name == 'code':
            result.append(f'`{content.get_text()}`')
        else:
            result.append(str(content.string) if content.string else '')
    return ''.join(result)

def process_list_item(item, depth=0):
    """递归处理列表项及其子列表"""
    content = process_inline_code(item)
    result = [content]
    
    # 处理子列表
    sublist = item.find(['ul', 'ol'])
    if sublist:
        result.append('')  # 添加空行
        if sublist.name == 'ul':
            for sub_item in sublist.find_all('li', recursive=False):
                result.append(f"{'  ' * (depth + 1)}* {process_list_item(sub_item, depth + 1)}")
        else:  # ol
            for i, sub_item in enumerate(sublist.find_all('li', recursive=False), 1):
                result.append(f"{'  ' * (depth + 1)}{i}. {process_list_item(sub_item, depth + 1)}")
    
    return '\n'.join(result)

def extract_code_block(element):
    """从pre标签中提取代码块内容并转换为markdown格式"""
    # 查找代码语言标识
    lang_div = element.find('div', class_='text-text-300')
    language = lang_div.get_text().strip() if lang_div else ''
    
    # 查找代码内容
    code_div = element.find('div', class_='code-block__code')
    if not code_div:
        return ''
        
    # 提取纯代码文本
    code_content = ''
    code_element = code_div.find('code')
    if code_element:
        for item in code_element.strings:
            code_content += item
            
    code_content = code_content.strip()
    return f"```{language}\n{code_content}\n```\n"

def process_message_content(main_content):
    """按顺序处理消息中的所有内容元素"""
    content_parts = []
    
    if not main_content:
        return ''
    
    # 直接遍历所有子元素，按它们在HTML中的顺序处理
    for element in main_content.children:
        if not element.name:  # 跳过纯文本节点
            continue
            
        if element.name == 'p':
            text = process_inline_code(element)
            if text.strip():
                content_parts.append(text + '\n')
                
        elif element.name == 'pre':
            content_parts.append(extract_code_block(element))
            
        elif element.name == 'ol':
            content_parts.append('')  # 添加空行
            for i, item in enumerate(element.find_all('li', recursive=False), 1):
                content_parts.append(f"{i}. {process_list_item(item)}")
            content_parts.append('')  # 添加空行
            
        elif element.name == 'ul':
            content_parts.append('')  # 添加空行
            for item in element.find_all('li', recursive=False):
                content_parts.append(f"* {process_list_item(item)}")
            content_parts.append('')  # 添加空行
    
    return '\n'.join(content_parts)

def convert_html_to_md(html_content):
    """将HTML格式的聊天记录转换为Markdown格式"""
    # 创建BeautifulSoup对象来解析整个文档
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 直接查找所有用户消息和AI消息
    conversations = []
    
    # 查找所有用户消息
    user_messages = soup.find_all('div', attrs={'data-testid': 'user-message'})
    # 查找所有AI消息
    ai_messages = soup.find_all('div', class_='grid-cols-1', attrs={'class': lambda x: x and 'gap-2.5' in x})
    
    # 合并消息列表，根据它们在文档中的位置排序
    all_messages = []
    for msg in user_messages:
        all_messages.append(('User', msg))
    for msg in ai_messages:
        all_messages.append(('AI', msg))
    
    # 根据元素在文档中的位置排序
    all_messages.sort(key=lambda x: len(str(x[1]).split('\n')))  # 简单的启发式排序
    
    # 处理每个消息
    for speaker, msg in all_messages:
        if speaker == 'User':
            text = ' '.join(p.get_text().strip() for p in msg.find_all('p'))
            if text:
                conversations.append((speaker, text))
        else:
            ai_text = process_message_content(msg)
            if ai_text:
                conversations.append((speaker, ai_text))
    
    # 转换为Markdown格式
    md_content = []
    for speaker, content in conversations:
        md_content.extend([f"\n## {speaker}\n", content])
    
    return '\n'.join(md_content)

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py chat.html")
        sys.exit(1)
    
    input_file = sys.argv[1]
    if not input_file.lower().endswith('.html'):
        print("Error: Input file must be an HTML file (.html)")
        sys.exit(1)
    
    output_file = input_file[:-5] + '.md'
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        print("Converting HTML to Markdown...")
        md_content = convert_html_to_md(html_content)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
            
        print(f"Successfully converted {input_file} to {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()