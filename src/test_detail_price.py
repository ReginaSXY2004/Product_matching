from pathlib import Path

from detail.taobao_sku import get_taobao_sku_prices


BASE_DIR = Path(__file__).resolve().parent.parent

STORAGE_PATH = BASE_DIR / "data" / "taobao_storage_state.json"


product_url = "https://detail.tmall.com/item.htm?id=1062950295308&ns=1&abbucket=3&xxc=taobaoSearch&mi_id=0000NQbahSMU9OHLQeO831QhkkSLMnQdEtzsHvLwSJ_yK8Y&skuId=6277743238257&priceTId=2150434717858913922251549e10c8&utparam=%7B%22aplus_abtest%22%3A%22f78892c14747876465f28545260b094d%22%7D&spm=a21n57.1.item.2"


result = get_taobao_sku_prices(
    product_url,
    STORAGE_PATH
)


for item in result:
    print("================")
    print(item)