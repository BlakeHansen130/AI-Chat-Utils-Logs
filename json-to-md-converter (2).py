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

def process_citations(text, citations):
    """Process citations in text"""
    if not citations:
        return text
    
    for citation in citations:
        if 'metadata' in citation and citation['metadata']:
            meta = citation['metadata']
            if 'url' in meta and 'title' in meta:
                # Create markdown link
                link = f"[{meta['title']}]({meta['url']})"
                # Get ref_index safely
                ref_id = citation.get('ref_id', {})
                ref_index = ref_id.get('ref_index', '\\d+') if isinstance(ref_id, dict) else '\\d+'
                # Create pattern without f-string
                pattern = r'citeturn\d+search' + str(ref_index) + r'\b'
                text = re.sub(pattern, link, text)
    
    return text

def extract_message_parts(message):
    """Extract message content while filtering out system messages"""
    if not message or not message.get('message'):
        return None
    
    # Skip system messages
    author = message.get('message', {}).get('author', {})
    author_name = author.get('name')
    if author_name and isinstance(author_name, str) and (
        author_name.startswith('canmore.') or
        author_name.startswith('dalle.') or
        author_name == 'web'
    ):
        return None
    
    content = message['message'].get('content', {})
    if not content:
        return None
    
    # Skip DALL-E related messages
    parts = content.get('parts', [])
    if not parts:
        return None
    
    if isinstance(parts[0], str) and "DALL-E displayed" in parts[0]:
        return None
    
    # Join parts into text
    text = ' '.join(str(part) for part in parts if part is not None)
    
    # Process citations if available
    citations = message.get('metadata', {}).get('citations', [])
    if citations:
        text = process_citations(text, citations)
    
    return text

def build_conversation_tree(mapping, node_id, indent=0):
    if node_id not in mapping:
        return []
    
    node = mapping[node_id]
    conversation = []
    
    message_content = extract_message_parts(node)
    if message_content:
        role = node['message']['author']['role']
        if role in ['user', 'assistant']:
            prefix = '## Human\n\n' if role == 'user' else '## Assistant\n\n'
            message_content = adjust_header_levels(message_content)
            conversation.append(f"{prefix}{message_content}")
    
    for child_id in node.get('children', []):
        conversation.extend(build_conversation_tree(mapping, child_id, indent + 1))
    
    return conversation

def convert_json_to_markdown(json_path):
    # Read JSON file
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get the document title
    title = data.get('title', Path(json_path).stem)
    
    # Get the root node ID
    mapping = data['mapping']
    root_id = next(node_id for node_id, node in mapping.items() if node.get('parent') is None)
    
    # Build conversation
    conversation = build_conversation_tree(mapping, root_id)
    
    # Create markdown content
    markdown_content = f"# {title}\n\n"
    markdown_content += '\n\n'.join(conversation)
    
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