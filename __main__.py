import os
import json
import time
import datetime
from rich.live import Live

from models import *
from parse import *
from print import prepare_live_print, print_stocks

# load stocks.json
def load_stocks_json() -> dict | None:
  self_dir = os.path.dirname(os.path.abspath(__file__))
  try:
    with open(os.path.join(self_dir, "stocks.json"), "r", encoding="utf-8") as f:
      return json.load(f)
  except Exception as e:
      print("stocks.json load error")
      print(e)
  return None


def check_market_open(data_store: DataStore) -> datetime.datetime:
  now = datetime.datetime.today()
  if now.weekday() < 6 and now.hour in [9, 10, 11, 13, 14, 15]:
    # 10:00~14:59
    if now.hour in [10, 13, 14]:
      data_store.market_open = True    
      return now
    # 9:29, 11:31 and 15:01
    if (now.hour == 9 and now.minute >= 29) or (
      now.hour == 11 and now.minute <= 31) or (
      now.hour == 15 and now.minute <= 1):
      data_store.market_open = True
      return now
  data_store.market_open = False
  return now


# main
def main() -> None:
  cfg: dict = load_stocks_json()
  proxy = cfg["proxy"]

  data_store: DataStore = DataStore()
  data_store.interval_seconds = float(cfg["interval_seconds"])

  eastmoney: dict = cfg["eastmoney"]
  if (eastmoney["enable"] == True):
    print(eastmoney)
    return
  else:
    data_store.stock_groups = parse_stock_groups_from_local(cfg)

  for market_index_code in cfg["market_indices"]:
    data_store.market_indices.stocks.append(Stock(market_index_code))
  
  data_store.all_stocks = data_store.market_indices.stocks.copy()
  stock_codes: list = list(map(lambda s: s.code, data_store.all_stocks))

  for group in data_store.stock_groups:
    for i in range(len(group.stocks)):
      if group.stocks[i].code in stock_codes:
        group.stocks[i] = data_store.all_stocks[stock_codes.index(group.stocks[i].code)]
      else:
        data_store.all_stocks.append(group.stocks[i])
        stock_codes.append(group.stocks[i].code)
  stock_codes = ",".join(stock_codes)
  if len(stock_codes) <= 0:
    return
  
  print("\n")
  live_print: Live = prepare_live_print()
  data_store.market_open = True
  while data_store.market_open:
      try:
          t_req_start = check_market_open(data_store)
          stock_info_content = get_stock_infos(stock_codes, proxy)
          if not stock_info_content:
            continue

          t_req_end = datetime.datetime.today()
          data_store.network_latency = (t_req_end - t_req_start).total_seconds()

          parse_stock_infos(cfg, data_store, stock_info_content)
          print_stocks(live_print, data_store)
          
          t_next_req = datetime.datetime.fromtimestamp(
            t_req_start.timestamp() + data_store.interval_seconds)
          if t_req_end < t_next_req:
            time.sleep((t_next_req - t_req_end).total_seconds())
      except KeyboardInterrupt:
        data_store.market_open = False
      except Exception as e:
        print(e)
        data_store.market_open = False

# run
if __name__ == "__main__":
  main()