import feedparser
import os
import time
import requests
from dotenv import load_dotenv
from helpers import time_difference

load_dotenv()

RUN_FREQUENCY = int(os.getenv("RUN_FREQUENCY", "3600"))

# ===== 外骨骼 RSS 源（覆盖新闻+微信+抖音+B站+微博）=====
RSS_URLS = [
    # 1. Google News 多关键词搜索（基础）
    "https://news.google.com/rss/search?q=exoskeleton+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+Ekso+OR+ReWalk+OR+Sarcos+OR+Cyberdyne+OR+%E8%BF%88%E5%AE%9D%E6%99%BA%E8%83%BD+OR+%E8%A7%86%E6%BA%90%E8%82%A1%E4%BB%BD+OR+%E5%82%85%E5%88%A9%E5%8F%B6&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",

    # 2. 行业垂直媒体
    "https://www.therobotreport.com/feed/",
    "https://roboticsandautomationnews.com/feed/",
    "https://www.roboticsbusinessreview.com/feed/",

    # 3. 公司官方博客
    "https://eksobionics.com/feed/",
    "https://rewalk.com/feed/",
    "https://www.sarcos.com/feed/",

    # 4. 国内科技媒体
    "https://36kr.com/feed",
    "https://www.huxiu.com/rss/",
    "https://rss.sina.com.cn/tech/rollnews.xml",

    # 5. 学术论文
    "http://export.arxiv.org/rss/cs.RO",

    # 6. 国外科技媒体
    "https://techcrunch.com/tag/exoskeleton/feed/",

    # 7. RSSHub 生成的社交媒体搜索（覆盖微信、抖音、B站、微博）
    "https://rsshub.app/wechat/search/外骨骼",
    "https://rsshub.app/douyin/search/外骨骼",
    "https://rsshub.app/bilibili/vsearch/外骨骼",
    "https://rsshub.app/weibo/search/外骨骼",
]

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
