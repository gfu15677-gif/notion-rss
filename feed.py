import feedparser
import os
import time
import requests
from dotenv import load_dotenv
from helpers import time_difference

load_dotenv()

RUN_FREQUENCY = int(os.getenv("RUN_FREQUENCY", "3600"))

# ===== 外骨骼 RSS 源（聚焦国内外深度报告）=====
RSS_URLS = [
    # 1. Google News 中文深度报告关键词
    "https://news.google.com/rss/search?q=%E5%A4%96%E9%AA%A8%E9%AA%BC+%E6%B7%B1%E5%BA%A6%E6%8A%A5%E5%91%8A+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E8%A1%8C%E4%B8%9A%E7%A0%94%E7%A9%B6+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E4%BA%A7%E4%B8%9A%E9%93%BE+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E6%8A%95%E8%B5%84%E4%BB%B7%E5%80%BC+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E5%B8%82%E5%9C%BA%E6%A0%BC%E5%B1%80&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",

    # 2. 国内科技媒体深度频道
    "https://36kr.com/feed",
    "https://www.huxiu.com/rss/",
    "https://www.jiqizhixin.com/rss",            # 机器之心
    "https://www.leiphone.com/feed",              # 雷锋网
    "https://www.gg-robot.com/feed",              # 高工机器人
    "https://www.chinaventure.com.cn/rss",        # 投中网

    # 3. 国外专业机器人媒体（保留，但不再是主力）
    "https://www.therobotreport.com/feed/",
    "https://roboticsandautomationnews.com/feed/",
    "https://www.roboticsbusinessreview.com/feed/",
    "https://techcrunch.com/tag/exoskeleton/feed/",
    "https://spectrum.ieee.org/feeds/robotics.rss",

    # 4. 学术论文
    "http://export.arxiv.org/rss/cs.RO",

    # 5. 公司官方（保留）
    "https://eksobionics.com/feed/",
    "https://rewalk.com/feed/",
    "https://www.sarcos.com/feed/",

    # 6. RSSHub 国内社交媒体（尝试抓取公众号文章）
    "https://rsshub.app/wechat/search/外骨骼%20深度报告",
    "https://rsshub.app/wechat/search/程天科技",
    "https://rsshub.app/wechat/search/傲鲨智能",
    "https://rsshub.app/wechat/search/傅利叶智能",
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
    """检查文本是否包含外骨骼相关关键词（不区分大小写）"""
    if not text:
        return False
    text_lower = text.lower()
    keywords = [
        "外骨骼", "exoskeleton", "程天科技", "傲鲨智能", "傅利叶", "大艾",
        "迈宝智能", "肯綮科技", "智元研究院", "康复机器人", "助力机器人",
        "行业报告", "深度报告", "产业链", "投融资", "商业化", "市场格局"
    ]
    for kw in keywords:
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
        content = item.get("summary", "") or item.get("description", "")

        # 关键词过滤：只有标题或内容包含相关关键词才保留
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
