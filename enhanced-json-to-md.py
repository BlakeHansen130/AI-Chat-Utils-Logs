#!/usr/bin/env python3
import json
import sys
import re
from pathlib import Path

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
            # Create a markdown link with the title as hover text
            link = f"[{title}]({url})"
            text = text[:start] + link + text[end:]
    
    return text

def extract_message_parts(message):
    """Extract message content while filtering out canvas-related and DALL-E messages"""
    if not message or not message.get('message'):
        return None
    
    # Check author name safely
    author = message.get('message', {}).get('author', {})
    author_name = author.get('name')
    if author_name and isinstance(author_name, str) and (
        author_name.startswith('canmore.') or 
        author_name.startswith('dalle.')
    ):
        return None
    
    content = message['message'].get('content', {})
    if not content:
        return None
        
    # Skip DALL-E related messages
    parts = content.get('parts', [])
    if parts and isinstance(parts[0], str) and "DALL-E displayed" in parts[0]:
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
        text = ' '.join(parts)
    else:
        parts = content.get('parts', [])
        if not parts:
            return None
        text = ' '.join(str(part) for part in parts if part is not None)
    
    # If no text was extracted, return None
    if not text:
        return None
    
    # Process citations if present in metadata
    metadata = message.get('message', {}).get('metadata', {})
    citations = metadata.get('citations', [])
    content_references = metadata.get('content_references', [])
    
    text = process_citations(text, citations, content_references)
    
    # Filter out canvas-related JSON content
    if text.strip().startswith('{') and text.strip().endswith('}'):
        try:
            json_content = json.loads(text)
            if any(key in json_content for key in ['name', 'type', 'content', 'updates']):
                return None
        except json.JSONDecodeError:
            pass
    
    return text

def is_canvas_related(node):
    """Check if a node is related to canvas operations"""
    if not node or not node.get('message'):
        return False
    
    # Check author name safely    
    author = node.get('message', {}).get('author', {})
    author_name = author.get('name')
    if author_name and isinstance(author_name, str) and author_name.startswith('canmore.'):
        return True
    
    # Check message content safely
    content = node.get('message', {}).get('content', {})
    parts = content.get('parts', [])
    if not parts:
        return False
    
    text = ' '.join(str(part) for part in parts if part is not None)
    if not text:
        return False
    
    # Check for canvas operation content
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
        message_content = extract_message_parts(node)
        if message_content:
            role = node.get('message', {}).get('author', {}).get('role')
            if role in ['user', 'assistant']:  # Only include user and assistant messages
                prefix = '## Human\n\n' if role == 'user' else '## Assistant\n\n'
                message_content = adjust_header_levels(message_content)
                conversation.append(f"{prefix}{message_content}")
    
    for child_id in node.get('children', []):
        conversation.extend(build_conversation_tree(mapping, child_id, indent + 1))
    
    return conversation

def adjust_header_levels(text, increase_by=2):
    """Increase markdown header levels by specified amount"""
    def replace_header(match):
        return '#' * (len(match.group(1)) + increase_by) + match.group(2)
    
    # Find lines starting with one or more #
    return re.sub(r'^(#+)(.*?)$', replace_header, text, flags=re.MULTILINE)

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
    
    # Remove empty lines between sections
    markdown_content = f"# {title}\n\n"
    
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
