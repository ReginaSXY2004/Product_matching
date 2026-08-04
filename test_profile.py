from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir="data/taobao_profile",
        headless=False,
        channel="chrome"
    )

    page = context.new_page()

    page.goto("https://www.taobao.com")

    time.sleep(10)

    print(page.url)
    print(page.locator("body").inner_text()[:500])

    input("enter close")