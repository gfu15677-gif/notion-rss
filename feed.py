import feedparser
import os
import time
import requests
from dotenv import load_dotenv
from helpers import time_difference

load_dotenv()

RUN_FREQUENCY = int(os.getenv("RUN_FREQUENCY", "3600"))

# ===== 必须包含的关键词（不区分大小写）=====
# 只有标题或内容中出现以下任意一个词的才推送
REQUIRED_KEYWORDS = [
    "外骨骼",
    "exoskeleton",
    "机器人",
    "robotics",
    "步态",
    "gait",
    "助力",
    "assist",
    "意图识别",
    "intent recognition",
    "人机协同",
    "human-robot",
    "自适应控制",
    "adaptive control",
    "轻量化",
    "lightweight",
    "电机",
    "motor",
    "康复",
    "rehabilitation",
    "负重",
    "load-bearing",
    "髋关节",
    "hip",
    "膝关节",
    "knee",
]

# ===== RSS 源列表 =====
RSS_URLS = [
    # 国外专业机器人媒体（最可靠）
    "https://www.therobotreport.com/feed/",
    "https://roboticsandautomationnews.com/feed/",
    "https://www.roboticsbusinessreview.com/feed/",
    "https://techcrunch.com/tag/exoskeleton/feed/",
    "https://spectrum.ieee.org/feeds/robotics.rss",

    # 学术论文
    "http://export.arxiv.org/rss/cs.RO",

    # 公司官方
    "https://eksobionics.com/feed/",
    "https://rewalk.com/feed/",
    "https://www.sarcos.com/feed/",

    # Google News 精准搜索（包含技术关键词）
    "https://news.google.com/rss/search?q=%E5%A4%96%E9%AA%A8%E9%AA%BC+%E6%8A%80%E6%9C%AF+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E7%A0%94%E5%8F%91+OR+AI%E6%84%8F%E5%9B%BE%E8%AF%86%E5%88%AB+%E5%A4%96%E9%AA%A8%E9%AA%BC+OR+%E6%AD%A5%E6%80%81%E9%A2%84%E6%B5%8B+%E5%A4%96%E9%AA%A8%E9%AA%BC+OR+%E4%BA%BA%E6%9C%BA%E5%8D%8F%E5%90%8C+%E5%A4%96%E9%AA%A8%E9%AA%BC+OR+%E8%87%AA%E9%80%82%E5%BA%94%E6%8E%A7%E5%88%B6+%E5%A4%96%E9%AA%A8%E9%AA%BC+OR+%E8%BF%90%E5%8A%A8%E6%84%8F%E5%9B%BE+%E5%A4%96%E9%AA%A8%E9%AA%BC+OR+%E8%BD%BB%E9%87%8F%E5%8C%96%E7%94%B5%E6%9C%BA+%E5%A4%96%E9%AA%A8%E9%AA%BC+OR+smart+exoskeleton+OR+exoskeleton+intent+recognition&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",

    # 国内科技媒体（噪音源，必须配合关键词过滤）
    "https://36kr.com/feed",
    "https://www.huxiu.com/rss/",
    "https://rss.sina.com.cn/tech/rollnews.xml",
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

def contains_keyword(text):
    """检查文本是否包含任一必需关键词（不区分大小写）"""
    if not text:
        return False
    text_lower = text.lower()
    for kw in REQUIRED_KEYWORDS:
        if kw.lower() in text_lower:
            return True
    return False

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
        if not pub_date:
            continue

        blog_published_time = _parse_struct_time_to_timestamp(pub_date)
        diff = time_difference(current_time, blog_published_time)
        if diff["diffInSeconds"] >= RUN_FREQUENCY:
            continue

        title = item.get("title", "")
        content = item.get("summary", "")  # 有的源用summary

        # 关键词过滤：只有标题或内容包含所需关键词才保留
        if not (contains_keyword(title) or contains_keyword(content)):
            continue

        new_items.append({
            "title": title,
            "link": item.get("link", ""),
            "content": content,
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

    # 去重
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
