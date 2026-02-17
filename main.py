from feed import get_new_feed_items

def main():
    items = get_new_feed_items()
    print(f"总抓取到 {len(items)} 条新文章")

if __name__ == "__main__":
    main()
