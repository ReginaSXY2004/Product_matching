def merge_sku_price(price_list, sku_mapping):

    result = []

    for item in price_list:

        sku_id = item["sku_id"]
        spec = sku_mapping.get(sku_id)

        if spec is None:
            spec = ""

        item["规格"] = spec

        result.append(item)

    return result

