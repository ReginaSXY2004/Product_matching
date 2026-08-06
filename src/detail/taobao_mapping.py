import re


def parse_sku_mapping(content):

    # -------------------------
    # 1. 获取规格 vid -> name
    # -------------------------

    vid_to_name = {}


    values = re.findall(
        r'"vid":"(-?\d+)".*?"name":"(.*?)"',
        content
    )

    # for key in [
    # "skuMap",
    # "skuBase",
    # "skuCore",
    # "props"
    # ]:

    #     print(
    #         key,
    #         key in content
    #     )

    for vid, name in values:
        vid_to_name[vid] = name



    # -------------------------
    # 2. 获取 propPath -> sku_id
    # -------------------------

    sku_matches = re.findall(
        r'"propPath":"(.*?)","skuId":"(.*?)"',
        content
    )


    sku_to_spec = {}


    for prop_path, sku_id in sku_matches:

        # propPath:
        # 31560:1525237643

        vid = prop_path.split(":")[-1]


        spec = vid_to_name.get(
            vid
        )


        if spec:
            sku_to_spec[sku_id] = spec


    return sku_to_spec