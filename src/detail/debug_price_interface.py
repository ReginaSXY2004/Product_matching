import time
import re
from urllib.parse import urlparse, parse_qs
from pathlib import Path

from src.detail.taobao_sku import (
    create_taobao_page,
    clean_taobao_url,
    click_first_available_sku,
)
from src.config import STORAGE_STATE_PATH


def sanitize_filename(text):
    return re.sub(r"[^0-9A-Za-z_.-]", "_", text)[:120]


def save_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def debug_price_interface(url):
    p, browser, page = create_taobao_page(STORAGE_STATE_PATH)

    url = clean_taobao_url(url)
    parsed = urlparse(url)
    item_id = parse_qs(parsed.query).get("id", ["unknown"])[0]
    base_dir = Path(__file__).resolve().parents[2] / "data" / "debug_responses" / item_id
    base_dir.mkdir(parents=True, exist_ok=True)

    seen_adjust = []
    all_responses = []

    def handle_response(response):
        try:
            urlr = response.url
        except Exception:
            return

        if ("mtop" in urlr) or ("pcdetail" in urlr) or ("price" in urlr) or ("sku" in urlr):
            try:
                body = response.text()
            except Exception as e:
                body = f"<failed to read response body: {e}>"

            file_name = sanitize_filename(urlr)
            file_path = base_dir / f"resp_{len(all_responses)+1}_{file_name}.txt"
            save_text(file_path, f"URL: {urlr}\n\n{body}")

            print("[RESP]", response.status, urlr)
            all_responses.append(urlr)

        if "mtop.taobao.pcdetail.data.adjust" in urlr:
            seen_adjust.append(urlr)
            print("[FOUND ADJUST]", urlr)

    page.on("response", handle_response)

    print("打开页面:", url)
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    print("等待 15 秒，观察初始加载接口...")
    time.sleep(15)

    html = page.content()
    save_text(base_dir / "page_content.html", html)

    sku2info_match = re.search(r'"sku2info":(\{.*?\})(?:,|\})', html, re.S)
    print("sku2info in HTML:", bool(sku2info_match))
    if sku2info_match:
        save_text(base_dir / "sku2info_snippet.txt", sku2info_match.group(0))
        print("sku2info snippet saved")

    try:
        from src.detail.taobao_price import parse_price_from_html
        html_price = parse_price_from_html(html)
        print("parse_price_from_html found", len(html_price), "prices")
        if html_price:
            save_text(base_dir / "html_price.txt", str(html_price))
    except Exception as e:
        print("parse_price_from_html error:", e)

    if not seen_adjust:
        print("初始加载未发现 pcdetail.data.adjust，尝试点击第一个可选 SKU")
        clicked = click_first_available_sku(page)
        print("是否点击成功:", clicked)
        print("继续等待 15 秒...")
        time.sleep(15)

        html = page.content()
        save_text(base_dir / "page_content_after_click.html", html)

    print("--- 诊断结果 ---")
    print("item_id:", item_id)
    print("matched_adjust:", len(seen_adjust))
    print("saved_responses:", len(all_responses))
    print("page_content saved to:", base_dir / "page_content.html")
    if not seen_adjust:
        print("page_content_after_click saved to:", base_dir / "page_content_after_click.html")

    browser.close()
    p.stop()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("用法: python -m src.detail.debug_price_interface <item_url>")
        sys.exit(1)

    debug_price_interface(sys.argv[1])
