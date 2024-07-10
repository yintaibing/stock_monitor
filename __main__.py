import os
import json
import time
import datetime
import traceback
from rich.live import Live

from models import *
from parse import *
from print import prepare_live_print, print_stocks
import utils

# load stocks.json
def load_json_file(file_name: str) -> dict | None:
  self_dir = os.path.dirname(os.path.abspath(__file__))
  try:
    with open(os.path.join(self_dir, file_name), "r", encoding="utf-8") as f:
      return json.load(f)
  except Exception as e:
      print("config.json load error")
      traceback.print_exc()
  return None


# compute remaining seconds to any time of today
def seconds_to_time_today(now: datetime.datetime, hour: int, minute: int) -> int:
  target = now.replace(hour=hour, minute=minute, second=0)
  seconds = (target - now).total_seconds()
  if seconds > 0 and seconds < 1:
    return 1
  return int(seconds) + 1


# check market is open or not
# <0: market closed
# ==0: market is open
# >0: remaining seconds to market open
def check_market_status(now: datetime.datetime) -> int:
  if now.weekday() <= 5:
    if now.hour <= 9:
      if now.hour < 9 or now.minute < 30:
        # before 9:30, before market open
        return seconds_to_time_today(now, 9, 30)
    if now.hour <= 12:
      if now.hour > 11 or (now.hour == 11 and now.minute > 30):
        # 11:30 ~ 12:59, lunch break
        return seconds_to_time_today(now, 13, 0)
    if now.hour >= 15:
      # after 15:00, market closed
      return -1
    return 0
  return -1


# main
def main() -> None:
  cfg: dict = load_json_file("config.json")
  local: dict = load_json_file("local.json")
  if not (cfg and local):
    return

  proxy = cfg["proxy"]

  data_store: DataStore = DataStore()
  data_store.colorize = bool(cfg["colorize"])
  data_store.interval_seconds = float(cfg["interval_seconds"])
  price_arrows = str(cfg["price_arrows"])
  if price_arrows != None and len(price_arrows) > 1:
    data_store.price_arrow_up = price_arrows[0]
    data_store.price_arrow_down = price_arrows[1]

  eastmoney: dict = cfg["eastmoney"]
  if (eastmoney["enable"] == True):
    print(eastmoney)
    return
  else:
    data_store.stock_groups = parse_stock_groups_from_local(local)

  for code in local["market_indices"]:
    if utils.verify_stock_code(code, is_market_index=True):
      data_store.market_indices.stocks.append(Stock(code))
    else:
      print(f"bad stock code: {code}, ignore")
  
  data_store.all_stocks = data_store.market_indices.stocks.copy()
  stock_codes: list = list(map(lambda s: s.code, data_store.all_stocks))

  for group in data_store.stock_groups:
    for i in range(len(group.stocks)):
      if group.stocks[i].code in stock_codes:
        group.stocks[i] = data_store.all_stocks[stock_codes.index(group.stocks[i].code)]
      else:
        data_store.all_stocks.append(group.stocks[i])
        stock_codes.append(group.stocks[i].code)
  if len(stock_codes) <= 0:
    return
  
  full_codes = ""
  for code in stock_codes:
    full_codes += utils.add_sh_sz_prefix(code) + ","
  full_codes = full_codes[:-1]
  # print(f"full_codes={full_codes}\n")

  live_print: Live = prepare_live_print()
  market_status = 0
  stock_info_content: str | None = None
  req_fail_count = 0
  while market_status >= 0:
    try:
        t_req_start = datetime.datetime.today()
        market_status = check_market_status(t_req_start)
        data_store.market_open = market_status == 0
        data_store.seconds_to_market_open = market_status

        # before market open, request only once(success), then wait
        if market_status > 0 and stock_info_content:
          print_stocks(live_print, data_store)
          time.sleep(data_store.interval_seconds)
          continue
        
        # request stock infos
        stock_info_content = get_stock_infos(full_codes, proxy, data_store.interval_seconds)
        
        # if request failed more than 10 times, terminate
        if not stock_info_content:
          req_fail_count += 1
          if req_fail_count < 10:
            continue
          print("req_fail_count >= 10")
          market_status = -1
          data_store.market_open = False
          break
          
        req_fail_count = 0
        t_req_end = datetime.datetime.today()
        data_store.network_latency = (t_req_end - t_req_start).total_seconds()

        parse_stock_infos(local, data_store, stock_info_content)
        print_stocks(live_print, data_store)
        
        if data_store.market_open:
          t_next_req = datetime.datetime.fromtimestamp(
            t_req_start.timestamp() + data_store.interval_seconds)
          if t_req_end < t_next_req:
            time.sleep((t_next_req - t_req_end).total_seconds())
    except KeyboardInterrupt:
      data_store.market_open = False
    except Exception:
      traceback.print_exc()
      data_store.market_open = False

# run
if __name__ == "__main__":
  main()