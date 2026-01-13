import time

import requests


def main() -> int:
    base = "http://127.0.0.1:8000"
    for i in range(10):
        r = requests.get(base + "/api/news", timeout=10)
        items = (r.json() or {}).get("items") or []
        print("try", i, "status", r.status_code, "items", len(items))
        if items:
            print("first", (items[0].get("title") or "")[:120])
            break
        time.sleep(1)

    html = requests.get(base + "/", timeout=10).text
    print("home_has_news_section", 'id="news"' in html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

