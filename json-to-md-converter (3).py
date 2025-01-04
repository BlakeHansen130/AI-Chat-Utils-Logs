import json
import sys
import re
from pathlib import Path
from datetime import datetime, timezone

def format_timestamp(timestamp):
    """Convert Unix timestamp to human readable format"""
    if timestamp:
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    return None

def get_model_info(message):
    """Extract model information from message metadata"""
    if not message or 'metadata' not in message:
        return None
    
    metadata = message['metadata']
    model_slug = metadata.get('model_slug')
    default_model_slug = metadata.get('default_model_slug')
    
    # Only return model info if it's different from the default
    if model_slug and default_model_slug and model_slug != default_model_slug:
        return f" [使用模型: {model_slug}]"
    return ""  # Return empty string instead of None

def process_citations(text, citations, content_references):
    """Process citations and content references to add markdown links"""
    if not citations or not content_references:
        return text
    
    # Create a map of citation markers to their URLs and titles
    citation_map = {}
    for ref in content_references:
        if ref.get('type') == 'webpage' or 'url' in ref:
            start_idx = ref.get('start_idx')
            end_idx = ref.get('end_idx')
            url = ref.get('url')
            title = ref.get('title', url)
            if start_idx is not None and end_idx is not None and url:
                citation_map[(start_idx, end_idx)] = (url, title)

    # Sort citations by start index in reverse order to avoid offset issues
    citations_sorted = sorted(citation_map.items(), key=lambda x: x[0][0], reverse=True)
    
    # Replace citations with markdown links
    for (start, end), (url, title) in citations_sorted:
        if start < len(text) and end <= len(text):
            link = f"[{title}]({url})"
            text = text[:start] + link + text[end:]
    
    return text

def extract_message_parts(message):
    """Extract message content while filtering out canvas-related and DALL-E messages"""
    if not message or not message.get('message'):
        return None, None
    
    msg = message['message']
    timestamp = format_timestamp(msg.get('create_time'))
    
    # Check author name safely
    author = msg.get('author', {})
    author_name = author.get('name')
    if author_name and isinstance(author_name, str) and (
        author_name.startswith('canmore.') or 
        author_name.startswith('dalle.')
    ):
        return None, None
    
    content = msg.get('content', {})
    if not content:
        return None, None
        
    # Skip DALL-E related messages
    parts = content.get('parts', [])
    if parts and isinstance(parts[0], str) and "DALL-E displayed" in parts[0]:
        return None, None
    
    # Handle multimodal content
    if content.get('content_type') == 'multimodal_text':
        parts = []
        for part in content.get('parts', []):
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                # Skip image parts as we can't render them
                continue
        text = ' '.join(parts)
    else:
        parts = content.get('parts', [])
        if not parts:
            return None, None
        text = ' '.join(str(part) for part in parts if part is not None)
    
    # If no text was extracted, return None
    if not text:
        return None, None
    
    # Process citations if present in metadata
    metadata = msg.get('metadata', {})
    citations = metadata.get('citations', [])
    content_references = metadata.get('content_references', [])
    
    text = process_citations(text, citations, content_references)
    
    return text, timestamp

def is_canvas_related(node):
    """Check if a node is related to canvas operations"""
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
    
    # Skip canvas-related nodes
    if not is_canvas_related(node):
        message_content, timestamp = extract_message_parts(node)
        if message_content:
            role = node.get('message', {}).get('author', {}).get('role')
            if role in ['user', 'assistant']:
                model_info = get_model_info(node.get('message', {}))
                timestamp_info = f"\n\n*{timestamp}*" if timestamp else ""
                prefix = (f"## Human{timestamp_info}\n\n" if role == 'user' else 
                         f"## Assistant{model_info}{timestamp_info}\n\n")
                message_content = adjust_header_levels(message_content)
                conversation.append(f"{prefix}{message_content}")
    
    for child_id in node.get('children', []):
        conversation.extend(build_conversation_tree(mapping, child_id, indent + 1))
    
    return conversation

def adjust_header_levels(text, increase_by=2):
    """Increase markdown header levels by specified amount"""
    def replace_header(match):
        return '#' * (len(match.group(1)) + increase_by) + match.group(2)
    
    return re.sub(r'^(#+)(.*?)$', replace_header, text, flags=re.MULTILINE)

def get_default_model(data):
    """Get the default model from the data"""
    if not data or 'mapping' not in data:
        return None
    
    # Try to find first assistant message to get default model
    for node in data['mapping'].values():
        if not node.get('message'):
            continue
        msg = node['message']
        if msg.get('author', {}).get('role') == 'assistant':
            metadata = msg.get('metadata', {})
            return metadata.get('default_model_slug')
    
    return 'unknown'  # Fallback value if no default model found

def convert_json_to_markdown(json_path):
    # Read JSON file
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get the document title and clean it
    title = data.get('title', Path(json_path).stem)
    default_model = get_default_model(data)
    
    # Get the root node ID
    mapping = data['mapping']
    root_id = next(node_id for node_id, node in mapping.items() if node.get('parent') is None)
    
    # Build conversation
    conversation = build_conversation_tree(mapping, root_id)
    
    # Remove empty lines between sections
    markdown_content = f"# {title}-{default_model}\n\n"
    
    # Join conversation parts and clean up multiple newlines
    conversation_text = '\n\n'.join(conversation)
    # Replace three or more newlines with two newlines
    markdown_content += re.sub(r'\n{3,}', '\n\n', conversation_text)
    
    # Write markdown file
    output_path = json_path.with_suffix('.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"Markdown file created: {output_path}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <json_file>")
        sys.exit(1)
    
    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"Error: File {json_path} does not exist")
        sys.exit(1)
    
    try:
        convert_json_to_markdown(json_path)
    except Exception as e:
        print(f"Error processing file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()