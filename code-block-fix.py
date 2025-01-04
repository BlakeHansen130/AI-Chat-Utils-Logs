def extract_code_block(element):
    """
    从pre标签中提取代码块内容并转换为markdown格式
    特别处理"示例输出"类型的代码块
    """
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

def convert_ai_message_to_md(content):
    """
    将AI消息的HTML内容转换为Markdown格式，保持格式化
    """
    soup = BeautifulSoup(content, 'html.parser')
    md_lines = []
    current_list_number = 1
    
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
        return elem.name in ['p', 'pre', 'ol', 'ul', 'div']
    
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