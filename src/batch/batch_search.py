import pandas as pd
import time
import random
import json

from src.config import DATA_DIR, OUTPUT_DIR, STORAGE_STATE_PATH
from src.search.taobao_search import search_taobao, _create_context, _save_storage_state
from playwright.sync_api import sync_playwright

# 输入文件
INPUT_FILE = DATA_DIR / "test_products.xlsx"

# 输出文件
OUTPUT_FILE = OUTPUT_DIR / "search_results.xlsx"

# 日志文件
LOG_FILE = OUTPUT_DIR / "search_log.json"


def batch_search(
        topk=3,
        max_products=None
):

    # 读取商品池
    products = pd.read_excel(INPUT_FILE)

    # 测试阶段可以限制数量
    if max_products:
        products = products.head(max_products)

    all_results = []
    logs = {}

    total = len(products)
    print(f"开始批量搜索，共 {total} 个商品")
    
    batch_start_time = time.time()

    # 启动 Playwright 一次，所有商品共享同一个 browser/context/page
    with sync_playwright() as p:
        browser, context = _create_context(p, STORAGE_STATE_PATH)
        page = context.new_page()

        for index, row in products.iterrows():

            goods_id = row["goodsId"]
            title = row["商品名称"]

            print(f"\n[{index+1}/{total}] 搜索: {title}")

            start_time = time.time()

            try:
                # 传递 page 和 context，复用浏览器
                result = search_taobao(
                    keyword=title,
                    topk=topk,
                    page=page,
                    context=context,
                    check_login=(index == 0)
                )

                cost_time = round(time.time() - start_time, 2)
                
                # 检查是否检测到反爬
                captcha_detected = result.get("captcha_detected", False)
                candidates = result.get("candidates", [])
                raw_text = result.get("raw_text", "")

                logs[str(goods_id)] = {
                    "title": title,
                    "status": "success",
                    "candidate_num": len(candidates),
                    "cost_time": cost_time,
                    "captcha_detected": captcha_detected
                }

                # 保存候选结果
                for rank, item in enumerate(candidates, start=1):
                    all_results.append(
                        {
                            "goodsId": goods_id,
                            "source_title": title,
                            "rank": rank,
                            "candidate_title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "raw_text": raw_text
                        }
                    )

                # ✓ 每个商品搜索后立即保存登录状态，避免下一个商品需要重新登录
                _save_storage_state(context, STORAGE_STATE_PATH, f"after search {goods_id}")

                if captcha_detected:
                    print(f"⚠️ 警告: 检测到反爬机制，获取 {len(candidates)} 个候选，耗时 {cost_time}s")
                else:
                    print(f"✓ 成功，获取 {len(candidates)} 个候选，耗时 {cost_time}s")

            except Exception as e:
                cost_time = round(time.time() - start_time, 2)

                logs[str(goods_id)] = {
                    "title": title,
                    "status": "failed",
                    "error": str(e),
                    "cost_time": cost_time,
                    "captcha_detected": False
                }

                print(f"✗ 失败: {e}")

            # 防止请求过快
            sleep_time = random.uniform(3, 8)
            print(f"等待 {round(sleep_time, 1)} 秒...")
            time.sleep(sleep_time)

        # 批量搜索结束，保存 storage_state 并关闭
        _save_storage_state(context, STORAGE_STATE_PATH, "batch search end")
        context.close()
        browser.close()

    batch_cost_time = round(time.time() - batch_start_time, 2)

    # 保存候选结果
    result_df = pd.DataFrame(all_results)
    result_df.to_excel(OUTPUT_FILE, index=False)

    # 保存日志
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

    # 统计信息
    success_count = sum(1 for log in logs.values() if log["status"] == "success")
    failed_count = total - success_count
    captcha_count = sum(1 for log in logs.values() if log.get("captcha_detected", False))
    avg_time = batch_cost_time / total if total > 0 else 0

    print("\n" + "="*50)
    print("批量搜索完成")
    print("="*50)
    print(f"总耗时: {batch_cost_time}s")
    print(f"平均单个耗时: {avg_time:.2f}s")
    print(f"成功: {success_count}/{total}")
    print(f"失败: {failed_count}/{total}")
    print(f"检测到反爬: {captcha_count}/{total}")
    print("-"*50)
    print(f"候选结果保存: {OUTPUT_FILE}")
    print(f"日志保存: {LOG_FILE}")
    print("="*50)


if __name__ == "__main__":


    batch_search(
        topk=10,

        # 第一次建议只测试10个
        # None代表全部100个
        max_products=None
    )
