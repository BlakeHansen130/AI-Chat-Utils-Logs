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
        else:
            result.append(str(content.string) if content.string else '')
    return ''.join(result)

def extract_code_block(element):
    """
    从pre标签中提取代码块内容并转换为markdown格式
    """
    # 查找代码语言标识
    lang_div = element.find('div', class_='text-text-300')
    language = lang_div.get_text().strip() if lang_div else ''
    
    # 查找代码内容
    code_div = element.find('div', class_='code-block__code')
    if not code_div:
        return ''
        
    # 提取纯代码文本(移除所有HTML标签和样式)
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

def convert_ai_message_to_md(content):
    """
    将AI消息的HTML内容转换为Markdown格式，保持格式化
    """
    soup = BeautifulSoup(content, 'html.parser')
    md_lines = []
    
    # 首先尝试找到消息的主体内容
    main_content = soup.find('div', class_='grid-cols-1')
    if not main_content:
        main_content = soup  # 如果找不到特定的div，就用整个内容
        
    # 查找所有内容元素
    for element in main_content.find_all(['p', 'pre', 'ol', 'ul']):
        if element.name == 'pre':
            # 处理代码块
            md_lines.append(extract_code_block(element))
            
        elif element.name == 'p':
            # 普通段落文本
            text = element.get_text().strip()
            if text:  # 只添加非空段落
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
                text = process_inline_code(item)
                md_lines.append(f"* {text}")
            md_lines.append("")  # 列表后加空行
    
    # 移除多余的空行
    while len(md_lines) > 1 and not md_lines[0].strip():
        md_lines.pop(0)
    while len(md_lines) > 1 and not md_lines[-1].strip():
        md_lines.pop()
        
    return "\n".join(md_lines)

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