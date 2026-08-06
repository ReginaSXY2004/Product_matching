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

        match = re.search(
            r'"sku2info":(\{.*?\}),"skuItem"',
            content
        )


        if not match:
            return result


        sku_info = json.loads(
            match.group(1)
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
            continue


        price = info.get("price")
        sub_price = info.get("subPrice")


        if price or sub_price:

            result.append(
                {
                    "sku_id": sku_id,

                    "优惠前":
                        price.get("priceText")
                        if price
                        else None,

                    "补贴后":
                        sub_price.get("priceText")
                        if sub_price
                        else None
                }
            )


    return result