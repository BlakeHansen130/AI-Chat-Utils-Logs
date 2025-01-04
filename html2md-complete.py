from bs4 import BeautifulSoup
import re
import sys
import os

class ChatHTML2Markdown:
    def __init__(self, html_content):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.markdown = []
        self.current_heading_level = 0

    def get_all_messages(self):
        """获取所有消息并按顺序排列"""
        messages = []
    
        # 打印找到的所有消息节点
        user_messages = self.soup.find_all('div', attrs={'data-testid': 'user-message'})
        print(f"Found {len(user_messages)} user messages")
    
        ai_messages = self.soup.find_all('div', class_='font-claude-message')
        print(f"Found {len(ai_messages)} AI messages")
    
        # 查找所有消息容器并按顺序排列
        all_containers = self.soup.find_all(['div'], attrs={
            'class': lambda x: x and 'font-claude-message' in str(x),
            'data-testid': lambda x: x == 'user-message'
        })
    
        for container in all_containers:
            if container.get('data-testid') == 'user-message':
                content = container.find('p', class_='whitespace-pre-wrap')
                print(f"User message content: {content.get_text() if content else 'None'}")
                messages.append(('User', container))
            else:
                content = container.find('p', class_='whitespace-pre-wrap')
                print(f"AI message content: {content.get_text() if content else 'None'}")
                messages.append(('Assistant', container))
                
        return messages

    def process_text_content(self, element):
        """处理普通文本内容，保持换行和空格"""
        if isinstance(element, str):
            return element.replace('\n', '  \n')
        elif element.name == 'p' and 'whitespace-pre-wrap' in element.get('class', []):
            return element.get_text().replace('\n', '  \n')
        return None

    def process_code(self, element):
        """处理代码块和行内代码"""
        # 跳过按钮展开式代码块
        if element.find('button', attrs={'class': lambda x: x and 'border-0.5' in x}):
            return None
            
        # 处理行内代码
        if element.name == 'code' and 'bg-text-200/5' in element.get('class', []):
            return f'`{element.get_text()}`'
            
        # 处理代码段
        if element.name == 'div' and 'code-block' in element.get('class', []):
            lang = element.find('div', class_='text-text-300')
            code_text = element.find('div', class_='leading-relaxed').get_text()
            lang_name = lang.get_text() if lang else ''
            return f'\n```{lang_name}\n{code_text}\n```\n'
            
        return None

    def process_latex(self, element):
        """处理LaTeX公式"""
        if 'math-inline' in element.get('class', []):
            return f'$${element.find("span", class_="katex").get_text()}$$'
        elif 'math-display' in element.get('class', []):
            return f'\n$$\n{element.find("span", class_="katex").get_text()}\n$$\n'
        return None

    def process_lists(self, element):
        """处理列表"""
        if element.name not in ['ol', 'ul']:
            return None

        markdown_lines = []
        list_type = element.name
        depth = int(element.get('depth', '0'))
        indent = '    ' * depth

        for li in element.find_all('li', recursive=False):
            index = li.get('index', '')
            content = li.get_text(strip=True)
            
            # 有序列表保持原始序号
            if list_type == 'ol':
                markdown_lines.append(f'{indent}{index}. {content}')
            else:
                markdown_lines.append(f'{indent}* {content}')

            # 处理嵌套列表
            nested_list = li.find(['ol', 'ul'])
            if nested_list:
                nested_content = self.process_lists(nested_list)
                if nested_content:
                    markdown_lines.extend(nested_content.split('\n'))

        return '\n'.join(markdown_lines)

    def process_table(self, element):
        """处理表格"""
        if not element.name == 'table':
            return None

        markdown_lines = []
        
        # 处理表头
        headers = []
        separators = []
        for th in element.find_all('th'):
            header_text = th.get_text(strip=True)
            headers.append(header_text)
            separators.append('-' * len(header_text))

        markdown_lines.append('| ' + ' | '.join(headers) + ' |')
        markdown_lines.append('| ' + ' | '.join(separators) + ' |')

        # 处理表格内容
        for tr in element.find_all('tr')[1:]:  # 跳过表头行
            row = []
            for td in tr.find_all('td'):
                cell_text = td.get_text(strip=True)
                row.append(cell_text)
            markdown_lines.append('| ' + ' | '.join(row) + ' |')

        return '\n'.join(markdown_lines)

    def process_message_content(self, message):
        """处理消息内容，返回处理后的文本"""
        content_parts = []
        
        for element in message.descendants:
            # 跳过已处理的元素
            if getattr(element, '_processed', False):
                continue
                
            # 跳过空白内容
            if isinstance(element, str) and element.strip() == '':
                continue

            # 跳过按钮展开式代码块
            if element.name == 'button' and 'border-0.5' in element.get('class', []):
                parent = element.find_parent('div', class_='py-2')
                if parent:
                    parent._processed = True
                continue

            # 处理特殊内容
            for processor in [
                self.process_code,
                self.process_latex,
                self.process_lists,
                self.process_table
            ]:
                result = processor(element)
                if result is not None:
                    content_parts.append(result)
                    if element.parent:
                        element.parent._processed = True
                    break
            else:
                # 处理普通文本
                if element.name == 'p' and 'whitespace-pre-wrap' in element.get('class', []):
                    text_content = element.get_text().strip()
                    if text_content:
                        content_parts.append(text_content)
                    element._processed = True

        return '\n'.join(part for part in content_parts if part.strip())

    def convert(self):
        """完整的转换流程"""
        messages = self.get_all_messages()
        
        for role, message in messages:
            self.markdown.append(f'\n## {role}:\n')
            content = self.process_message_content(message)
            if content:
                self.markdown.append(content + '\n')

        return '\n'.join(self.markdown).strip()

def convert_html_to_markdown(html_content):
    """转换HTML到Markdown的入口函数"""
    converter = ChatHTML2Markdown(html_content)
    return converter.convert()

def main():
    # 检查命令行参数
    if len(sys.argv) != 2:
        print("Usage: python script.py input.html")
        sys.exit(1)

    input_file = sys.argv[1]
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)
    
    # 生成输出文件名
    output_file = os.path.splitext(input_file)[0] + '.md'
    
    try:
        # 读取HTML文件
        with open(input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 转换为Markdown
        markdown_content = convert_html_to_markdown(html_content)
        
        # 写入Markdown文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        print(f"Conversion successful! Output saved to: {output_file}")
        
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()