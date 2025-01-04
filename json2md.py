import json
import datetime
import sys

def json_to_markdown(json_data):
    # Parse the input JSON data
    data = json.loads(json_data)
    
    # Start building Markdown content
    markdown = []
    
    # Title
    markdown.append(f"# {data.get('name', 'Untitled')}")
    
    # Basic Information
    markdown.append(f"**UUID:** `{data['uuid']}`")
    created_at = data.get('created_at', '')
    updated_at = data.get('updated_at', '')
    if created_at:
        created_date = datetime.datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M:%S')
        markdown.append(f"**创建时间:** `{created_date}`")
    if updated_at:
        updated_date = datetime.datetime.fromisoformat(updated_at).strftime('%Y-%m-%d %H:%M:%S')
        markdown.append(f"**更新时间:** `{updated_date}`")
    markdown.append('')  # New line
    
    # Settings
    markdown.append('## 设置')
    settings = data.get('settings', {})
    for key, value in settings.items():
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        markdown.append(f"- **{key.replace('_', ' ').capitalize()}**: `{value}`")
    markdown.append('')  # New line
    
    # Chat Messages
    markdown.append('## 消息记录')
    chat_messages = data.get('chat_messages', [])
    for i, message in enumerate(chat_messages):
        sender = message.get('sender', 'unknown').capitalize()
        timestamp = message.get('created_at', '')
        message_date = datetime.datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp else ''
        
        # Message header
        markdown.append(f"### 消息 {i + 1}")
        markdown.append(f"**UUID:** `{message['uuid']}`")
        markdown.append(f"**发送者:** `{sender}`")
        markdown.append(f"**创建时间:** `{message_date}`")
        markdown.append('')
        
        # Content of the message
        content = message.get('content', [])
        for part in content:
            if part.get('type') == 'text':
                markdown.append(f"> {part['text']}")
        markdown.append('')  # New line

    # Join everything into a single string and return
    return '\n'.join(markdown)

# Command line usage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_json_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = input_file.rsplit('.', 1)[0] + '.md'
    
    # Read input JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        json_input = f.read()
    
    # Convert JSON to Markdown
    markdown_output = json_to_markdown(json_input)
    
    # Write to output Markdown file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_output)
    
    print(f"Markdown file '{output_file}' generated successfully.")
