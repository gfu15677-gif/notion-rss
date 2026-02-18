import feedparser
import os
import time
import requests
from dotenv import load_dotenv
from helpers import time_difference

load_dotenv()

RUN_FREQUENCY = int(os.getenv("RUN_FREQUENCY", "3600"))

# ===== 外骨骼 RSS 源（按相关性排序，技术研发优先）=====
RSS_URLS = [
    # 1. 国外专业机器人媒体（核心信源）
    "https://www.therobotreport.com/feed/",
    "https://roboticsandautomationnews.com/feed/",
    "https://www.roboticsbusinessreview.com/feed/",
    "https://techcrunch.com/tag/exoskeleton/feed/",
    "https://spectrum.ieee.org/feeds/robotics.rss",               # IEEE Spectrum 机器人

    # 2. 学术论文预印本（前沿研究）
    "http://export.arxiv.org/rss/cs.RO",                           # arXiv 机器人学

    # 3. 公司官方研发动态（部分可能无 RSS，保留已验证的）
    "https://eksobionics.com/feed/",
    "https://rewalk.com/feed/",
    "https://www.sarcos.com/feed/",

    # 4. Google News 精准关键词搜索（聚焦技术研发）
    "https://news.google.com/rss/search?q=%E5%A4%96%E9%AA%A8%E9%AA%BC+%E6%8A%80%E6%9C%AF+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E7%A0%94%E5%8F%91+OR+AI%E6%84%8F%E5%9B%BE%E8%AF%86%E5%88%AB+%E5%A4%96%E9%AA%A8%E9%AA%BC+OR+%E6%AD%A5%E6%80%81%E9%A2%84%E6%B5%8B+%E5%A4%96%E9%AA%A8%E9%AA%BC+OR+%E4%BA%BA%E6%9C%BA%E5%8D%8F%E5%90%8C+%E5%A4%96%E9%AA%A8%E9%AA%BC+OR+%E8%87%AA%E9%80%82%E5%BA%94%E6%8E%A7%E5%88%B6+%E5%A4%96%E9%AA%A8%E9%AA%BC+OR+%E8%BF%90%E5%8A%A8%E6%84%8F%E5%9B%BE+%E5%A4%96%E9%AA%A8%E9%AA%BC+OR+%E8%BD%BB%E9%87%8F%E5%8C%96%E7%94%B5%E6%9C%BA+%E5%A4%96%E9%AA%A8%E9%AA%BC+OR+smart+exoskeleton+OR+exoskeleton+intent+recognition&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",

    # 5. 国内科技媒体（放在后面，减少杂音）
    "https://36kr.com/feed",
    "https://www.huxiu.com/rss/",
    "https://rss.sina.com.cn/tech/rollnews.xml",
    "https://rss.qq.com/tech/rollnews.xml",
    "https://www.thepaper.cn/rss/news.xml",

    # 6. RSSHub 社交媒体源（可选，公共实例可能无效，保留但不影响）
    "https://rsshub.app/wechat/search/外骨骼",
    "https://rsshub.app/weibo/search/外骨骼",
    "https://rsshub.app/bilibili/vsearch/外骨骼",
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
    print(f"总共 {len(all_new_feed_items)} 条新文章待推送（去重前）")

    # 去重逻辑：基于链接（忽略大小写和空格）
    unique_items_dict = {}
    for item in all_new_feed_items:
        link_key = item['link'].strip().lower()
        if link_key not in unique_items_dict:
            unique_items_dict[link_key] = item

    unique_items = list(unique_items_dict.values())
    print(f"总共 {len(unique_items)} 条新文章待推送（去重后）")

    for item in unique_items:
        text = f"{item['title']}\n{item['link']}"
        send_feishu_message(text)

    return unique_items
