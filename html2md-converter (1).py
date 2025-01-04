import re
from bs4 import BeautifulSoup
import html

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
                text = item.get_text().strip()
                # 使用实际的序号
                md_lines.append(f"{i}. {text}")
            md_lines.append("")  # 列表后加空行
            
        elif element.name == 'ul':
            # 无序列表，先加一个空行
            md_lines.append("")
            items = element.find_all('li', recursive=False)
            for item in items:
                text = item.get_text().strip()
                md_lines.append(f"* {text}")
            md_lines.append("")  # 列表后加空行
    
    return "\n".join(md_lines)

def convert_html_to_md(html_content):
    """
    将HTML格式的聊天记录转换为Markdown格式
    """
    # 对话标识模式
    user_start = r'<div class="flex shrink-0 items-center justify-center rounded-full font-bold h-7 w-7 text-\[12px \] bg-accent-pro-100 text-oncolor-100">([^<]+)</div></div><div data-testid="user-message"'
    ai_start = r'<div class="grid-cols-1 grid gap-2\.5  \[&amp;_&gt;_\*\]:min-w-0"><p class="whitespace-pre-wrap break-words">'
    ai_end = r'</div></div></div><div class="absolute -bottom-0 -right-1\.5" style="transform: none;">'
    
    # 获取用户名
    username_match = re.search(user_start, html_content)
    if not username_match:
        return "无法识别对话内容：未找到用户发言"
    username = username_match.group(1)
    
    # 分割对话内容
    conversations = []
    current_pos = 0
    
    # 确保第一条消息是用户发言
    first_user = re.search(user_start, html_content)
    first_ai = re.search(ai_start, html_content)
    if not first_user or (first_ai and first_ai.start() < first_user.start()):
        return "对话格式错误：第一条消息不是用户发言"
    
    while current_pos < len(html_content):
        # 查找下一个用户或AI的发言开始位置
        user_match = re.search(user_start, html_content[current_pos:])
        ai_match = re.search(ai_start, html_content[current_pos:])
        
        # 如果找不到更多的对话了，就结束
        if not user_match and not ai_match:
            break
            
        if not ai_match or (user_match and user_match.start() < ai_match.start()):
            # 处理用户发言
            start_pos = current_pos + user_match.start()
            content_start = start_pos + user_match.end()
            # 用户发言到AI发言开始或文件结束
            next_ai = re.search(ai_start, html_content[content_start:])
            if next_ai:
                content_end = content_start + next_ai.start()
            else:
                content_end = len(html_content)
            
            # 提取内容，用户内容保持纯文本处理
            content = html_content[content_start:content_end]
            conversations.append(("user", content))
            current_pos = content_end
            
        else:
            # 处理AI发言
            start_pos = current_pos + ai_match.start()
            content_start = start_pos + ai_match.end()
            # 查找AI发言结束标志
            end_match = re.search(ai_end, html_content[content_start:])
            if end_match:
                content_end = content_start + end_match.start()
            else:
                content_end = len(html_content)
            
            # 提取内容
            content = html_content[content_start:content_end]
            conversations.append(("ai", content))
            current_pos = content_end if not end_match else content_start + end_match.end()
    
    # 转换为Markdown格式
    md_content = []
    for speaker, content in conversations:
        if speaker == "user":
            # 用户消息简单处理
            soup = BeautifulSoup(content, 'html.parser')
            clean_text = soup.get_text().strip()
            md_content.append(f"\n## {username}\n")
            md_content.append(clean_text)
        else:
            # AI消息需要保持格式
            md_content.append(f"\n## AI\n")
            md_content.append(convert_ai_message_to_md(content))
    
    return "\n".join(md_content)

def main():
    # 读取HTML文件
    with open('input.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 转换内容
    md_content = convert_html_to_md(html_content)
    
    # 写入Markdown文件
    with open('output.md', 'w', encoding='utf-8') as f:
        f.write(md_content)

if __name__ == "__main__":
    main()
