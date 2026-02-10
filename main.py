import asyncio
from feed import get_new_feed_items
from notion import add_feed_item_to_notion
from parser import html_to_notion_blocks
from feishu import send_feed_summary_to_feishu


async def main():
    """Main entry point for the Notion Feeder application."""
    feed_items = get_new_feed_items()
    print(feed_items)

    if feed_items:
        send_feed_summary_to_feishu(feed_items)

    for item in feed_items:
        notion_item = {
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "content": html_to_notion_blocks(item.get("content", ""))
        }
        add_feed_item_to_notion(notion_item)


if __name__ == "__main__":
    asyncio.run(main())