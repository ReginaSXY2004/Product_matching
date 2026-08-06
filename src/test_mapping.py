from detail.taobao_mapping import parse_sku_mapping


with open(
    "taobao_debug.html",
    encoding="utf-8"
) as f:

    content = f.read()


mapping = parse_sku_mapping(content)


print(mapping)