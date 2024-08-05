import utils

# Stock class
class Stock:
  def __init__(self, code: str) -> None:
    self.code: str = code
    self.name: str = None
    self.price: float = None # 最新价
    self.last_price: float = None # 最新价前的上一次价格
    self.last_day_price: float = None # 昨收
    self.init_price: float = None # 今开
    self.amplitude: float = None # 涨跌幅
    self.buys = None # 买盘
    self.sells = None # 卖盘

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
    self.show_trading_stock: Stock | None = None

    self.colorize: bool = True
    self.interval_seconds: float = 0
    self.price_arrow_up: str = None
    self.price_arrow_down: str = None
    self.seconds_to_market_open: int = 0
    self.network_latency: float = 0
    
    self.is_updated_for_gui: bool = False


# GUI theme, default is light theme
class Theme:
  def __init__(self) -> None:
    self.bg_color: str = "#ddd"
    self.font_color: str = "#000"
    self.red: str = "#f00"
    self.green: str = "#0f0"