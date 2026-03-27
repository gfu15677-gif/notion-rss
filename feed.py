import feedparser
import os
import time
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, urlunparse
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from helpers import time_difference

load_dotenv()

RUN_FREQUENCY = int(os.getenv("RUN_FREQUENCY", "3600"))
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# ===== 外骨骼 RSS 源（保持不变）=====
RSS_URLS = [
    "https://news.google.com/rss/search?q=%E5%A4%96%E9%AA%A8%E9%AA%BC+%E6%B7%B1%E5%BA%A6%E6%8A%A5%E5%91%8A+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E8%A1%8C%E4%B8%9A%E7%A0%94%E7%A9%B6+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E4%BA%A7%E4%B8%9A%E9%93%BE+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E6%8A%95%E8%B5%84%E4%BB%B7%E5%80%BC+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E5%B8%82%E5%9C%BA%E6%A0%BC%E5%B1%80+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E6%8A%80%E6%9C%AF%E7%AA%81%E7%A0%B4+OR+%E5%A4%96%E9%AA%A8%E9%AA%BC+%E8%9E%8D%E8%B5%84&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    "https://rsshub.app/wechat/search/程天科技",
    "https://rsshub.app/wechat/search/傲鲨智能",
    "https://rsshub.app/wechat/search/傅利叶智能",
    "https://rsshub.app/wechat/search/大艾机器人",
    "https://rsshub.app/wechat/search/迈宝智能",
    "http://export.arxiv.org/rss/cs.RO",
    "https://eksobionics.com/feed/",
    "https://rewalk.com/feed/",
    "https://www.sarcos.com/feed/",
    "https://36kr.com/feed",
    "https://www.jiqizhixin.com/rss",
]

def _parse_struct_time_to_timestamp(st):
    if st:
        return time.mktime(st)
    return 0

def normalize_url(url):
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

def fetch_article_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()
        article = soup.find('article') or soup.find('main') or soup.body
        if article:
            text = article.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)
    except Exception as e:
        print(f"抓取失败: {e}")
        return None

def summarize_with_deepseek(text, title):
    """调用 DeepSeek API 生成中文摘要（自动翻译英文内容）"""
    if not DEEPSEEK_API_KEY:
        return "[未配置 DeepSeek API Key，无法生成摘要]"
    if not text:
        return "[文章内容为空]"

    prompt = f"""请为以下文章写一个简短的中文摘要。如果原文是英文，请先翻译成中文再进行总结。

要求：
1. 摘要用中文输出
2. 保留关键信息，突出核心内容
3. 不要超过300字

标题：{title}

正文：{text[:3000]}"""

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个专业的新闻摘要助手，擅长翻译和提炼文章核心内容，输出语言始终为中文。"},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "temperature": 0.3,
        "max_tokens": 500
    }
    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=20
        )
        if resp.status_code == 200:
            result = resp.json()
            summary = result['choices'][0]['message']['content'].strip()
            return summary
        else:
            print(f"DeepSeek API 返回错误: {resp.status_code} - {resp.text}")
            return f"[摘要生成失败: HTTP {resp.status_code}]"
    except Exception as e:
        print(f"DeepSeek API 调用异常: {e}")
        return f"[摘要生成失败: {str(e)}]"

def format_summary(item, summary):
    return f"🔹 **{item['title']}**\n🔗 {item['link']}\n📄 {summary}\n"

def send_feishu_message(text):
    webhook_url = os.getenv("FEISHU_WEBHOOK")
    if not webhook_url:
        print("❌ 环境变量 FEISHU_WEBHOOK 未设置")
        return False
    max_len = 4000
    chunks = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    for chunk in chunks:
        payload = {"msg_type": "text", "content": {"text": chunk}}
        try:
            resp = requests.post(webhook_url, json=payload)
            if resp.status_code == 200:
                print("✅ 飞书消息发送成功")
            else:
                print(f"❌ 飞书消息发送失败: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"❌ 飞书请求异常: {e}")
    return True

def should_keep_article(title, content):
    if not title and not content:
        return False
    text = (title + " " + content).lower()
    strong_keywords = [
        "外骨骼", "exoskeleton", "程天科技", "傲鲨智能", "傅利叶", "大艾",
        "迈宝智能", "肯綮科技", "智元研究院", "康复机器人", "助力机器人",
        "髋关节", "膝关节", "步态", "人机协同", "意图识别", "轻量化",
        "ekso", "rewalk", "sarcos", "cyberdyne", "hal", "bionics"
    ]
    if not any(kw in text for kw in strong_keywords):
        return False
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
    cache_file = "/tmp/pushed_links_cache_exo.json"
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

    all_new_feed_items = []
    for feed_url in RSS_URLS:
        feed_items = get_new_feed_items_from(feed_url)
        all_new_feed_items.extend(feed_items)

    print(f"总共 {len(all_new_feed_items)} 条新文章待处理（抓取总数）")

    unique_items_dict = {}
    for item in all_new_feed_items:
        normalized_link = normalize_url(item['link'])
        if normalized_link not in unique_items_dict:
            unique_items_dict[normalized_link] = item
    print(f"单次运行内去重后剩余 {len(unique_items_dict)} 条")

    truly_new_items = []
    for item in unique_items_dict.values():
        normalized_link = normalize_url(item['link'])
        if normalized_link not in pushed_links:
            truly_new_items.append(item)
    print(f"跨周期去重后剩余 {len(truly_new_items)} 条新文章待推送")

    if not truly_new_items:
        print("没有新文章，跳过推送")
        return truly_new_items

    print("开始抓取文章内容并调用AI生成摘要，可能需要一些时间...")
    summary_lines = [f"📅 **外骨骼行业日报 - {datetime.now().strftime('%Y-%m-%d')}**", ""]
    for idx, item in enumerate(truly_new_items, 1):
        print(f"正在处理第 {idx}/{len(truly_new_items)} 篇: {item['title']}")
        full_text = fetch_article_content(item['link'])
        if full_text:
            summary = summarize_with_deepseek(full_text, item['title'])
        else:
            summary = "[无法获取文章内容]"
        summary_lines.append(format_summary(item, summary))
        time.sleep(1)

    final_message = "\n".join(summary_lines)
    send_feishu_message(final_message)

    for item in truly_new_items:
        pushed_links.add(normalize_url(item['link']))
    try:
        data_to_save = {link: datetime.now().isoformat() for link in pushed_links}
        with open(cache_file, 'w') as f:
            json.dump(data_to_save, f)
    except Exception as e:
        print(f"⚠️ 保存推送缓存失败: {e}")

    return truly_new_items
