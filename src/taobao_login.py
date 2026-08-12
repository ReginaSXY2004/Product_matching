import time
import json
from src.config import DEBUG_HTML_DIR, DEBUG_SCREENSHOTS_DIR, STORAGE_STATE_PATH

DEBUG = False

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
        # Prefer explicit retrieval + atomic file write for reliability
        state = context.storage_state()

        # ensure parent directory exists
        storage_state_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = storage_state_path.with_suffix('.tmp')

        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False)

        # atomic replace
        tmp_path.replace(storage_state_path)

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
