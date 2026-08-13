from pathlib import Path
import random
from playwright.sync_api import sync_playwright
import urllib.parse
from urllib.parse import unquote
from src.taobao_login import (
    _create_context,
    _page_is_logged_in,
    _wait_for_login,
    _save_login_state_if_ready,
    _save_storage_state
)
import time

from src.taobao_utils import _detect_captcha
from src.config import DEBUG_HTML_DIR, DEBUG_SCREENSHOTS_DIR, STORAGE_STATE_PATH

DEBUG = False


def _get_root_dir() -> Path:
    return STORAGE_STATE_PATH.parents[1]


def _get_storage_state_path() -> Path:
    return STORAGE_STATE_PATH


def _print_page_state(page, tag: str):
    if not DEBUG:
        return

    try:
        url = page.url
        body = page.locator("body").inner_text(timeout=5000)
        snippet = body[:200].replace("\n", " ").replace("\r", " ")
        print(f"[PAGE STATE] {tag} url={url}")
        print(f"[PAGE STATE] {tag} body_snippet={snippet}")
    except Exception as exc:
        print(f"[PAGE STATE] {tag} failed to read page state: {exc}")


def _page_needs_login(page) -> bool:
    try:
        url = page.url
        body = page.locator("body").inner_text(timeout=5000)
    except Exception:
        return True

    if "login.taobao.com" in url or "passport.taobao.com" in url:
        return True
    if "请登录" in body or "扫码登录" in body or "登录淘宝" in body:
        return True
    return False


def _has_login_cookie(page) -> bool:

    login_cookie_names = [
        "cookie2",
        "tracknick",
        "lgc",
        "lid"
    ]

    try:
        cookies = page.context.cookies()

        names = {
            c["name"]
            for c in cookies
        }

        return (
            "cookie2" in names
            and "tracknick" in names
        )

    except Exception:
        return False


def _save_login_state_if_ready(page, storage_state_path, reason: str) -> bool:
    if _has_login_cookie(page):
        _save_storage_state(page.context, storage_state_path, reason)
        return True
    return False


def _page_is_logged_in(page) -> bool:
    """
    判断淘宝是否登录
    优先相信cookie，不依赖页面文字
    """

    try:
        if _has_login_cookie(page):
            return True

        url = page.url

        if "login.taobao.com" in url:
            return False

        return False

    except Exception:
        return False


def _wait_for_login(page, timeout=180) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        _print_page_state(page, "waiting for login")
        if _page_is_logged_in(page):
            return True
        time.sleep(3)
    return False


def _save_storage_state(context, storage_state_path, reason: str):
    try:
        context.storage_state(path=str(storage_state_path))
        print(f"[SAVE STATE] 保存storage_state ({reason}) 到: {storage_state_path}")
    except Exception as exc:
        print(f"[SAVE STATE] 保存storage_state失败: {exc}")


def _create_context(p, storage_state_path):

    # Google Chrome浏览器，现在已被风控
    # context = p.chromium.launch_persistent_context(
    #     user_data_dir="data/taobao_chrome_profile",
    #     headless=False,
    #     channel="chrome",
    #     viewport={"width":1280,"height":900},
    #     args=[
    #         "--disable-blink-features=AutomationControlled"
    #     ]
    # )

    # Edge浏览器
    browser = p.chromium.launch(
        headless=False,
        channel="msedge",
        args=[
            "--disable-blink-features=AutomationControlled"
        ]
    )

    if storage_state_path.exists():
        context = browser.new_context(
            storage_state=str(storage_state_path),
            viewport={
                "width":1280,
                "height":900
            }
        )
    else:
        context = browser.new_context(
            viewport={
                "width":1280,
                "height":900
            }
        )

    return browser, context


def _search_single_page(page, keyword, topk, check_login=True):
    """
    单个商品的搜索逻辑，返回结果及元数据
    返回格式: {
        "candidates": [...],
        "raw_text": "...",
        "captcha_detected": False,
        "url": "..."
    }
    """
    results = {
        "candidates": [],
        "raw_text": "",
        "captcha_detected": False,
        "url": ""
    }
    
    keyword = unquote(str(keyword)).strip().strip("'\"").strip()
    storage_state_path = _get_storage_state_path()
    
    login_url = "https://login.taobao.com/member/login.jhtml"
    search_url = "https://s.taobao.com/search"

    print("正在搜索:", keyword)

    if check_login:
        page.goto("https://www.taobao.com", wait_until="domcontentloaded")
        page.wait_for_timeout(8000)

        if not _page_is_logged_in(page):
            print("登录状态检查失败，等待确认...")
            page.wait_for_timeout(3000)

            if not _page_is_logged_in(page):
                print("确认未登录，需要扫码")

                page.goto(
                    "https://login.taobao.com/member/login.jhtml",
                    wait_until="domcontentloaded"
                )

            page.wait_for_timeout(5000)

            print("请扫码登录淘宝")

            if _wait_for_login(page, timeout=180):
                print("登录成功")
                _save_login_state_if_ready(
                    page,
                    storage_state_path,
                    "after login"
                )
            else:
                print("登录失败")
        else:
            print("已有登录状态")
            print("cookies:", page.context.cookies())

    print("FINAL SEARCH URL:", search_url)
    page.goto(search_url)
    print("打开搜索页后URL:", page.url)
    print("INPUT数量:", page.locator("input").count())

    for i in range(page.locator("input").count()):
        inp = page.locator("input").nth(i)
        print(
            i,
            inp.get_attribute("name"),
            inp.get_attribute("placeholder"),
            inp.is_visible()
        )

    page.wait_for_timeout(random.randint(1500,4000))

    search_box = page.locator("input[name='q']")

    print("search_box count:", search_box.count())
    
    search_box.click()

    page.keyboard.type(keyword, delay=random.randint(80,250))

    print("输入后的值:", search_box.input_value())

    page.wait_for_timeout(1000)

    page.keyboard.press("Enter")

    page.wait_for_timeout(random.randint(6000,12000))

    print("CURRENT URL:", page.url)

    #鼠标往下滚动
    page.mouse.wheel(
    0,
    random.randint(300,700)
    )
    page.wait_for_timeout(
        random.randint(1000,3000)
    )

    # 获取搜索结果页面的完整文本（用于后续商品匹配）
    try:
        raw_text = page.locator("body").inner_text()
        
        results["raw_text"] = raw_text
    except Exception as exc:
        print(f"无法获取页面文本: {exc}")
        raw_text = ""

    # 检测是否出现反爬机制
    captcha_detected = _detect_captcha(page, raw_text)
    results["captcha_detected"] = captcha_detected
    
    if captcha_detected:
        print("⚠️ 警告: 检测到滑块验证/安全验证，可能需要手动处理")
        results["url"] = page.url
        return results

    results["url"] = page.url

    product_links = page.locator("a").evaluate_all(
        """
        elements => elements.map(
            e => ({
                text:e.innerText,
                href:e.href
            })
        )
        """
    )

    product_links = [
        x for x in product_links
        if "item.taobao.com" in x["href"]
        or "detail.tmall.com" in x["href"]
    ]

    print("商品链接数量:", len(product_links))

    for x in product_links[:topk]:
        results["candidates"].append(
            {
                "title": x["text"],
                "url": x["href"]
            }
        )

    page.wait_for_timeout(3000)

    safe_name = "".join(
        c for c in keyword if c.isalnum() or c in (" ", "_", "-")
    ).strip()[:20] or "taobao"

    # 仅保留必要的截图，避免大容量文本存储
    page.screenshot(path=str(DEBUG_SCREENSHOTS_DIR / f"{safe_name}.png"))

    if captcha_detected:
        html = page.content()
        html_path = DEBUG_HTML_DIR / f"{safe_name}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

    return results


def search_taobao(keyword, topk=5, page=None, context=None, check_login=True):
    """输入关键词，返回淘宝搜索结果TopK
    
    如果 page 和 context 已提供（批量搜索模式）：
        - 直接使用已有的 page，无需启动关闭浏览器
        - 调用者负责最后关闭 browser/context
    
    否则（单次搜索模式）：
        - 完整启动 Playwright，搜索，关闭
    """
    
    if page is not None and context is not None:
        # 批量搜索模式：复用已有的 page
        return _search_single_page(page, keyword, topk, check_login=check_login)
    
    # 单次搜索模式：启动并关闭
    results = []
    storage_state_path = _get_storage_state_path()

    with sync_playwright() as p:
        browser, context = _create_context(p, storage_state_path)
        page = context.new_page()

        page.on(
            "response",
            lambda response: print(response.status, response.url)
            if ("mtop" in response.url or "search" in response.url)
            else None
        )

        results = _search_single_page(page, keyword, topk)
        
        # 单次模式才保存 storage_state
        _save_storage_state(context, storage_state_path, "single search end")
        context.close()

    return results
