import sys
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
        elif isinstance(content, str):
            result.append(content)
        else:
            result.append(str(content.string) if content.string else '')
    return ''.join(result)

def extract_code_block(element):
    """
    从pre标签中提取代码块内容并转换为markdown格式
    """
    # 首先尝试查找 text-text-300 类的div来获取语言
    lang_div = element.find('div', class_='text-text-300')
    
    # 如果找不到，尝试其他可能包含语言信息的元素
    if not lang_div:
        # 查找所有 div，检查text content
        all_divs = element.find_all('div')
        for div in all_divs:
            text_content = div.get_text().strip().lower()
            if text_content in ['python', 'bash', 'javascript', 'html', 'css', 'java', 'cpp', 'c++', 'c']:
                lang_div = div
                break
    
    language = lang_div.get_text().strip() if lang_div else ''
    
    # 查找代码内容
    code_div = element.find('div', class_='code-block__code')
    if not code_div:
        # 如果找不到特定class的div，尝试找到code标签
        code_element = element.find('code')
        if code_element:
            code_div = code_element.parent
    
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
    
    # 按markdown代码块格式返回
    return f"```{language}\n{code_content}\n```\n"

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
    current_list_number = 1  # 跟踪当前有序列表的编号
    
    # 首先尝试找到消息的主体内容
    main_content = soup.find('div', class_='grid-cols-1')
    if not main_content:
        main_content = soup  # 如果找不到特定的div，就用整个内容
        
    # 查找所有顶级内容元素，忽略图片和按钮
    def should_process_element(elem):
        # 跳过图片相关元素
        if elem.find('img') or elem.get('data-testid', '').startswith('image'):
            return False
        # 跳过按钮和相关UI元素
        if elem.name == 'div' and elem.get('class'):
            skip_classes = ['font-styrene', 'relative', 'absolute', '-bottom-0']
            return not any(cls in elem.get('class', []) for cls in skip_classes)
        return elem.name in ['p', 'pre', 'ol', 'ul', 'div']
    
    elements = [elem for elem in main_content.children 
               if elem.name and should_process_element(elem)]
    
    i = 0
    while i < len(elements):
        element = elements[i]
        
        if element.name == 'pre':
            # 处理代码块，确保它和前后的文本正确分隔
            if md_lines and not md_lines[-1].isspace() and md_lines[-1].strip():
                md_lines.append('')
            
            md_lines.append(extract_code_block(element))
            
            # 在代码块后添加空行（如果不是列表的一部分）
            if i + 1 < len(elements) and elements[i + 1].name not in ['ol', 'ul']:
                md_lines.append('')
            
        elif element.name == 'p':
            # 普通段落文本处理
            text = process_inline_code(element)
            if text:  # 只添加非空段落
                # 如果前一个是代码块，确保有空行分隔
                if md_lines and md_lines[-1].startswith('```'):
                    md_lines.append('')
                md_lines.append(f"{text}\n")
            
        elif element.name in ['ol', 'ul']:
            # 列表处理，添加适当的空行
            if md_lines and md_lines[-1].strip():
                md_lines.append("")
            
            # 检查是否需要继续之前的编号
            start_number = element.get('start')
            if start_number:
                current_list_number = int(start_number)
            
            # 处理列表项
            list_items = process_list_items(element, depth=0, start_number=current_list_number)
            md_lines.extend(list_items)
            
            # 更新列表编号
            if element.name == 'ol':
                current_list_number += len(element.find_all('li', recursive=False))
            
            # 列表后添加空行
            if i + 1 < len(elements):
                md_lines.append("")
        
        i += 1
    
    # 清理多余空行
    result = []
    for i in range(len(md_lines)):
        line = md_lines[i]
        # 避免连续的空行
        if line.strip() == "" and (i > 0 and md_lines[i-1].strip() == ""):
            continue
        # 确保代码块前后只有一个空行
        if (line.strip().startswith("```") and i > 0 and md_lines[i-1].strip() == "") or \
           (line.strip() == "" and i > 0 and md_lines[i-1].strip().startswith("```")):
            result.append(line)
        # 保留其他内容
        elif line.strip() or (i > 0 and i < len(md_lines) - 1):
            result.append(line)
    
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