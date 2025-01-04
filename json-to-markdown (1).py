#!/usr/bin/env python3
import json
import sys
import re
from pathlib import Path

def adjust_header_levels(text, increase_by=2):
    """Increase markdown header levels by specified amount"""
    def replace_header(match):
        return '#' * (len(match.group(1)) + increase_by) + match.group(2)
    
    # Find lines starting with one or more #
    return re.sub(r'^(#+)(.*?)$', replace_header, text, flags=re.MULTILINE)

def extract_message_parts(message):
    if not message or not message.get('message'):
        return None
    
    content = message['message'].get('content', {})
    if not content:
        return None
    
    # Handle multimodal content
    if content.get('content_type') == 'multimodal_text':
        parts = []
        for part in content.get('parts', []):
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                # Skip image parts as we can't render them
                continue
        return ' '.join(parts)
    
    # Handle regular text content
    return ' '.join(content.get('parts', []))

def build_conversation_tree(mapping, node_id, indent=0):
    if node_id not in mapping:
        return []
    
    node = mapping[node_id]
    message_content = extract_message_parts(node)
    conversation = []
    
    if message_content:
        role = node['message']['author']['role']
        # Add role as second level header
        prefix = '## Human\n\n' if role == 'user' else '## Assistant\n\n'
        # Adjust existing headers in the content
        message_content = adjust_header_levels(message_content)
        conversation.append(f"{prefix}{message_content}")
    
    for child_id in node.get('children', []):
        conversation.extend(build_conversation_tree(mapping, child_id, indent + 1))
    
    return conversation

def convert_json_to_markdown(json_path):
    # Read JSON file
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get the document title and clean it
    title = data.get('title', Path(json_path).stem)
    
    # Get the root node ID
    mapping = data['mapping']
    root_id = next(node_id for node_id, node in mapping.items() if node.get('parent') is None)
    
    # Build conversation
    conversation = build_conversation_tree(mapping, root_id)
    
    # Create markdown content with title
    markdown_content = f"# {title}\n\n" + '\n\n'.join(conversation)
    
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
