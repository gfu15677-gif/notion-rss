import feedparser
import os
import time
from dotenv import load_dotenv
from helpers import time_difference

load_dotenv()

RUN_FREQUENCY = int(os.getenv("RUN_FREQUENCY", "86400"))

RSS_URLS = [
    "https://news.google.com/rss/search?q=exoskeleton+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+Ekso+OR+ReWalk+OR+Sarcos&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
]

def _parse_struct_time_to_timestamp(st):
    if st:
        return time.mktime(st)
    return 0

def get_new_feed_items_from(feed_url):
    print(f"正在抓取 RSS: {feed_url}")  # 调试信息
    try:
        rss = feedparser.parse(feed_url)
        print(f"RSS 解析成功，条目总数: {len(rss.entries)}")  # 调试信息
    except Exception as e:
        print(f"Error parsing feed {feed_url}: {e}")
        return []

    current_time_struct = rss.get("updated_parsed") or rss.get("published_parsed")
    current_time = _parse_struct_time_to_timestamp(current_time_struct) if current_time_struct else time.time()

    new_items = []
    for item in rss.entries:
        pub_date = item.get("published_parsed") or item.get("updated_parsed")
        if pub_date:
            blog_published_time = _parse_struct_time_to_timestamp(pub_date)
        else:
            continue

        diff = time_difference(current_time, blog_published_time)
        if diff["diffInSeconds"] < RUN_FREQUENCY:
            new_items.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "content": item.get("content", [{}])[0].get("value", item.get("summary", "")),
                "published_parsed": pub_date
            })

    print(f"本次抓取到 {len(new_items)} 条新文章")  # 调试信息
    return new_items

def get_new_feed_items():
    all_new_feed_items = []
    for feed_url in RSS_URLS:
        feed_items = get_new_feed_items_from(feed_url)
        all_new_feed_items.extend(feed_items)

    all_new_feed_items.sort(
        key=lambda x: _parse_struct_time_to_timestamp(x.get("published_parsed"))
    )
    print(f"总共 {len(all_new_feed_items)} 条新文章待推送")  # 调试信息
    return all_new_feed_items
