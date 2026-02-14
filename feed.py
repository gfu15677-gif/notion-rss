import feedparser
import os
import time
import requests
from dotenv import load_dotenv
from helpers import time_difference

load_dotenv()

RUN_FREQUENCY = int(os.getenv("RUN_FREQUENCY", "3600"))  # 单位：秒（默认1小时）

# ===== 扩展的 RSS 源列表 =====
# 你可以随时在这里添加或删除链接，一行一个
RSS_URLS = [
    # 1. Google News 多关键词搜索（中英文、公司名、通用术语）
    "https://news.google.com/rss/search?q=exoskeleton+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+Ekso+OR+ReWalk+OR+Sarcos+OR+Cyberdyne+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC%E6%9C%BA%E5%99%A8%E4%BA%BA&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",

    # 2. arXiv 机器人学最新论文（包含大量外骨骼研究）
    "http://export.arxiv.org/rss/cs.RO",

    # 3. Ekso Bionics 官方新闻（公司官网 RSS）
    "https://eksobionics.com/feed/",

    # 4. ReWalk 官方博客（如果存在，通常官网有 /feed）
    "https://rewalk.com/feed/",

    # 5. 科技新闻聚合（TechCrunch 外骨骼相关）
    "https://techcrunch.com/tag/exoskeleton/feed/",

    # 6. The Verge 外骨骼标签
    "https://www.theverge.com/tech/rss/index.xml",  # 整个科技版，可能过滤，但可以再加一个专用标签
    # 更精准的 The Verge 搜索 RSS（需要 Google News 已经涵盖，暂不重复）

    # 7. 学术期刊：IEEE Xplore 机器人学期刊 RSS（可能需要订阅，这里用 Google Scholar 替代）
    # 可用 Google Scholar 的 RSS（但需要特定关键词），我们直接使用 Google News 已覆盖

    # 8. 行业新闻网站：Robotics & Automation News
    "https://roboticsandautomationnews.com/category/exoskeletons/feed/",

    # 9. 公司：Sarcos Robotics 新闻
    "https://www.sarcos.com/category/news/feed/",

    # 10. 公司：Cyberdyne 新闻（如果提供 RSS，未找到公开，可暂时用 Google News 覆盖）
]

# 如果你想添加更多源，只需在 RSS_URLS 列表里追加一行，格式如上面所示
# ============================

def _parse_struct_time_to_timestamp(st):
    if st:
        return time.mktime(st)
    return 0

def send_feishu_message(text):
    webhook_url = os.getenv("FEISHU_WEBHOOK")
    if not webhook_url:
        print("❌ 环境变量 FEISHU_WEBHOOK 未设置")
        return
    payload = {
        "msg_type": "text",
        "content": {"text": text}
    }
    try:
        resp = requests.post(webhook_url, json=payload)
        if resp.status_code == 200:
            print("✅ 飞书消息发送成功")
        else:
            print(f"❌ 飞书消息发送失败: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ 飞书请求异常: {e}")

def get_new_feed_items_from(feed_url):
    print(f"正在抓取 RSS: {feed_url}")
    try:
        rss = feedparser.parse(feed_url)
        print(f"RSS 解析成功，条目总数: {len(rss.entries)}")
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

    print(f"本次抓取到 {len(new_items)} 条新文章")
    return new_items

def get_new_feed_items():
    all_new_feed_items = []
    for feed_url in RSS_URLS:
        feed_items = get_new_feed_items_from(feed_url)
        all_new_feed_items.extend(feed_items)

    all_new_feed_items.sort(
        key=lambda x: _parse_struct_time_to_timestamp(x.get("published_parsed"))
    )
    print(f"总共 {len(all_new_feed_items)} 条新文章待推送")

    return all_new_feed_items
