from playwright.sync_api import sync_playwright

from src.detail.taobao_mapping import parse_sku_mapping
from src.detail.taobao_price import parse_price_response
from src.detail.taobao_merge import merge_sku_price
from urllib.parse import urlparse, parse_qs

from pathlib import Path

def create_taobao_page(storage_path):

    p = sync_playwright().start()

    browser = p.chromium.launch(
        headless=False,
        channel="msedge",
        args=[
            "--disable-blink-features=AutomationControlled"
        ]
    )

    context = browser.new_context(
        storage_state=str(storage_path),
        viewport={
            "width":1280,
            "height":900
        }
    )

    page = context.new_page()


    def block_resource(route):
        resource_type = route.request.resource_type

        if resource_type in [
            "image",
            "media",
            "font"
        ]:
            route.abort()
        else:
            route.continue_()


    page.route(
        "**/*",
        block_resource
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
        # 监听价格接口
        # ==========================

    def handle_response(response):
        if (
            "mtop.taobao.pcdetail.data.adjust"
            not in response.url
        ):
            return


        try:
            text = response.text()

            prices = parse_price_response(
                text
            )

            price_result.extend(prices)

        except Exception as e:
            print(
                "response解析失败:",
                e
            )

    page.on(
        "response",
        handle_response
    )


    # ==========================
    # 打开页面
    # ==========================

    url = clean_taobao_url(url)

    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=30000
    )

    # 5秒等待初始价格接口
    for _ in range(10):
        if price_result:
            break
        page.wait_for_timeout(500)


    # ==========================
    # SKU规格映射
    # ==========================
    if len(price_result) > 0:
        content = page.content()

        print(
            "sku2info:",
            "sku2info" in content
        )

        print(
            "price:",
            '"price"' in content
        )

        sku_mapping = parse_sku_mapping(
            content
        )

        print("SKU Mapping:")

        print(sku_mapping)

    # ==========================
    # 若第一个规格不可用，可以自动触发skuClick
    # ==========================

    else:
        print("没有初始价格，尝试点击SKU")

        click_first_available_sku(page)

        for _ in range(5):
            if price_result:
                break
            page.wait_for_timeout(500)
            
        content = page.content()
        sku_mapping = parse_sku_mapping(content)


    # ==========================
    # 去重合并
    # ==========================
    unique_price = {}
    for item in price_result:
        unique_price[item["sku_id"]] = item

    price_result = list(
        unique_price.values()
    )


    result = merge_sku_price(
        price_result,
        sku_mapping
    )


    page.remove_listener(
        "response",
        handle_response
    )


    return result