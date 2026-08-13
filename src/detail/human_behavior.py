import random
import time


def simulate_browsing(page):
    """
    模拟简单浏览行为
    """

    # 页面打开后停留
    wait = random.uniform(2, 5)
    print(f"浏览页面等待 {wait:.1f}s")
    time.sleep(wait)


    # 随机滚动
    if random.random() < 0.6:
        page.mouse.wheel(
            0,
            random.randint(300,700)
        )

        time.sleep(
            random.uniform(1,2)
        )


