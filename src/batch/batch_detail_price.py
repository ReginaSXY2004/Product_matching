import json
import pandas as pd
import time
import random

from src.detail.taobao_sku import (
    create_taobao_page,
    get_taobao_sku_prices
)
from src.config import STORAGE_STATE_PATH
from src.config import OUTPUT_DIR


INPUT_FILE = OUTPUT_DIR / "search_results.xlsx"
OUTPUT_FILE = OUTPUT_DIR / "taobao_price_results.xlsx"
FAILED_FILE = OUTPUT_DIR / "taobao_price_failed.xlsx"
PROGRESS_FILE = OUTPUT_DIR / "taobao_price_progress.json"


def _load_progress():
    if not PROGRESS_FILE.exists():
        return {"success": [], "failed": []}

    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "success": list(data.get("success", [])),
            "failed": list(data.get("failed", []))
        }
    except Exception:
        return {"success": [], "failed": []}


def _save_progress(success_ids, failed_ids):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "success": sorted(success_ids),
                "failed": sorted(failed_ids)
            },
            f,
            ensure_ascii=False,
            indent=2
        )


def batch_detail_price(max_products=None):
    progress = _load_progress()
    success_ids = set(str(x) for x in progress.get("success", []))
    failed_ids = set(str(x) for x in progress.get("failed", []))

    p, browser, page = create_taobao_page(STORAGE_STATE_PATH)

    try:
        products = pd.read_excel(INPUT_FILE)

        if max_products:
            products = products.head(max_products)

        all_results = []
        failed_results = []
        total = len(products)

        print(f"开始抓取详情页，共 {total} 个")
        print(f"已成功商品数: {len(success_ids)}")
        print(f"已失败商品数: {len(failed_ids)}")

        for index, row in products.iterrows():
            goods_id = str(row["goodsId"])
            url = row["url"]

            if goods_id in success_ids:
                print(f"跳过已成功商品: {goods_id}")
                continue

            print(f"\n[{index+1}/{total}] {url}")

            while True:
                try:
                    sku_prices = get_taobao_sku_prices(page, url)

                    if not sku_prices:
                        raise ValueError("没有获取任何价格")

                    for item in sku_prices:
                        item["goodsId"] = goods_id
                        item["url"] = url
                        all_results.append(item)

                    success_ids.add(goods_id)
                    failed_ids.discard(goods_id)
                    _save_progress(success_ids, failed_ids)

                    print(f"成功 {goods_id}，获取 {len(sku_prices)} 个SKU")
                    break

                except Exception as e:
                    error_msg = str(e)
                    lower_msg = error_msg.lower()

                    print("失败:", error_msg)

                    if "验证码" in error_msg or "captcha" in lower_msg:
                        print("检测到淘宝验证码，请人工处理")
                        print("当前页面保持打开，完成验证码后按 Enter 继续；输入 q 退出当前批次")
                        user_input = input("请完成验证码后按 Enter 继续，输入 q 退出: ").strip()
                        if user_input.lower() == "q":
                            print("用户选择退出，当前批次结束")
                            _save_progress(success_ids, failed_ids)
                            return
                        # 当前商品继续重试，页面保留不关闭
                        continue

                    failed_ids.add(goods_id)
                    failed_results.append(
                        {
                            "goodsId": goods_id,
                            "url": url,
                            "status": "no_price" if "没有获取" in error_msg or "没有任何价格" in error_msg else "error",
                            "error": error_msg
                        }
                    )
                    _save_progress(success_ids, failed_ids)
                    break

                finally:
                    # 防止访问过快
                    sleep_time = random.uniform(3, 8)
                    print(f"等待 {sleep_time:.1f}s")
                    time.sleep(sleep_time)

        df = pd.DataFrame(all_results)
        df.to_excel(OUTPUT_FILE, index=False)

        failed_df = pd.DataFrame(failed_results)
        failed_df.to_excel(FAILED_FILE, index=False)

        print("================")
        print("完成")
        print(f"保存到: {OUTPUT_FILE}")
        print(f"失败记录: {FAILED_FILE}")
        print(f"进度文件: {PROGRESS_FILE}")

    finally:
        browser.close()
        p.stop()


if __name__ == "__main__":
    batch_detail_price(max_products=5)