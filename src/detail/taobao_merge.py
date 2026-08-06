def merge_sku_price(price_list, sku_mapping):

    result = []

    for item in price_list:

        sku_id = item["sku_id"]

        item["规格"] = sku_mapping.get(
            sku_id,
            None
        )

        result.append(item)

    return result

