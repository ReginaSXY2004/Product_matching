from playwright.sync_api import sync_playwright

from src.detail.taobao_mapping import parse_sku_mapping
from src.detail.taobao_price import (
    parse_price_response,
    parse_price_from_html
)
from src.detail.taobao_merge import merge_sku_price
from src.taobao_login import (
    _create_context,
    _page_is_logged_in,
    _wait_for_login,
    _save_login_state_if_ready
)
from urllib.parse import urlparse, parse_qs

from pathlib import Path


def create_taobao_page(storage_path):

    p = sync_playwright().start()

    browser, context = _create_context(
        p,
        storage_path
    )

    page = context.new_page()

    # ===== 登录检查 =====

    page.goto(
        "https://www.taobao.com",
        wait_until="domcontentloaded"
    )

    page.wait_for_timeout(5000)

    if not _page_is_logged_in(page):

        print("淘宝登录失效，请扫码")

        page.goto(
            "https://login.taobao.com/member/login.jhtml"
        )

        if _wait_for_login(page):

            _save_login_state_if_ready(
                page,
                storage_path,
                "detail login"
            )

    return p, browser, page


def click_first_available_sku(page):
    sku_items = page.locator(
        "[class*='valueItem--']"
    )

    count = sku_items.count()

    print(
        "SKU按钮数量:",
        count
    )

    for i in range(count):
        item = sku_items.nth(i)

        disabled = item.get_attribute(
            "data-disabled"
        )

        cls = item.get_attribute(
            "class"
        )

        print(
            i,
            disabled,
            cls
        )

        # 跳过不可用
        if disabled == "true":
            continue

        # 跳过当前已经选中的
        if cls and "isSelected" in cls:
            continue

        item.click()

        print(
            "点击SKU:",
            i
        )
        return True

    return False


def clean_taobao_url(url):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    item_id = params.get("id")

    if item_id:
        return (
            "https://item.taobao.com/item.htm?id="
            + item_id[0]
        )

    return url


def get_taobao_sku_prices(page, url):
    price_result = []
    sku_mapping = {}

    # ==========================
    # 响应监听器（仅在 HTML 未命中时启用）
    # ==========================
    def handle_response(response):
        try:
            urlr = response.url
        except Exception:
            return

        try:
            if ("mtop" in urlr) or ("pcdetail" in urlr) or ("price" in urlr) or ("adjust" in urlr):
                try:
                    print("[RESP]", response.status, urlr)
                except Exception:
                    print("[RESP]", urlr)
        except Exception:
            pass

        if "mtop.taobao.pcdetail.data.adjust" not in urlr:
            return

        try:
            text = response.text()
            prices = parse_price_response(text)
            price_result.extend(prices)
            print(f"[PRICE] parsed {len(prices)} items from response")
        except Exception as e:
            print("response解析失败:", e)

    # ==========================
    # 打开页面并等待初始化
    # ==========================
    url = clean_taobao_url(url)
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)

    # ==========================
    # 优先从 HTML 解析价格
    # ==========================
    content = page.content()
    print("sku2info:", "sku2info" in content)
    print("price:", '"price"' in content)

    price_result = parse_price_from_html(content)
    print("HTML parser result:", price_result[:3])
    if price_result:
        print(f"HTML 解析到 {len(price_result)} 个价格条目，跳过接口点击")
        sku_mapping = parse_sku_mapping(content)
        result = merge_sku_price(price_result, sku_mapping)
        return result
    else:
        with open(
            "data/debug_responses/html_failed.html",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(content)        

    # ==========================
    # HTML 未命中，启动接口监听等待自然触发
    # ==========================
    page.on("response", handle_response)
    print("HTML 未命中价格，开始监听 mtop.taobao.pcdetail.data.adjust 接口")

    for _ in range(30):
        if price_result:
            break
        page.wait_for_timeout(500)

    content = page.content()
    sku_mapping = parse_sku_mapping(content)

    if price_result:
        print("接口已获取到价格，返回结果")
        result = merge_sku_price(price_result, sku_mapping)
        try:
            page.remove_listener("response", handle_response)
        except Exception:
            try:
                page.off("response", handle_response)
            except Exception:
                pass
        return result

    # ==========================
    # HTML 和接口都失败，点击一次可用 SKU 作为最后兜底
    # ==========================
    print("HTML 和接口都未获取到价格，尝试点击第一个可用 SKU")
    clicked = click_first_available_sku(page)
    print("click_first_available_sku 结果:", clicked)

    if clicked:
        for _ in range(20):
            if price_result:
                break
            page.wait_for_timeout(500)

    if not price_result:
        print("单次 SKU 点击后仍未获取到价格，停止继续点击")
        content = page.content()
        fallback_prices = parse_price_from_html(content)
        if fallback_prices:
            print(f"点击后 HTML 解析到 {len(fallback_prices)} 个价格条目")
            price_result = fallback_prices

    print(f"debug: total raw price entries collected: {len(price_result)}")
    unique_price = {}
    for item in price_result:
        unique_price[item["sku_id"]] = item
    price_result = list(unique_price.values())
    result = merge_sku_price(price_result, sku_mapping)

    try:
        page.remove_listener("response", handle_response)
    except Exception:
        try:
            page.off("response", handle_response)
        except Exception:
            pass

    return result
