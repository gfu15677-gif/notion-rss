from markdownify import markdownify as turndown


def html_to_markdown(html_content):
    """Convert HTML content to Markdown."""
    try:
        return turndown(html_content)
    except Exception as e:
        print(f"Error converting HTML to Markdown: {e}")
        return ""


def markdown_to_notion_blocks(markdown_content):
    """Convert Markdown content to Notion blocks."""
    blocks = []
    lines = markdown_content.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("# "):
            blocks.append({
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                }
            })
        elif line.startswith("## "):
            blocks.append({
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                }
            })
        elif line.startswith("### "):
            blocks.append({
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                }
            })
        elif line.startswith("- "):
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                }
            })
        elif line.startswith("1. "):
            blocks.append({
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                }
            })
        elif line.startswith("**") and line.endswith("**"):
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": line[2:-2]},
                        "annotations": {"bold": True}
                    }]
                }
            })
        elif line.startswith("*") and line.endswith("*"):
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": line[1:-1]},
                        "annotations": {"italic": True}
                    }]
                }
            })
        elif line.startswith("`") and line.endswith("`"):
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": line[1:-1]},
                        "annotations": {"code": True}
                    }]
                }
            })
        elif line.startswith("[") and "](" in line:
            # Link: [text](url)
            text_part = line[1:line.index("](")]
            url_part = line[line.index("](")+2:line.index(")")]
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": text_part, "link": {"url": url_part}}
                    }]
                }
            })
        elif line.startswith("http://") or line.startswith("https://"):
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line, "link": {"url": line}}}]
                }
            })
        else:
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line}}]
                }
            })

    return blocks


def html_to_notion_blocks(html_content):
    """Convert HTML content to Notion blocks."""
    markdown_json = html_to_markdown(html_content)
    return markdown_to_notion_blocks(markdown_json)
