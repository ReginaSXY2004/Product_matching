from urllib import response

from playwright.sync_api import sync_playwright
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

STORAGE_PATH = BASE_DIR / "data" / "taobao_storage_state.json"

print("STORAGE PATH:", STORAGE_PATH)

product_url = "https://detail.tmall.com/item.htm?id=1062950295308&ns=1&abbucket=3&xxc=taobaoSearch&mi_id=0000NQbahSMU9OHLQeO831QhkkSLMnQdEtzsHvLwSJ_yK8Y&skuId=6277743238257&priceTId=2150434717858913922251549e10c8&utparam=%7B%22aplus_abtest%22%3A%22f78892c14747876465f28545260b094d%22%7D&spm=a21n57.1.item.2"


with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False,
        channel="msedge",
        args=[
            "--disable-blink-features=AutomationControlled"
        ]
    )

    context = browser.new_context(
        storage_state=str(STORAGE_PATH),
        viewport={
            "width":1280,
            "height":900
        }
    )

    page = context.new_page()


    def handle_response(response):
        # url = response.url

        # if "mtop" in url: # 打印所有接口
            # parts = url.split("/")
            # print("================")
            # print(parts[4])   # API名字
            # print(parts[5])   # version

        # 只处理价格接口，打开页面后需要点击选择一个规格，才会触发打印价格接口
        if "mtop.taobao.pcdetail.data.adjust" not in response.url:
            return

        try:
            import json
            import re

            text = response.text()

            print("RAW:", text[:200])

            text = re.sub(r'^[^(]*\(', '', text)
            text = re.sub(r'\);?\s*$', '', text)

            data = json.loads(text)

            sku_info = data["data"]["skuCore"]["sku2info"]

            for sku_id, info in sku_info.items():

                price = info.get("price")
                sub_price = info.get("subPrice")

                if price or sub_price:
                    print("================")
                    print("SKU:", sku_id)

                    if price:
                        print(
                            "优惠前:",
                            price.get("priceText")
                        )

                    if sub_price:
                        print(
                            "补贴后:",
                            sub_price.get("priceText")
                        )

        except Exception as e:
            print("解析失败:", e)

    page.on("response", handle_response)


    page.goto(product_url)

    page.wait_for_timeout(10000)

    context.close()