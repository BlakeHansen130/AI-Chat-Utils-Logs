import re
from bs4 import BeautifulSoup
import html

def process_inline_code(element):
    """
    处理内联代码块，将code标签转换为markdown的内联代码格式
    """
    result = []
    for content in element.contents:
        if content.name == 'code':
            # 使用markdown的内联代码格式 `code`
            result.append(f'`{content.get_text()}`')
        else:
            result.append(str(content.string) if content.string else '')
    return ''.join(result)

def convert_ai_message_to_md(content):
    """
    将AI消息的HTML内容转换为Markdown格式，保持格式化
    """
    soup = BeautifulSoup(content, 'html.parser')
    md_lines = []
    
    for element in soup.children:
        if not element.name:  # 跳过空文本节点
            continue
            
        if element.name == 'p':
            # 普通段落文本
            text = element.get_text().strip()
            md_lines.append(f"{text}\n")
            
        elif element.name == 'ol':
            # 有序列表，先加一个空行
            md_lines.append("")
            # 获取所有列表项
            items = element.find_all('li', recursive=False)
            for i, item in enumerate(items, 1):
                # 使用process_inline_code处理可能包含的code标签
                text = process_inline_code(item)
                # 使用实际的序号
                md_lines.append(f"{i}. {text}")
            md_lines.append("")  # 列表后加空行
            
        elif element.name == 'ul':
            # 无序列表，先加一个空行
            md_lines.append("")
            items = element.find_all('li', recursive=False)
            for item in items:
                # 同样使用process_inline_code处理可能包含的code标签
                text = process_inline_code(item)
                md_lines.append(f"* {text}")
            md_lines.append("")  # 列表后加空行
    
    return "\n".join(md_lines)

[其余代码保持不变...]
