from pathlib import Path
from playwright.sync_api import sync_playwright
import urllib.parse
import time

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
    try:
        cookies = page.evaluate('document.cookie')
    except Exception:
        return False

    login_cookie_names = ["cookie2", "t", "cna", "sgcookie", "thw", "tracknick"]
    for name in login_cookie_names:
        if f"{name}=" in cookies:
            return True
    return False


def _page_is_logged_in(page) -> bool:
    try:
        url = page.url
        if "login.taobao.com" in url or "passport.taobao.com" in url:
            return False
        if _has_login_cookie(page):
            return True
        body = page.locator("body").inner_text(timeout=5000)
    except Exception:
        return False

    if "请登录" in body or "扫码登录" in body or "登录淘宝" in body:
        return False
    return True


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
    browser = p.chromium.launch(
        headless=False,
        channel="chrome"
    )

    if storage_state_path.exists():
        print("使用已保存的登录状态：", storage_state_path)
        context = browser.new_context(
            storage_state=str(storage_state_path),
            viewport={"width": 1280, "height": 900}
        )
    else:
        print("未找到登录状态文件，将进入扫码登录流程")
        context = browser.new_context(
            viewport={"width": 1280, "height": 900}
        )

    return browser, context


def _detect_captcha(page, body_text: str) -> bool:
    """检测是否出现了滑块验证、登录异常等反爬机制"""
    try:
        url = page.url
        # 检测 URL 中的关键词
        if "check.taobao.com" in url or "passport" in url or "seccodelogin" in url:
            return True
        
        # 检测页面文本中的反爬关键词
        captcha_keywords = [
            "滑块验证",
            "拖动滑块",
            "安全验证",
            "验证码",
            "我是人类",
            "suspected robot",
            "请输入验证码",
            "perform suspicious"
        ]
        
        for keyword in captcha_keywords:
            if keyword in body_text:
                return True
        
        return False
    except Exception:
        return False


def _search_single_page(page, keyword, topk):
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
    
    storage_state_path = _get_storage_state_path()
    
    login_url = "https://login.taobao.com/member/login.jhtml"
    search_url = "https://s.taobao.com/search?q=" + urllib.parse.quote(keyword)

    print("正在搜索:", keyword)

    page.goto(login_url, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    _print_page_state(page, "after initial goto")

    if _page_needs_login(page):
        if storage_state_path.exists():
            print("保存的登录状态失效，删除后重新登录")
            storage_state_path.unlink(missing_ok=True)
            page.goto(login_url, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

        print("请扫码登录淘宝，登录完成后请耐心等待页面跳转")
        if _wait_for_login(page, timeout=180):
            print("检测到已登录，保存当前 storage_state")
            _print_page_state(page, "after login")
        else:
            print("登录超时，请检查扫码流程或网络状态")
    else:
        if not storage_state_path.exists():
            print("检测到已登录状态，正在保存 storage_state")
            _print_page_state(page, "already logged in")

    page.goto(search_url, wait_until="networkidle")
    page.wait_for_timeout(5000)

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

    page.screenshot(path=str(DEBUG_SCREENSHOTS_DIR / f"{safe_name}.png"))

    html = page.content()

    html_path = DEBUG_HTML_DIR / f"{safe_name}.html"
    text_path = DEBUG_HTML_DIR / f"{safe_name}.txt"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    with open(text_path, "w", encoding="utf-8") as f:
        f.write(raw_text)

    return results


def search_taobao(keyword, topk=5, page=None, context=None):
    """输入关键词，返回淘宝搜索结果TopK
    
    如果 page 和 context 已提供（批量搜索模式）：
        - 直接使用已有的 page，无需启动关闭浏览器
        - 调用者负责最后关闭 browser/context
    
    否则（单次搜索模式）：
        - 完整启动 Playwright，搜索，关闭
    """
    
    if page is not None and context is not None:
        # 批量搜索模式：复用已有的 page
        return _search_single_page(page, keyword, topk)
    
    # 单次搜索模式：启动并关闭
    results = []
    storage_state_path = _get_storage_state_path()

    with sync_playwright() as p:
        browser, context = _create_context(p, storage_state_path)
        page = context.new_page()

        results = _search_single_page(page, keyword, topk)
        
        # 单次模式才保存 storage_state
        _save_storage_state(context, storage_state_path, "single search end")
        context.close()
        browser.close()

    return results
