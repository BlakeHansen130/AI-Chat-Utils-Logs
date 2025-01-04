import json
import sys
import re
from pathlib import Path
from datetime import datetime, timezone

def format_timestamp(timestamp):
    """将 Unix 时间戳转换为可读格式"""
    if timestamp:
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    return None

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

def extract_message_parts(message):
    """提取消息内容，同时过滤掉与 canvas 相关和 DALL-E 的消息"""
    if not message or not message.get('message'):
        return None, None, []

    msg = message['message']
    timestamp = format_timestamp(msg.get('create_time'))

    # 安全地检查作者名称
    author = msg.get('author', {})
    author_name = author.get('name')
    if author_name and isinstance(author_name, str) and (
        author_name.startswith('canmore.') or
        author_name.startswith('dalle.')
    ):
        return None, None, []

    content = msg.get('content', {})
    if not content:
        return None, None, []

    # 跳过 DALL-E 相关消息
    parts = content.get('parts', [])
    if parts and isinstance(parts[0], str) and "DALL-E displayed" in parts[0]:
        return None, None, []

    # 处理多模态内容
    text = ' '.join(parts) if parts else ''
    if not text:
        return None, None, []

    # 移除不必要的引用标记（例如 citeturn0newsX）
    cleaned_text = re.sub(r'citeturn0news\d+', '', text)

    # 处理元数据中可能存在的引用
    metadata = msg.get('metadata', {})
    content_references = metadata.get('content_references', [])

    footnotes, updated_text = generate_footnotes(cleaned_text, content_references)
    return updated_text, timestamp, footnotes

def is_canvas_related(node):
    """检查节点是否与 canvas 操作相关"""
    if not node or not node.get('message'):
        return False
    
    author = node.get('message', {}).get('author', {})
    author_name = author.get('name')
    if author_name and isinstance(author_name, str) and author_name.startswith('canmore.'):
        return True
    
    content = node.get('message', {}).get('content', {})
    parts = content.get('parts', [])
    if not parts:
        return False
    
    text = ' '.join(str(part) for part in parts if part is not None)
    if not text:
        return False
    
    if text.strip().startswith('{') and text.strip().endswith('}'):
        try:
            json_content = json.loads(text)
            return any(key in json_content for key in ['name', 'type', 'content', 'updates'])
        except json.JSONDecodeError:
            return False
    
    return False

def build_conversation_tree(mapping, node_id, indent=0):
    if node_id not in mapping:
        return []

    node = mapping[node_id]
    conversation = []

    if not is_canvas_related(node):
        message_content, timestamp, footnotes = extract_message_parts(node)
        if message_content:
            role = node.get('message', {}).get('author', {}).get('role')
            if role in ['user', 'assistant']:
                model_info = get_model_info(node.get('message', {}))
                timestamp_info = f"\n\n*{timestamp}*" if timestamp else ""

                prefix = (f"## Human{timestamp_info}\n\n" if role == 'user' else
                         f"## Assistant{model_info}{timestamp_info}\n\n")
                
                # 添加消息内容
                message_content = adjust_header_levels(message_content)
                conversation.append(prefix + message_content)

                # 将脚注直接添加到消息内容之后
                if footnotes:
                    conversation.append("\n" + "\n".join(footnotes))

    for child_id in node.get('children', []):
        conversation.extend(build_conversation_tree(mapping, child_id, indent + 1))

    return conversation

def adjust_header_levels(text, increase_by=2):
    """按指定数量增加 Markdown 标题级别"""
    def replace_header(match):
        return '#' * (len(match.group(1)) + increase_by) + match.group(2)
    
    return re.sub(r'^(#+)(.*?)$', replace_header, text, flags=re.MULTILINE)

def get_default_model(data):
    """从数据中获取默认模型"""
    if not data or 'mapping' not in data:
        return None
    
    # 尝试找到第一个助手消息来获取默认模型
    for node in data['mapping'].values():
        if not node.get('message'):
            continue
        msg = node['message']
        if msg.get('author', {}).get('role') == 'assistant':
            metadata = msg.get('metadata', {})
            return metadata.get('default_model_slug')
    
    return 'unknown'  # 如果找不到默认模型，则返回未知值

def remove_citeturn_and_navlist_markers(data):
    """递归地移除 'citeturn0newsX'、'citeturn0searchX'、'turn0newsX' 和 'navlist' 标记，同时移除特定的视频预览行"""
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "content" and isinstance(value, dict):
                # 处理 content 字段中的 parts 列表，移除视频预览行
                if "parts" in value and isinstance(value["parts"], list):
                    value["parts"] = [part for part in value["parts"] if "video 袁娅维" not in part]
            data[key] = remove_citeturn_and_navlist_markers(value)
        return data
    elif isinstance(data, list):
        # 递归处理列表中的每一项
        return [remove_citeturn_and_navlist_markers(item) for item in data]
    elif isinstance(data, str):
        # 移除 citeturn 和 turn 标记
        data = re.sub(r'(citeturn|turn)0(news|search)\d+', '', data)
        # 移除视频描述部分的行
        data = re.sub(r'^video.*?《.*?》MV\s*', '', data, flags=re.MULTILINE)
        # 移除整个 navlist 行及其内容
        data = re.sub(r'navlist.*?(?=\n|$)', '', data)
        # 清理可能产生的多余空行
        data = re.sub(r'\n\s*\n', '\n\n', data)

        return data.strip()
    else:
        return data

def convert_json_to_markdown(json_path):
    # 读取 JSON 文件
    with open(json_path, 'r', encoding='utf-8') as f:
        data_str = f.read()
        # 移除 PUA 字符（U+E000 - U+F8FF）
        data_str = re.sub(r'[\uE000-\uF8FF]', '', data_str)
        data = json.loads(data_str)

    # 从解析后的数据中移除 "citeturn0newsX" 和 "navlist" 标记
    data = remove_citeturn_and_navlist_markers(data)

    # 获取文档标题并进行清理
    title = data.get('title', Path(json_path).stem)
    default_model = get_default_model(data)

    # 获取根节点 ID
    mapping = data['mapping']
    root_id = next(node_id for node_id, node in mapping.items() if node.get('parent') is None)

    # 构建对话
    conversation = build_conversation_tree(mapping, root_id)

    # 去除各部分之间的空行
    markdown_content = f"# {title}-{default_model}\n\n"

    # 合并对话部分并清理多余的空行
    conversation_text = '\n\n'.join(conversation)
    # 替换三个或更多的换行符为两个换行符
    markdown_content += re.sub(r'\n{3,}', '\n\n', conversation_text)

    # 写入 Markdown 文件
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
