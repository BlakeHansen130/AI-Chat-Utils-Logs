import json
import sys
import re
from pathlib import Path
from datetime import datetime, timezone

def format_timestamp(timestamp):
    """将 Unix 时间戳转换为可读格式"""
    if timestamp:
        try:
            dt = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except ValueError:
            return "Invalid Timestamp"
    return "Unknown Time"

def get_model_info(message):
    """从消息元数据中提取模型信息"""
    if not message or 'metadata' not in message:
        return None
    
    metadata = message['metadata']
    model_slug = metadata.get('model_slug')
    default_model_slug = metadata.get('default_model_slug')
    
    # 仅当模型信息与默认模型不同的时候返回模型信息
    if model_slug and default_model_slug and model_slug != default_model_slug:
        return f" [使用模型: {model_slug}]"
    return ""  # 返回空字符串而不是 None

def generate_footnotes(text, content_references):
    """使用内容引用生成脚注"""
    footnotes = []
    footnote_index = 1
    updated_text = text

    # 处理内容引用以生成脚注
    for ref in content_references:
        if ref.get('type') == 'webpage' and 'url' in ref:
            url = ref.get('url')
            title = ref.get('title', url)
            if url:
                # 在文本中添加脚注引用
                updated_text += f" [^{footnote_index}]"
                # 添加实际的脚注
                footnotes.append(f"[^{footnote_index}]: [{title}]({url})")
                footnote_index += 1

    return footnotes, updated_text

def extract_message_parts(messages):
    """
    提取消息内容，处理 Markdown 的改进版。
    """
    conversation = []
    for message in messages:
        if is_canvas_related(message):
            # 跳过 Canvas 相关内容
            continue

        # 正常提取非 Canvas 相关的对话内容
        author = message.get('author', {}).get('name', 'Unknown')
        content = message.get('content', '无内容')
        timestamp = format_timestamp(message.get('create_time'))

        conversation.append(f"{author} ({timestamp}):\n{content}\n\n")

    return ''.join(conversation)

def is_canvas_related(node):
    """
    判断某个节点是否与 Canvas 相关的改进版本。
    增强逻辑以覆盖所有可能包含 Canvas 信息的字段。
    """
    if isinstance(node, dict):
        # 检查是否有 Canvas 相关字段
        if 'canmore.' in node.get('type', ''):
            return True
        if 'exclusive_key' in node and 'canvas' in node['exclusive_key']:
            return True
        if 'content' in node and 'canvas' in node.get('name', '').lower():
            return True
        # 检查更新字段中的特定内容
        if 'updates' in node:
            for update in node['updates']:
                if 'pattern' in update and 'canvas' in update.get('replacement', ''):
                    return True
    return False

def build_conversation_tree(mapping, node_id):
    """
    构建对话树，递归处理节点，确保过滤掉 Canvas 相关内容。
    """
    conversation_tree = []

    # 获取当前节点
    node = mapping.get(node_id)

    if not node or is_canvas_related(node):
        # 如果节点为空或者与 Canvas 相关，跳过该节点
        return conversation_tree

    # 提取当前节点的基本信息
    author = node.get("author", {}).get("name", "Unknown")
    content = node.get("content", "无内容")
    timestamp = format_timestamp(node.get("create_time"))

    # 添加当前节点到对话树
    conversation_tree.append(f"{author} ({timestamp}):\n{content}\n")

    # 递归处理子节点
    children = node.get("children", [])
    for child_id in children:
        conversation_tree.extend(build_conversation_tree(mapping, child_id))

    return conversation_tree

def get_default_model(data):
    """获取默认模型的信息"""
    if 'default_model' in data:
        return data['default_model']
    return "Unknown Model"  # 如果没有找到默认模型则返回默认的说明

def remove_citeturn_and_navlist_markers(data):
    """移除特定的标记和文本"""
    if isinstance(data, str):
        data = re.sub(r'(citeturn|turn)0(news|search)\d+', '', data)
        data = re.sub(r'^video.*?《.*?》MV\s*', '', data, flags=re.MULTILINE)
        data = re.sub(r'navlist.*?(?=\n|$)', '', data)
        data = re.sub(r'\n\s*\n', '\n\n', data)
        return data.strip()
    else:
        return data

def convert_json_to_markdown(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data_str = f.read()
        data_str = re.sub(r'[\uE000-\uF8FF]', '', data_str)
        data = json.loads(data_str)

    data = remove_citeturn_and_navlist_markers(data)

    title = data.get('title', Path(json_path).stem)
    default_model = get_default_model(data)

    mapping = data['mapping']
    root_id = next(node_id for node_id, node in mapping.items() if node.get('parent') is None)

    conversation = build_conversation_tree(mapping, root_id)

    markdown_content = f"# {title}-{default_model}\n\n"
    conversation_text = '\n\n'.join(conversation)
    markdown_content += re.sub(r'\n{3,}', '\n\n', conversation_text)

    output_path = json_path.with_suffix('.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"Markdown 文件已创建：{output_path}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <json_file>")
        sys.exit(1)
    
    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"错误：文件 {json_path} 不存在")
        sys.exit(1)
    
    try:
        convert_json_to_markdown(json_path)
    except Exception as e:
        print(f"处理文件时出错：{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
