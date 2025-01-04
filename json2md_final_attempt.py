
import json
import datetime
import sys
import re

def json_to_markdown(json_data):
    # Parse the input JSON data
    data = json.loads(json_data)

    # Start building Markdown content
    markdown = []

    # Title
    name = data.get('name', 'Untitled')
    markdown.append(f"# {name}")

    # Basic Information
    uuid = data.get('uuid', 'N/A')
    markdown.append(f"**UUID:** `{uuid}`")

    created_at = data.get('created_at', '')
    updated_at = data.get('updated_at', '')

    if created_at:
        created_date = datetime.datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M:%S')
        markdown.append(f"**Created At:** `{created_date}`")

    if updated_at:
        updated_date = datetime.datetime.fromisoformat(updated_at).strftime('%Y-%m-%d %H:%M:%S')
        markdown.append(f"**Updated At:** `{updated_date}`")

    # Chat Messages
    for message in data.get('chat_messages', []):
        sender = message.get('sender', 'Unknown')
        text_content = []

        for content in message.get('content', []):
            if content.get('type') == 'text':
                text = content.get('text', '')
                # Separate inline and block LaTeX formulas
                processed_text = process_latex(text)
                text_content.append(processed_text)

        # Constructing the message format
        index = message.get('index', 0)
        uuid = message.get('uuid', 'N/A')

        markdown.append(f"### 消息 {index + 1}")
        markdown.append(f"**UUID:** `{uuid}`")
        markdown.append(f"**发送者:** {sender}")

        created_at = message.get('created_at', '')
        if created_at:
            created_date = datetime.datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M:%S')
            markdown.append(f"**创建时间:** `{created_date}`")

        # Adding the actual message content, ensuring proper formatting
        markdown.extend(text_content)

    return "

".join(markdown)

def process_latex(text):
    # This function will distinguish inline and block LaTeX formulas

    # Replace inline LaTeX wrapped in single dollar signs
    text = re.sub(r'\$(.+?)\$', r'\(\)', text)

    # Replace block LaTeX wrapped in double dollar signs or new lines with display math environment
    text = re.sub(r'\$\$(.+?)\$\$', r'\[\]', text, flags=re.DOTALL)

    return text

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python json2md.py <输入文件>")
        sys.exit(1)

    input_file = sys.argv[1]

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            json_data = f.read()
    except FileNotFoundError:
        print(f"错误: 找不到文件 {input_file}")
        sys.exit(1)

    try:
        markdown_content = json_to_markdown(json_data)
    except json.JSONDecodeError:
        print("错误: 输入的JSON格式不正确，请检查输入文件内容")
        sys.exit(1)

    output_file = input_file.rsplit('.', 1)[0] + '.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"已处理完成，输出文件为: {output_file}")
