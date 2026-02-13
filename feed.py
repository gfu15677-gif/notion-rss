def get_new_feed_items():
    all_new_feed_items = []
    for feed_url in RSS_URLS:
        feed_items = get_new_feed_items_from(feed_url)
        all_new_feed_items.extend(feed_items)

    all_new_feed_items.sort(
        key=lambda x: _parse_struct_time_to_timestamp(x.get("published_parsed"))
    )
    print(f"总共 {len(all_new_feed_items)} 条新文章待推送")

    # ===== 新增：如果没有新文章，就生成一条测试消息，用于验证飞书推送 =====
    if not all_new_feed_items:
        print("⚠️ 没有新文章，生成一条测试消息强制推送")
        all_new_feed_items.append({
            "title": "【测试】外骨骼日报推送验证",
            "link": "https://github.com/你的用户名/notion-rss",
            "content": "这是一条由 GitHub Actions 自动生成的测试消息，用于验证飞书推送是否正常。",
            "published_parsed": time.localtime()  # 当前时间
        })
    # =================================================================

    return all_new_feed_items
