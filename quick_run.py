#!/usr/bin/env python
"""
竞品库数据采集 - 快速运行脚本

使用方式:
  python quick_run.py 10    # 采集前 10 个商品
  python quick_run.py 100   # 采集前 100 个商品（推荐）
  python quick_run.py       # 采集所有商品
"""

import sys
from src.batch.batch_search import batch_search

def main():
    if len(sys.argv) > 1:
        try:
            max_products = int(sys.argv[1])
        except ValueError:
            print("错误: 请输入数字")
            print("用法: python quick_run.py [商品数量]")
            sys.exit(1)
    else:
        max_products = None
    
    print("="*60)
    print("淘宝竞品库采集工具")
    print("="*60)
    
    if max_products:
        print(f"采集前 {max_products} 个商品，每个取 Top10 候选...")
    else:
        print("采集所有商品，每个取 Top5 候选...")
    
    print("\n输出文件:")
    print("  - data/output/search_results.xlsx  (竞品候选库)")
    print("  - data/output/search_log.json       (采集日志)")
    print("\n开始采集...")
    print("="*60)
    
    batch_search(topk=5, max_products=max_products)

if __name__ == "__main__":
    main()
