import sys
import re
from bs4 import BeautifulSoup
import html
from bs4.element import Tag

def process_latex(element):
    """
    处理LaTeX公式
    """
    tex = element.find('annotation', encoding='application/x-tex')
    if tex:
        return f'$${tex.get_text()}$$'
    return ''

def process_inline_code(element):
    """
    处理内联代码块，以及其他内联格式如斜体、粗体等
    """
    result = []
    for content in element.contents:
        if isinstance(content, Tag):
            if content.name == 'em':
                result.append(f'*{content.get_text()}*')
            elif content.name == 'strong':
                result.append(f'**{content.get_text()}**')
            elif content.name == 'code':
                result.append(f'`{content.get_text()}`')
            elif 'math' in content.get('class', []):
                result.append(process_latex(content.find('semantics')))
            else:
                result.append(content.get_text())
        elif isinstance(content, str):
            result.append(content)
        else:
            result.append(str(content.string) if content.string else '')
    return ''.join(result)

def process_table(table_element):
    """
    将HTML表格转换为Markdown格式的表格
    """
    md_table = []
    
    # 处理表头
    header_cells = table_element.find('thead').find_all('th')
    if header_cells:
        # 添加表头行
        header_row = '| ' + ' | '.join(cell.get_text().strip() for cell in header_cells) + ' |'
        md_table.append(header_row)
        # 添加分隔行
        separator = '| ' + ' | '.join(['---'] * len(header_cells)) + ' |'
        md_table.append(separator)
    
    # 处理表体
    tbody = table_element.find('tbody')
    if tbody:
        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            row_content = '| ' + ' | '.join(cell.get_text().strip() for cell in cells) + ' |'
            md_table.append(row_content)
    
    return '\n'.join(md_table) + '\n'

def extract_code_block(element):
    """
    从pre标签中提取代码块内容并转换为markdown格式
    特别处理"示例输出"类型的代码块
    """
    # 首先检查是否为表格
    if element.find('table'):
        return process_table(element.find('table'))
    
    # 首先尝试查找 text-text-300 类的div来获取语言
    lang_div = element.find('div', class_='text-text-300')
    
    # 检查是否为示例输出代码块
    code_element = element.find('code')
    if code_element and code_element.get('class') is None:
        # 这可能是一个示例输出代码块，直接作为普通文本处理
        text = code_element.get_text().strip()
        if text:
            return text + "\n"
        return ''
    
    # 处理正常代码块
    if not lang_div:
        # 查找所有 div，检查text content
        all_divs = element.find_all('div')
        for div in all_divs:
            text_content = div.get_text().strip().lower()
            if text_content in ['python', 'bash', 'javascript', 'html', 'css', 'java', 'cpp', 'c++', 'c', 'markdown']:
                lang_div = div
                break
    
    language = lang_div.get_text().strip() if lang_div else ''
    
    # 查找代码内容
    code_div = element.find('div', class_='code-block__code')
    if not code_div:
        code_div = element
    
    if not code_div:
        return ''
        
    # 提取代码内容
    code_content = ''
    code_element = code_div.find('code')
    if code_element:
        # 获取所有文本节点
        for item in code_element.strings:
            code_content += item
            
    # 确保代码内容两端没有多余的空行
    code_content = code_content.strip()
    
    # 特殊处理：如果代码内容看起来像普通文本（没有特殊格式和缩进），则作为普通文本处理
    lines = code_content.split('\n')
    if len(lines) == 1 and not any(char in code_content for char in '{}[]()=><'):
        return code_content + "\n"
    
    # 按markdown代码块格式返回
    if language:
        return f"```{language}\n{code_content}\n```\n"
    else:
        return f"```\n{code_content}\n```\n"
def process_list_items(element, depth=0, start_number=1):
    """
    递归处理列表及其嵌套列表
    """
    result = []
    items = element.find_all('li', recursive=False)
    
    is_ordered = element.name == 'ol'
    indent = "    " * depth  # 使用4个空格作为缩进
    current_number = start_number
    
    for item in items:
        # 处理当前列表项的文本（包括可能的内联代码）
        content = process_inline_code(item)
        
        # 处理嵌套列表前的内容
        main_content = content
        nested_lists = item.find_all(['ul', 'ol'], recursive=False)
        if nested_lists:
            # 如果有嵌套列表，需要分离主要内容和嵌套列表
            first_text = item.find(string=True, recursive=False)
            if first_text and first_text.parent:
                main_content = process_inline_code(first_text.parent)
        
        # 添加列表项标记
        if is_ordered:
            result.append(f"{indent}{current_number}. {main_content}")
            current_number += 1
        else:
            result.append(f"{indent}* {main_content}")
            
        # 处理列表项中的代码块
        code_blocks = item.find_all('pre', recursive=True)
        if code_blocks:
            for code_block in code_blocks:
                # 确保代码块前有空行
                result.append("")
                # 提取并添加代码块
                result.append(extract_code_block(code_block))
            
        # 处理嵌套列表
        for nested_list in nested_lists:
            # 递归处理嵌套列表
            nested_items = process_list_items(nested_list, depth + 1)
            result.extend(nested_items)
    
    return result

def convert_ai_message_to_md(content):
    """
    将AI消息的HTML内容转换为Markdown格式，保持格式化
    """
    soup = BeautifulSoup(content, 'html.parser')
    md_lines = []
    
    # 首先尝试找到消息的主体内容
    main_content = soup.find('div', class_='grid-cols-1')
    if not main_content:
        main_content = soup
        
    def should_process_element(elem):
        if not elem.name:
            return False
        # 跳过图片相关元素
        if elem.find('img') or elem.get('data-testid', '').startswith('image'):
            return False
        # 跳过按钮和相关UI元素
        if elem.name == 'div' and elem.get('class'):
            skip_classes = ['font-styrene', 'relative', 'absolute', '-bottom-0', 'flex items-center']
            return not any(cls in elem.get('class', []) for cls in skip_classes)
        return elem.name in ['p', 'pre', 'ol', 'ul', 'div', 'table', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote']
    
    # 获取需要处理的元素
    elements = []
    for elem in main_content.children:
        if should_process_element(elem):
            if elem.name == 'div':
                # 检查div是否为代码块容器
                if not elem.find('pre') and not elem.find('code'):
                    continue
            elements.append(elem)
    
    last_was_code = False
    current_list_number = 1
    
    for i, element in enumerate(elements):
        if element.name == 'pre':
            text = extract_code_block(element)
            if not text.startswith('```'):
                # 这是普通文本
                if last_was_code:
                    md_lines.append('')
                md_lines.append(text)
            else:
                # 这是代码块
                if md_lines and md_lines[-1].strip():
                    md_lines.append('')
                md_lines.append(text)
                last_was_code = True
                continue
        
        elif element.name == 'p':
            text = process_inline_code(element)
            if text:
                if last_was_code:
                    md_lines.append('')
                md_lines.append(f"{text}\n")
            last_was_code = False
            
        elif element.name in ['ol', 'ul']:
            if last_was_code:
                md_lines.append('')
            if md_lines and md_lines[-1].strip():
                md_lines.append("")
            
            # 如果前一个元素不是列表,重置编号    
            if i > 0 and elements[i-1].name not in ['ol', 'ul']:
                current_list_number = 1
                
            start_number = element.get('start')
            if start_number:
                current_list_number = int(start_number)
            
            list_items = process_list_items(element, depth=0, start_number=current_list_number)
            md_lines.extend(list_items)
            
            if element.name == 'ol':
                current_list_number += len(element.find_all('li', recursive=False))
            
            if i < len(elements) - 1 and elements[i + 1].name not in ['ol', 'ul']:
                md_lines.append("")
            last_was_code = False
            
        elif element.name == 'table':
            if last_was_code:
                md_lines.append('')
            md_lines.append(process_table(element))
            last_was_code = False
            
        elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(element.name[1]) + 2  # 增加2级
            if level <= 6:  # 确保不超过6级标题
                md_lines.append(f"\n{'#' * level} {element.get_text().strip()}\n")
            else:
                # 如果超过6级，使用6级标题
                md_lines.append(f"\n###### {element.get_text().strip()}\n")
                
        elif element.name == 'blockquote':
            md_lines.append(f'> {process_inline_code(element.find("p"))}\n')
    
    # 清理多余空行
    result = []
    prev_line = ""
    for line in md_lines:
        if line.strip() or (prev_line.strip() and not line.strip()):
            result.append(line)
        prev_line = line
        
    # 移除最后的空行
    while result and not result[-1].strip():
        result.pop()
        
    return "\n".join(result)

def convert_html_to_md(html_content):
    """
    将HTML格式的聊天记录转换为Markdown格式
    """
    # 对话标识模式
    user_start = r'</div></div><div data-testid="user-message"'
    user_end = r'<div class="absolute -bottom-0 -right-1.5"'
    ai_start = r'<div class="grid-cols-1 grid gap-2\.5\s*\[&amp;_&gt;_\*\]:min-w-0">'
    
    # 分割对话内容
    conversations = []
    current_pos = 0
    
    while current_pos < len(html_content):
        # 查找下一个用户或AI的发言开始位置
        user_match = re.search(user_start, html_content[current_pos:])
        ai_match = re.search(ai_start, html_content[current_pos:])
        
        # 如果找不到更多的对话了，就结束
        if not user_match and not ai_match:
            break
            
        if not ai_match or (user_match and user_match.start() < ai_match.start()):
            # 处理用户发言
            if user_match:
                start_pos = current_pos + user_match.start()
                content_start = start_pos + len(user_start)
                
                # 找到用户发言的结束位置（下一个AI发言开始或用户发言结束标记）
                next_ai = re.search(ai_start, html_content[content_start:])
                end_mark = re.search(user_end, html_content[content_start:])
                
                if end_mark and (not next_ai or end_mark.start() < next_ai.start()):
                    content_end = content_start + end_mark.start()
                elif next_ai:
                    content_end = content_start + next_ai.start()
                else:
                    content_end = len(html_content)
                
                # 提取用户消息内容
                content = html_content[content_start:content_end]
                # 使用BeautifulSoup提取文本
                soup = BeautifulSoup(content, 'html.parser')
                user_text = ' '.join(p.get_text().strip() for p in soup.find_all('p'))
                if user_text:
                    conversations.append(("user", user_text))
                current_pos = content_end
        else:
            # 处理AI发言
            start_pos = current_pos + ai_match.start()
            content_start = start_pos
            
            # 查找下一个用户发言作为当前AI发言的结束点
            next_user = re.search(user_start, html_content[content_start:])
            if next_user:
                content_end = content_start + next_user.start()
            else:
                content_end = len(html_content)
            
            # 提取内容
            content = html_content[content_start:content_end]
            conversations.append(("ai", content))
            current_pos = content_end
    
    # 转换为Markdown格式
    md_content = []
    for speaker, content in conversations:
        if speaker == "user":
            # 用户消息已经是纯文本了
            md_content.append(f"\n## User\n")
            md_content.append(content)
        else:
            # AI消息需要保持格式
            md_content.append(f"\n## AI\n")
            md_content.append(convert_ai_message_to_md(content))
    
    return "\n".join(md_content)

def main():
    # 检查命令行参数
    if len(sys.argv) != 2:
        print("Usage: python script.py input.html")
        print("Example: python script.py chat.html")
        sys.exit(1)
    
    # 获取输入文件路径
    input_file = sys.argv[1]
    
    # 检查文件是否以.html结尾
    if not input_file.lower().endswith('.html'):
        print("Error: Input file must be an HTML file (.html)")
        sys.exit(1)
    
    # 生成输出文件名（替换.html为.md）
    output_file = input_file[:-5] + '.md'  # 去掉.html后加上.md
    
    try:
        # 读取HTML文件
        with open(input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 转换内容
        md_content = convert_html_to_md(html_content)
        
        # 写入Markdown文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
            
        print(f"Successfully converted {input_file} to {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()