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
def colorize(data_store: DataStore, stock: Stock, text: any) -> str:
  s = format_num(text) if isinstance(text, float) else str(text)
  if data_store.colorize:
    if stock.price > stock.last_day_price:
      return "[red]" + s + "[/]"
    if stock.price < stock.last_day_price:
      return "[green]" + s + "[/]"
  return s


# build table
def build_stocks_table(data_store: DataStore) -> Table:
  title = "●" if data_store.market_open else "×"
  if data_store.colorize:
    title = f"[red]{title}[/]" if data_store.market_open else f"[green]{title}[/]"

  title += f" 延迟/间隔：{format_num(data_store.network_latency)}s/{data_store.interval_seconds}s\n"
  for s in data_store.market_indices.stocks:
    title += f" {s.name[0]} {colorize(data_store, s, s.amplitude)}"

  table = Table(show_header=True, title=title)
  
  max_rows = 1
  for group in data_store.stock_groups:
    stock_count = len(group.stocks)
    if stock_count > max_rows:
      max_rows = stock_count

  for group in data_store.stock_groups:
      table.add_column(group.name, justify="right", no_wrap=True)
      table.add_column("¥-" if data_store.market_open else "¥", justify="right", no_wrap=True)
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
        name_str = stock.name
        if data_store.market_open:
          if stock.last_price != None and stock.price != stock.last_price:
            # ↑↓▲▼ʌv
            name_str += "ʌ" if stock.price > stock.last_price else "v"
          else:
            name_str += "-"
        row += (name_str, format_num(stock.price), colorize(data_store, stock, stock.amplitude))
    table.add_row(*row)

  return table


# print stocks in console
def print_stocks(live: Live, data_store: DataStore) -> None:
  live.update(build_stocks_table(data_store), refresh=True)