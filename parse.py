import requests
from io import BytesIO
from PIL import Image, ImageFile

from models import *
from utils import more_than_wan, add_sh_sz_prefix

# parse stock groups from local
def parse_stock_groups_from_local(cfg: dict) -> list:
  groups = []
  m: dict = cfg["stock_groups"]
  for name, stock_codes in m.items():
    if isinstance(stock_codes, list) and len(stock_codes) > 0:
      groups.append(StockGroup(name=name, stock_codes=stock_codes))
  return groups


# get stock info
def get_stock_infos(stock_codes: str, proxy: dict, data_store: DataStore) -> str:
  url = f"https://qt.gtimg.cn/q={stock_codes}"
  try:
    response = requests.get(url, proxies=proxy, timeout=data_store.interval_seconds * 3)
    if response.status_code == 200:
      charset = response.headers["Content-Type"].split(";")[1]
      encoding = charset.split("=")[1]
      content = response.content.decode(encoding)
      return content
  except Exception as e:
    print(e)
  return None


# hide stock name
def hide_stock_name(cfg: dict, name: str) -> str:
  if bool(cfg["stock_name_hiding_enable"]):
    hidings: dict = cfg["stock_name_hidings"]
    for k, v in hidings.items():
      key = str(k).strip()
      if len(key) > 0 and name.count(key) > 0:
        return name.replace(key, str(v).strip())
  return name


# parse stock info
def parse_stock_infos(local: dict, data_store: DataStore, content: str) -> None:
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
        stock.name = hide_stock_name(local, items[1])
        stock.last_day_price = float(items[4])
        stock.init_price = float(items[5])
      if stock.price != None:
        stock.last_price = stock.price
      stock.price = float(items[3])
      stock.amplitude = float(items[32])
      # trading stock
      if stock == data_store.show_trading_stock:
        stock.buys = items[9:19]
        buy_sell_amount_to_wan(stock.buys)
        stock.sells = items[19:29]
        buy_sell_amount_to_wan(stock.sells)
      else:
        stock.buys = None
        stock.sells = None


# convert buy or sell amount to wan
def buy_sell_amount_to_wan(ary) -> None:
  for i in range(0, len(ary)):
    if ary[i] == "0" or ary[i] == "0.00":
      ary[i] = "-"
    elif i % 2 != 0:
      ary[i] = more_than_wan(int(ary[i])) if ary[i] else "-"


# get stock chart image
def get_stock_chart_image(stock: Stock, chart_type: str, proxy: dict) -> (ImageFile.ImageFile | Image.Image) | None:
  url = f"https://image.sinajs.cn/newchart/{chart_type}/n/{add_sh_sz_prefix(stock.code)}.gif"
  try:
    response = requests.get(url, proxies=proxy, timeout=10)
    if response.status_code == 200:
      image = Image.open(fp=BytesIO(response.content))
      if image.mode != "RGB":
        image = image.convert("RGB")
      scale = 0.6
      new_size = (int(image.width * scale), int(image.height * scale))
      image.thumbnail(size=new_size, reducing_gap=3)
      return image
  except Exception as e:
    print(e)
  return None