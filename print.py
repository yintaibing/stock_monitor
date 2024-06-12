from rich.table import Table
from rich.live import Live

from models import *

# prepare live print
def prepare_live_print() -> Live:
  live = Live(auto_refresh=False)
  live.start()
  return live


# append 0 if endswith .0
def format_num(num: float) -> str:
  return "{:.2f}".format(num)


# colorize with amplitude
def colorize(stock: Stock, text: any) -> str:
  s = format_num(text) if isinstance(text, float) else str(text)
  if stock.price > stock.last_day_price:
    return "[#ff8888]" + s + "[/]"
  if stock.price < stock.last_day_price:
    return "[green]" + s + "[/]"
  return s


# build table
def build_stocks_table(data_store: DataStore) -> Table:
  title = f" 延迟/间隔：{format_num(data_store.network_latency)}s/{data_store.interval_seconds}s\n"
  title += "[#ff8888]○[/]" if data_store.market_open else "[green]×[/]"
  for s in data_store.market_indices.stocks:
    title += f" {s.name[0:1]} {colorize(s, s.amplitude)}"

  table = Table(show_header=True, title=title)
  
  max_rows = 1
  for group in data_store.stock_groups:
    stock_count = len(group.stocks)
    if stock_count > max_rows:
      max_rows = stock_count

  for group in data_store.stock_groups:
      table.add_column(group.name, justify="right", no_wrap=True)
      table.add_column("Price", justify="right", no_wrap=True)
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
        row += (stock.name, format_num(stock.price), colorize(stock, stock.amplitude))
    table.add_row(*row)

  return table


# print stocks in console
def print_stocks(live: Live, data_store: DataStore) -> None:
  live.update(build_stocks_table(data_store), refresh=True)