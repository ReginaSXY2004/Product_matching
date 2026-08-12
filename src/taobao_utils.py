def _detect_captcha(page, body_text: str) -> bool:
    """检测是否出现了滑块验证、登录异常等反爬机制"""
    try:
        url = (page.url or "").lower()
        html_text = ""
        try:
            html_text = (page.content() or "").lower()
        except Exception:
            html_text = ""

        text_blob = f"{(body_text or '').lower()} {html_text}"

        # 检测 URL 中的关键词
        if any(token in url for token in [
            "check.taobao.com",
            "passport",
            "seccodelogin",
            "captcha",
            "punish",
            "verify",
        ]):
            return True

        # 检测页面正文和 HTML 头部/脚本中的反爬关键词
        captcha_keywords = [
            "滑块验证",
            "拖动滑块",
            "安全验证",
            "验证码",
            "我是人类",
            "suspected robot",
            "请输入验证码",
            "perform suspicious",
            "captcha",
            "verify"
        ]

        for keyword in captcha_keywords:
            if keyword.lower() in text_blob:
                return True

        # 额外检查常见验证码容器/iframe
        try:
            for selector in [
                "#nc_1_n1z",
                ".nc-container",
                "iframe[src*='captcha']",
                "iframe[src*='verify']",
                "div.nc-container",
            ]:
                if page.locator(selector).count() > 0:
                    return True
        except Exception:
            pass

        return False
    except Exception:
        return False
