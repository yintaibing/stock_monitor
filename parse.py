import requests

from models import *

# parse stock groups from local
def parse_stock_groups_from_local(cfg: dict) -> list:
  stock_groups = []
  local_stock_groups: list = cfg["local_stock_groups"]
  for item in local_stock_groups:
    if isinstance(item, list) and len(item) > 0:
      group = StockGroup(name=item[0], stock_codes=item[1:] if len(item) > 1 else [])
      stock_groups.append(group)
  return stock_groups


# get stock info
def get_stock_infos(stock_codes: str, proxy: dict) -> str:
  url = f"https://qt.gtimg.cn/q={stock_codes}"
  try:
    response = requests.get(url, proxies=proxy)
    charset = response.headers["Content-Type"].split(";")[1]
    encoding = charset.split("=")[1]
    content = response.content.decode(encoding)
    return content
  except Exception as e:
    print(e)
    return None


# hide stock name
def hide_stock_name(cfg: dict, name: str) -> str:
  hidings: dict = cfg["stock_name_hidings"]
  for k, v in hidings.items():
    key = str(k).strip()
    value = str(v).strip()
    if len(key) > 0 and len(value) > 0:
      if key.startswith("*"):
        key = key[1:]
        if name.endswith(key):
          return name.replace(key, value)
      elif key.endswith("*"):
        key = key[:-1]
        if name.startswith(key):
          return name.replace(key, value)
      elif name.count(key) > 0:
        return name.replace(key, value)
  return name


# parse stock info
def parse_stock_infos(cfg: dict, data_store: DataStore, content: str) -> None:
  stock_infos = content.split(";")
  stock: Stock
  for i in range(len(stock_infos)):
    if stock_infos[i].startswith("\n"):
      stock_infos[i] = stock_infos[i][1:]
    if stock_infos[i].endswith("\n"):
      stock_infos[i] = stock_infos[i][:1]
    if len(stock_infos[i]) <= 0:
      continue

    stock = None
    items = stock_infos[i].split("~")
    code = items[2]
    if data_store.all_stocks[i].code.endswith(code):
      stock = data_store.all_stocks[i]
    else:
      for s in data_store.all_stocks:
        if s.code.endswith(code):
          stock = s
          break

    if stock:
      if not stock.name:
        stock.name = hide_stock_name(cfg, items[1])
        stock.last_day_price = float(items[4])
      stock.price = float(items[3])
      stock.amplitude = float(items[32])