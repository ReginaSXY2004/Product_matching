import pandas as pd
import time
import random
from pathlib import Path

from src.detail.taobao_sku import (
    create_taobao_page,
    get_taobao_sku_prices
)
from src.config import STORAGE_STATE_PATH
from src.config import OUTPUT_DIR


INPUT_FILE = OUTPUT_DIR / "search_results.xlsx"
OUTPUT_FILE = OUTPUT_DIR / "taobao_price_results.xlsx"
FAILED_FILE = OUTPUT_DIR / "taobao_price_failed.xlsx"


def batch_detail_price(max_products=None):

    p, browser, page = create_taobao_page(
    STORAGE_STATE_PATH
    )

    # 读取淘宝候选链接
    products = pd.read_excel(INPUT_FILE)


    if max_products:
        products = products.head(max_products)


    all_results = []
    failed_results = []


    total = len(products)

    print(f"开始抓取详情页，共 {total} 个")


    for index, row in products.iterrows():

        goods_id = row["goodsId"]
        url = row["url"]

        print(
            f"\n[{index+1}/{total}] {url}"
        )


        try:

            sku_prices = get_taobao_sku_prices(
                page,
                url
            )


            for item in sku_prices:

                item["goodsId"] = goods_id
                item["url"] = url

                all_results.append(item)


            print(
                f"成功 {goods_id}，获取 {len(sku_prices)} 个SKU"
            )


        except Exception as e:

            error_msg = str(e)

            print(
                "失败:",
                error_msg
            )


            # 淘宝验证码，停止整个batch
            if "验证码" in error_msg:
                print("检测到淘宝验证码，停止任务")
                
                failed_results.append(
                    {
                        "goodsId": goods_id,
                        "url": url,
                        "status": "captcha",
                        "error": "淘宝验证码拦截"
                    }
                )

                break


            # 普通失败继续
            failed_results.append(
                {
                    "goodsId": goods_id,
                    "url": url,
                    "status": "parse_failed",
                    "error": "没有获取价格"
                }
            )


        # 防止访问过快
        sleep_time = random.uniform(3,8)

        print(
            f"等待 {sleep_time:.1f}s"
        )

        time.sleep(sleep_time)



    df = pd.DataFrame(all_results)

    df.to_excel(
        OUTPUT_FILE,
        index=False
    )

    failed_df = pd.DataFrame(failed_results)

    failed_df.to_excel(
        FAILED_FILE,
        index=False
    )

    browser.close()
    p.stop()

    print("================")
    print("完成")
    print(
        f"保存到: {OUTPUT_FILE}"
    )



if __name__ == "__main__":

    batch_detail_price(
        max_products=5
    )