import json
import re
from playwright.sync_api import sync_playwright


def get_taobao_price(product_url, storage_path):

    result = []

    with sync_playwright() as p:

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


        def handle_response(response):

            if "mtop.taobao.pcdetail.data.adjust" not in response.url:
                return

            try:
                text = response.text()

                # JSONP去括号
                text = re.sub(r'^[^(]*\(', '', text)
                text = re.sub(r'\);?\s*$', '', text)

                data = json.loads(text)


                sku_info = data["data"]["skuCore"]["sku2info"]


                for sku_id, info in sku_info.items():

                    price = info.get("price")
                    sub_price = info.get("subPrice")


                    if price or sub_price:

                        result.append(
                        {
                            "sku_id": sku_id,
                            "优惠前": (
                                price.get("priceText")
                                if price else None
                            ),
                            "补贴后": (
                                sub_price.get("priceText")
                                if sub_price else None
                            )
                        }
                        )


            except Exception as e:
                print("解析失败:", e)



        page.on("response", handle_response)


        page.goto(product_url)

        # 等待接口触发
        page.wait_for_timeout(5000)

        all_items = page.locator("[class*='valueItem']")

        sku_items = []

        for i in range(all_items.count()):

            item = all_items.nth(i)

            cls = item.get_attribute("class")

            if (
                "valueItem--" in cls
                and "isDisabled" not in cls
            ):
                sku_items.append(item)

        print("真实SKU数量:", len(sku_items))

        for item in sku_items:
            spec = item.locator("span").first.get_attribute("title")
            print(spec)

        selected = sku_items[0]


        selected_spec = selected.locator(
            "span[class*='valueItemText']"
        ).first.get_attribute("title")



        print("选择规格:", selected_spec)

        selected.click()

        for item in result:
            item["规格"] = selected_spec



        context.close()
        browser.close()


    return result