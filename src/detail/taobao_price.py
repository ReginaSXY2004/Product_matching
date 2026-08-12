import re
import json


def parse_price_response(response_text):

    """
    解析淘宝API返回价格
    """

    result = []

    try:

        text = re.sub(
            r'^[^(]*\(',
            '',
            response_text
        )

        text = re.sub(
            r'\);?\s*$',
            '',
            text
        )


        data = json.loads(text)


        sku_info = (
            data
            .get("data", {})
            .get("skuCore", {})
            .get("sku2info", {})
        )


        result = extract_price(sku_info)


    except Exception as e:
        print(
            "API价格解析失败:",
            e
        )


    return result



def parse_price_from_html(content):
    """
    解析页面HTML里的sku2info
    """

    result = []

    try:
        key = '"sku2info":'

        start = content.find(key)

        if start == -1:
            print("HTML中没有找到sku2info")
            return result


        # 找 sku2info 后面的第一个 {
        brace_start = content.find(
            "{",
            start + len(key)
        )

        if brace_start == -1:
            print("没有找到sku2info对象开始")
            return result


        # 根据括号匹配找到完整 JSON
        count = 0
        brace_end = -1

        for i in range(brace_start, len(content)):

            if content[i] == "{":
                count += 1

            elif content[i] == "}":
                count -= 1

                if count == 0:
                    brace_end = i + 1
                    break


        if brace_end == -1:
            print("没有找到sku2info对象结束")
            return result


        sku_json = content[
            brace_start:brace_end
        ]


        sku_info = json.loads(
            sku_json
        )


        result = extract_price(
            sku_info
        )


    except Exception as e:

        print(
            "HTML价格解析失败:",
            e
        )


    return result



def extract_price(sku_info):

    """
    公共价格提取逻辑
    """

    result = []


    for sku_id, info in sku_info.items():

        if sku_id == "0":
            sku_id = "default"

        price = info.get("price")
        sub_price = info.get("subPrice")

        def parse_price(p):
            if isinstance(p, dict):
                return (
                    p.get("priceText")
                    or p.get("priceMoney")
                )

            if isinstance(p, str):
                return p

            return None


        before = parse_price(price)
        after = parse_price(sub_price)

        if before or after:
            result.append(
                {
                    "sku_id": sku_id,
                    "优惠前": before,
                    "补贴后": after
                }
            )

    return result