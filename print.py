from typing import Tuple

from rich.console import Group
from rich.text import Text
from rich.table import Table
from rich.live import Live

from models import *
from utils import fraction_2, seconds_to_hms

RED = "red"
GREEN = "green"

# prepare live print
def prepare_live_print() -> Live:
  live = Live(auto_refresh=False)
  live.start()
  return live


# colorize with assemble
def colorize_assemble(data_store: DataStore, stock: Stock, text: any) -> str | Tuple:
  s = fraction_2(text) if isinstance(text, float) else str(text)
  if data_store.colorize:
    if stock.price > stock.last_day_price:
      return (s, RED)
    if stock.price < stock.last_day_price:
      return (s, GREEN)
  return s


# colorize with markup
def colorize_markup(data_store: DataStore, stock: Stock, text: any) -> str:
  s = fraction_2(text) if isinstance(text, float) else str(text)
  if data_store.colorize:
    if stock.price > stock.last_day_price:
      return f"[{RED}]{s}[/]"
    if stock.price < stock.last_day_price:
      return f"[{GREEN}]{s}[/]"
  return s


# build market status
def build_market_status(data_store: DataStore) -> Text:
  parts = ["\n"] # give a blank line at start
  if data_store.seconds_to_market_open > 0:
    parts.append(f"距开市：{seconds_to_hms(data_store.seconds_to_market_open)}")
  elif data_store.market_open:
    parts.append(("●", RED))
  else:
    parts.append(("×", GREEN))
  
  parts.append(f" 延迟/间隔：{fraction_2(data_store.network_latency)}s/{data_store.interval_seconds}s")
  parts.append("\n")

  # market indices, print sh000001 value and amplitude
  # market indices must be colorized
  value_colorize = data_store.colorize
  data_store.colorize = True
  
  for s in data_store.market_indices.stocks:
    if s.code == "sh000001":
      parts.append(colorize_assemble(data_store, s, f"{s.name[0]} {s.amplitude} {s.price}"))
    else:
      parts.append(colorize_assemble(data_store, s, f"{s.name[0]} {s.amplitude}"))
    parts.append(" ")
  
  data_store.colorize = value_colorize

  return Text.assemble(*parts)


# build stocks table
def build_stocks_table(data_store: DataStore) -> Table:
  table = Table(show_header=True)
  max_rows = 1
  for group in data_store.stock_groups:
    stock_count = len(group.stocks)
    if stock_count > max_rows:
      max_rows = stock_count

  for group in data_store.stock_groups:
      table.add_column(group.name, justify="right", no_wrap=True)
      table.add_column("¥", justify="right", no_wrap=True)
      table.add_column("%", justify="right", no_wrap=True)

  group_count = len(data_store.stock_groups)
  group: StockGroup
  for i in range(max_rows):
    row = ()
    for j in range(group_count):
      group = data_store.stock_groups[j]
      if i >= len(group.stocks):
        row += ("", "", "")
      else:
        stock: Stock = group.stocks[i]
        str_name = stock.name
        if data_store.market_open and data_store.price_arrow_up != None:
          str_name += " "
          if stock.last_price != None and stock.price != stock.last_price:
            str_name += data_store.price_arrow_up if stock.price > stock.last_price else data_store.price_arrow_down
          else:
            str_name += "-"
        row += (str_name, fraction_2(stock.price), colorize_markup(data_store, stock, stock.amplitude))
    table.add_row(*row)

  return table


# print stocks in console
def print_stocks(live: Live, data_store: DataStore) -> None:
  market_status = build_market_status(data_store)
  table = build_stocks_table(data_store)
  live.update(Group(market_status, table), refresh=True)