from playwright.sync_api import sync_playwright

from src.detail.taobao_mapping import parse_sku_mapping
from src.detail.taobao_price import parse_price_response
from src.detail.taobao_merge import merge_sku_price

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


def get_taobao_sku_prices(page, url):

    price_result = []

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

    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=30000
    )

    page.wait_for_timeout(
        5000
    )



    # ==========================
    # SKU规格映射
    # ==========================

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


    print(
        "SKU Mapping:"
    )

    print(
        sku_mapping
    )

    # ==========================
    # 自动触发skuClick
    # ==========================

    click_first_available_sku(page)


    page.wait_for_timeout(
        3000
    )

    # ==========================
    # 等待价格接口
    # ==========================

    page.wait_for_timeout(
        3000
    )



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