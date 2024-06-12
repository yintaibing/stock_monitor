import utils

# Stock class
class Stock:
  def __init__(self, code: str) -> None:
    self.code: str = code
    self.name: str = None
    self.price: float = None
    self.last_day_price: float = None
    self.amplitude: float = None

  def __str__(self) -> str:
    return f"{self.name}({self.code}){self.price}元{self.amplitude}%"


# Stock group class
class StockGroup:
  def __init__(self, name: str, stock_codes: list) -> None:
    self.name: str = name
    self.stocks: list = []

    if stock_codes:
      for code in stock_codes:
        if utils.verify_stock_code(code):
          self.stocks.append(Stock(code[-6:]))
        else:
          print(f"bad stock code: {code}, ignore")

  def __str__(self) -> str:
    return f"{self.name}({len(self.stocks)})"
  

# Data store
class DataStore:
  def __init__(self) -> None:
    self.market_open: bool = True
    self.all_stocks: list = None
    self.market_indices: StockGroup = StockGroup("market", None)
    self.stock_groups: list = None

    self.colorize: bool = True
    self.interval_seconds: float = 0
    self.network_latency: float = 0