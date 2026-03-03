import feedparser
import os
import time
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, urlunparse
from dotenv import load_dotenv
from helpers import time_difference

load_dotenv()

RUN_FREQUENCY = int(os.getenv("RUN_FREQUENCY", "3600"))

# ===== 外骨骼专用 RSS 源（已整合更多国内公司、社交媒体和研究报告）=====
RSS_URLS = [
    # ========== 1. Google News 深度报告搜索（覆盖更多关键词） ==========
    "https://news.google.com/rss/search?q=%E5%A4%96%E9%AA%A8%E9%AA%BC+%E6%B7%B1%E5%BA%A6%E6%8A%A5%E5%91%8A+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E8%A1%8C%E4%B8%9A%E7%A0%94%E7%A9%B6+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E4%BA%A7%E4%B8%9A%E9%93%BE+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E6%8A%95%E8%B5%84%E4%BB%B7%E5%80%BC+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E5%B8%82%E5%9C%BA%E6%A0%BC%E5%B1%80+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E6%8A%80%E6%9C%AF%E7%AA%81%E7%A0%B4+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E8%9E%8D%E8%B5%84&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",

    # ========== 2. 国内公司微信公众号 RSSHub 搜索（涵盖更多企业） ==========
    # 你已知的
    "https://rsshub.app/wechat/search/程天科技",
    "https://rsshub.app/wechat/search/傲鲨智能",
    "https://rsshub.app/wechat/search/傅利叶智能",
    "https://rsshub.app/wechat/search/大艾机器人",
    "https://rsshub.app/wechat/search/迈宝智能",

    # 新增国内公司（通过微信公众号搜索公司名）
    "https://rsshub.app/wechat/search/无锡福芯机器人",
    "https://rsshub.app/wechat/search/长沙优龙机器人",
    "https://rsshub.app/wechat/search/极壳",
    "https://rsshub.app/wechat/search/Hypershell",
    "https://rsshub.app/wechat/search/动思",
    "https://rsshub.app/wechat/search/DNSYS",
    "https://rsshub.app/wechat/search/森越成行",
    "https://rsshub.app/wechat/search/Synrise%20Technology",
    "https://rsshub.app/wechat/search/雷赛智能",
    "https://rsshub.app/wechat/search/步科股份",
    "https://rsshub.app/wechat/search/柯力传感",
    "https://rsshub.app/wechat/search/安培龙",
    "https://rsshub.app/wechat/search/华依科技",
    "https://rsshub.app/wechat/search/振江股份",
    "https://rsshub.app/wechat/search/精工科技",
    "https://rsshub.app/wechat/search/卧龙电驱",
    "https://rsshub.app/wechat/search/光大同创",

    # ========== 3. 社交媒体 RSSHub 关键词搜索（抖音、B站、微博） ==========
    "https://rsshub.app/douyin/search/外骨骼",
    "https://rsshub.app/bilibili/vsearch/外骨骼",
    "https://rsshub.app/weibo/search/外骨骼",

    # ========== 4. 学术论文 ==========
    "http://export.arxiv.org/rss/cs.RO",

    # ========== 5. 公司官方博客（已确认有外骨骼业务） ==========
    "https://eksobionics.com/feed/",
    "https://rewalk.com/feed/",
    "https://www.sarcos.com/feed/",

    # ========== 6. 国内科技媒体（仍可能产生少量杂音，但关键词过滤会处理） ==========
    "https://36kr.com/feed",
    "https://www.jiqizhixin.com/rss",
]

def _parse_struct_time_to_timestamp(st):
    if st:
        return time.mktime(st)
    return 0

def normalize_url(url):
    """标准化URL：去除常见追踪参数，并统一为小写"""
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'fbclid', 'gclid']
        filtered_params = {k: v for k, v in query_params.items() if k not in tracking_params}
        new_query = '&'.join([f"{k}={v[0]}" for k, v in filtered_params.items()])
        new_parsed = parsed._replace(query=new_query)
        return urlunparse(new_parsed).rstrip('/').lower()
    except:
        return url.rstrip('/').lower()

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

def should_keep_article(title, content):
    """必须包含外骨骼相关关键词，且不含黑名单词"""
    if not title and not content:
        return False

    text = (title + " " + content).lower()

    # 强相关词（必须有至少一个）
    strong_keywords = [
        "外骨骼", "exoskeleton", "程天科技", "傲鲨智能", "傅利叶", "大艾",
        "迈宝智能", "肯綮科技", "智元研究院", "康复机器人", "助力机器人",
        "髋关节", "膝关节", "步态", "人机协同", "意图识别", "轻量化",
        "ekso", "rewalk", "sarcos", "cyberdyne", "hal", "bionics",
        "无锡福芯", "优龙机器人", "极壳", "hypershell", "动思", "dnsys",
        "森越成行", "synrise", "雷赛", "步科", "柯力", "安培龙", "华依",
        "振江股份", "精工科技", "卧龙电驱", "光大同创"
    ]
    if not any(kw in text for kw in strong_keywords):
        return False

    # 黑名单词（出现则丢弃）
    blacklist = [
        "手机", "汽车", "锂矿", "锂电", "小红书", "电商", "抖音", "快手",
        "微信", "支付宝", "外卖", "打车", "共享单车", "游戏", "影视",
        "股票", "基金", "理财", "房价", "地产", "消费", "零售", "演唱会"
    ]
    if any(bw in text for bw in blacklist):
        return False

    return True

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

        if not should_keep_article(title, content):
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
    # 加载已推送链接缓存（保存7天，避免跨周期重复）
    cache_file = "/tmp/pushed_links_cache.json"
    pushed_links = set()
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                data = json.load(f)
                cutoff_time = datetime.now() - timedelta(days=7)
                for link, timestamp_str in data.items():
                    try:
                        if datetime.fromisoformat(timestamp_str) > cutoff_time:
                            pushed_links.add(link)
                    except:
                        pass
    except Exception as e:
        print(f"⚠️ 读取推送缓存失败: {e}")

    # 抓取所有源的新文章
    all_new_feed_items = []
    for feed_url in RSS_URLS:
        feed_items = get_new_feed_items_from(feed_url)
        all_new_feed_items.extend(feed_items)

    print(f"总共 {len(all_new_feed_items)} 条新文章待处理（抓取总数）")

    # 单次运行内去重（基于标准化链接）
    unique_items_dict = {}
    for item in all_new_feed_items:
        normalized_link = normalize_url(item['link'])
        if normalized_link not in unique_items_dict:
            unique_items_dict[normalized_link] = item

    print(f"单次运行内去重后剩余 {len(unique_items_dict)} 条")

    # 跨周期去重：过滤掉缓存中已有的链接
    truly_new_items = []
    for item in unique_items_dict.values():
        normalized_link = normalize_url(item['link'])
        if normalized_link not in pushed_links:
            truly_new_items.append(item)

    print(f"跨周期去重后剩余 {len(truly_new_items)} 条新文章待推送")

    # 推送并更新缓存
    for item in truly_new_items:
        text = f"{item['title']}\n{item['link']}"
        send_feishu_message(text)
        pushed_links.add(normalize_url(item['link']))

    # 保存更新后的缓存
    try:
        data_to_save = {link: datetime.now().isoformat() for link in pushed_links}
        with open(cache_file, 'w') as f:
            json.dump(data_to_save, f)
    except Exception as e:
        print(f"⚠️ 保存推送缓存失败: {e}")

    return truly_new_items
