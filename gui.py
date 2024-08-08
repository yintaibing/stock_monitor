import os
from threading import Thread
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageFile, ImageTk

from models import *
from parse import get_stock_chart_image
from utils import *

_cfg: dict = None
_font = ("宋体", 10)
_theme_list: list = []
_theme: Theme | None = None
gui_data_store: DataStore | None = None

_root: tk.Tk = None
_x: int = 0
_y: int = 0
_transparent_mode = False
_topmost_mode = False

CHART_TYPES = [("分时", "min"), ("日K", "daily"), ("周K", "weekly"), ("月K", "monthly"), ("关闭", "close")]
_chart_type = "close"
_chart_loading = False
_chart_result = None


def _destroy_window() -> None:
  if _root:
    _root.destroy()
  os._exit(os.EX_OK)


def _drag_start(event: tk.Event) -> None:
  global _x, _y
  _x = event.x
  _y = event.y


def _drag_move(event: tk.Event) -> None:
  global _root, _x, _y
  x = _root.winfo_x() + event.x - _x
  y = _root.winfo_y() + event.y - _y
  _root.geometry(f"+{x}+{y}")


def _drag_release(event: tk.Event) -> None:
  global _x, _y
  _x = None
  _y = None


def _switch_transparent(event: tk.Event) -> None:
  global _cfg, _theme, _root, _transparent_mode
  _transparent_mode = not _transparent_mode
  # 窗口边框
  _root.overrideredirect(1 if _transparent_mode else 0) 
  # 透明背景
  _root.wm_attributes("-transparentcolor", _theme.bg_color if _transparent_mode else "")


def _switch_topmost(event: tk.Event) -> None:
  global _root, _topmost_mode
  _topmost_mode = not _topmost_mode
  # 窗口置顶
  _root.wm_attributes("-topmost", _topmost_mode)
  event.widget.configure(text="已置顶 |" if _topmost_mode else "窗口置顶 |")


def _fill_theme(t: Theme, current: dict) -> None:
  t.bg_color = current["bg_color"] if current.get("bg_color") else t.bg_color
  t.font_color = current["font_color"] if current.get("font_color") else t.font_color
  t.red = current["red"] if current.get("red") else t.red
  t.green = current["green"] if current.get("green") else t.green


def _parse_theme_list() -> None:
  global _cfg, _theme_list, _theme
  cur_theme_name = _cfg.get("gui_theme")
  list: dict = _cfg.get("gui_theme_list")
  for i, (k, v) in enumerate(list.items()):
    t = Theme()
    _fill_theme(t, v)
    _theme_list.append(t)
    if k == cur_theme_name:
      _theme = t
  if not _theme:
    _theme = Theme()


def _switch_theme(event: tk.Event) -> None:
  global _theme_list, _theme, _root
  if len(_theme_list) < 2:
    return
  i = _theme_list.index(_theme)
  if i < 0:
    return
  i = i + 1 if i < len(_theme_list) - 1 else 0
  _theme = _theme_list[i]

  _root.config(bg=_theme.bg_color)
  _apply_theme(_theme, _root)

  global _transparent_mode
  _root.wm_attributes("-transparentcolor", _theme.bg_color if _transparent_mode else "")


def _apply_theme(theme: Theme, widget: tk.Widget) -> None:
  if widget.children is None or len(widget.children) == 0:
    return
  for i, (name, child) in enumerate(widget.children.items()):
    if name == "frame_btns":
      continue
    if isinstance(child, tk.Frame):
      child.config(bg=theme.bg_color)
      _apply_theme(theme, child)
    elif isinstance(child, tk.Label):
      child.config(bg=theme.bg_color, fg=theme.font_color)


def _colorize(data_store: DataStore, stock: Stock) -> str:
  global _theme
  if data_store.colorize:
    if stock.price > stock.last_day_price:
      return _theme.red
    if stock.price < stock.last_day_price:
      return _theme.green
  return _theme.font_color


def _set_label_underline(label: tk.Label, underline: bool) -> None:
  global _font
  f = tkfont.Font(label, _font)
  f.configure(underline=underline)
  label.configure(font=f)


def _create_market_indices_grids(frame: tk.Frame, data_store: DataStore) -> None:
  global _font, _theme
  for i in range(0, len(data_store.market_indices.stocks)):
    s: Stock = data_store.market_indices.stocks[i]
    label = tk.Label(frame, name=s.code, text=s.code, 
                     bg=_theme.bg_color, fg=_theme.font_color, font=_font)
    label.grid(row=0, column=i)


def _create_stock_groups_grids(frame: tk.Frame, data_store: DataStore) -> None:
  global _font, _theme
  appear_count = dict()
  for i in range(0, len(data_store.stock_groups)):
    col_name = i * 3

    group: StockGroup = data_store.stock_groups[i]
    label_group_name = tk.Label(frame, text=group.name, 
                                bg=_theme.bg_color, fg=_theme.font_color, font=_font)
    label_group_name.grid(row=0, column=col_name)
    label_group_price = tk.Label(frame, text="¥", 
                                 bg=_theme.bg_color, fg=_theme.font_color, font=_font)
    label_group_price.grid(row=0, column=col_name + 1)
    label_group_amp = tk.Label(frame, text="%", 
                               bg=_theme.bg_color, fg=_theme.font_color, font=_font)
    label_group_amp.grid(row=0, column=col_name + 2)
    
    for j in range(0, len(group.stocks)):
      s: Stock = group.stocks[j]
      # if stock appears 2 times or more, name the label with numbers
      count: int = appear_count.get(s.code, 0)
      label_stock_name = tk.Label(frame, name=f"{s.code}name{count}", text=s.code, 
                                  bg=_theme.bg_color, fg=_theme.font_color, font=_font)
      label_stock_name.grid(row=j + 1, column=col_name, sticky="e")
      label_stock_name.bind("<Button-1>", _switch_trading)
      label_price = tk.Label(frame, name=f"{s.code}price{count}", text="-", 
                             bg=_theme.bg_color, fg=_theme.font_color, font=_font)
      label_price.grid(row=j + 1, column=col_name + 1, sticky="e")
      label_price.bind("<Button-1>", _switch_trading)
      label_amp = tk.Label(frame, name=f"{s.code}amp{count}", text="-", 
                           bg=_theme.bg_color, fg=_theme.font_color, font=_font)
      label_amp.grid(row=j + 1, column=col_name + 2, sticky="e")
      label_amp.bind("<Button-1>", _switch_trading)
      appear_count[s.code] = count + 1


def _set_stock_name_label_underline(stock: Stock, underline: bool) -> None:
  global _root
  frame_stock_groups: tk.Frame = _root.children["frame_stock_groups"]
  for i, (name, label_stock_name) in enumerate(frame_stock_groups.children.items()):
    if name.startswith(stock.code):
      _set_label_underline(label_stock_name, underline)
      return


def _switch_trading(event: tk.Event) -> None:
  global _font, _theme, _root, gui_data_store, _chart_type, _chart_loading, _chart_result
  if not gui_data_store:
    return
  widget_full_name = str(event.widget)
  stock_code = widget_full_name.split(".")[-1][0:6]
  stock: Stock | None = None
  for s in gui_data_store.all_stocks:
    if s.code == stock_code:
      stock = s
      break
  if not stock:
    return
  
  frame_trading: tk.Frame | None = _root.children.get("frame_trading")
  label_chart_image: tk.Label | None = _root.children.get("label_chart_image")
  if stock == gui_data_store.show_trading_stock:
    # showing this stock, destroy the trading frame
    gui_data_store.show_trading_stock = None
    _set_stock_name_label_underline(stock, False)
    if frame_trading:
      frame_trading.destroy()
    if label_chart_image:
      _chart_type = "close"
      _chart_loading = False
      _chart_result = None
      label_chart_image.image = None
      label_chart_image.destroy()
    
  elif frame_trading or label_chart_image:
    # showing other stock, switch to this stock
    if _chart_loading:
      return
    if gui_data_store.show_trading_stock:
      _set_stock_name_label_underline(gui_data_store.show_trading_stock, False)
    gui_data_store.show_trading_stock = stock
    _set_stock_name_label_underline(gui_data_store.show_trading_stock, True)
    if frame_trading:
      _update_trading_frame(frame_trading, stock)
    if _chart_type != "close":
      _start_load_chart_image()

  else:
    # not showing any stock, show the trading frame
    gui_data_store.show_trading_stock = stock
    _set_stock_name_label_underline(gui_data_store.show_trading_stock, True)
    frame_trading = tk.Frame(_root, name="frame_trading")
    frame_trading.configure(bg=_theme.bg_color)
    for i in range(0, 2):
      for j in range(0, 7):
        label = tk.Label(frame_trading, name=f"label_trading{i}{j}",
                         bg=_theme.bg_color, fg=_theme.font_color, font=_font,
                         justify="left", padx=4)
        label.grid(row=i, column=j)
    # chart type btns
    global CHART_TYPES
    for i, (text, chart_type) in enumerate(CHART_TYPES):
      label = tk.Label(frame_trading, name=f"label_chart_{chart_type}", 
                       bg="#e0e0e0", fg="#000", font=_font, text=text)
      label.bind("<Button-1>", _click_chart_type)
      if i == len(CHART_TYPES) - 1:
        _set_label_underline(label, True)
      label.grid(row=2, column=i + 1)
    frame_trading.pack()
    _update_trading_frame(frame_trading, stock)


def _update_trading_frame(frame_trading: tk.Frame, s: Stock) -> None:
  global gui_data_store
  label: tk.Label = frame_trading.children["label_trading00"]
  label.configure(text=f"昨收\n{fraction_2(s.last_day_price)} #")
  label = frame_trading.children["label_trading10"]
  label.configure(text=f"{fraction_2(s.init_price)} #\n今开", fg=_colorize(gui_data_store, s))
  for i in range(0, 5):
    j = i * 2
    # sells
    label = frame_trading.children[f"label_trading0{i + 1}"]
    label.configure(text=f"{s.sells[j + 1]}\n{s.sells[j]}" if s.sells else "-\n-")
    # buys
    label = frame_trading.children[f"label_trading1{i + 1}"]
    label.configure(text=f"{s.buys[j]}\n{s.buys[j + 1]}" if s.buys else "-\n-")


def _set_chart_type_label_underline() -> None:
  global _root, CHART_TYPES, _chart_type
  frame_trading: tk.Frame | None = _root.children.get("frame_trading")
  if frame_trading:
    for chart_type in CHART_TYPES:
      label = frame_trading.children[f"label_chart_{chart_type[1]}"]
      _set_label_underline(label, chart_type[1] == _chart_type)


def _click_chart_type(event: tk.Event) -> None:
  global gui_data_store, _root, _chart_type, _chart_loading, _chart_result
  if not gui_data_store:
    return
  widget_full_name = str(event.widget)
  chart_type = widget_full_name.split("_")[-1]
  if chart_type == "close":
    _chart_type = chart_type
    _chart_loading = False
    _chart_result = None
    _set_chart_type_label_underline()
    label_chart_image: tk.Label | None = _root.children.get("label_chart_image")
    if label_chart_image:
      label_chart_image.image = None
      label_chart_image.destroy()
  elif chart_type == _chart_type:
    _refresh_chart(None)
  elif not _chart_loading:
    _chart_type = chart_type
    _set_chart_type_label_underline()
    _start_load_chart_image()


def _start_load_chart_image() -> None:
  global _root, _chart_loading
  label_chart_image: tk.Label | None = _root.children.get("label_chart_image")
  if label_chart_image:
    label_chart_image.image = None
    label_chart_image.configure(text="Chart Loading", image="")
  else:
    label_chart_image = tk.Label(_root, name="label_chart_image", text="Chart Loading",
                                 bg=_theme.bg_color, fg=_theme.font_color, font=_font)
    label_chart_image.bind("<Button-1>", _refresh_chart)
    label_chart_image.pack()
  global _chart_loading
  _chart_loading = True
  _root.after(100, _listen_chart_loading)
  Thread(target=_load_chart_image).start()


def _refresh_chart(event: tk.Event | None) -> None:
  global _chart_loading
  if not _chart_loading:
    _start_load_chart_image()

  
def _load_chart_image() -> None:
  global _cfg, gui_data_store, _chart_type, _chart_result
  image: ImageFile.ImageFile | None = None
  failure_count = 0
  while failure_count < 4 and gui_data_store.show_trading_stock and _chart_type != "close":
    image = get_stock_chart_image(gui_data_store.show_trading_stock, _chart_type, _cfg["proxy"])
    if not (gui_data_store.show_trading_stock and _chart_type != "close"):
      return
    if image:
      _chart_result = image
      return
    else:
      failure_count += 1
  _chart_result = "Chart Load Failed"


def _listen_chart_loading() -> None:
  # label of chart image
  global _root, _chart_loading, _chart_result
  label_chart_image: tk.Label | None = _root.children.get("label_chart_image")
  if label_chart_image:
    if _chart_result:
      if isinstance(_chart_result, Image.Image) or isinstance(_chart_result, ImageFile.ImageFile):
        pil_image = ImageTk.PhotoImage(image=_chart_result)
        label_chart_image.configure(text=None, image=pil_image)
        label_chart_image.image = pil_image # save a reference of the image to avoid garbage collection
      else:
        label_chart_image.configure(text=str(_chart_result), image="")
      _chart_loading = False
      _chart_result = None
    else:
      _root.after(100, _listen_chart_loading)


def _listen_loop() -> None:
  global _root, gui_data_store
  if gui_data_store and gui_data_store.is_updated_for_gui:
    # label of market status
    label_market_status: tk.Label = _root.children["label_market_status"]
    str_market_status: str
    if gui_data_store.seconds_to_market_open > 0:
      str_market_status = f"距开市：{seconds_to_hms(gui_data_store.seconds_to_market_open)}"
    elif gui_data_store.market_open:
      str_market_status = "●"
    else:
      str_market_status = "×"
    str_market_status += " 延迟/间隔："
    str_market_status += f"{fraction_2(gui_data_store.network_latency)}s/{gui_data_store.interval_seconds}s"
    label_market_status.configure(text=str_market_status)

    # frame of market indices
    # market indices, print sh000001 value and amplitude
    # market indices must be colorized
    value_colorize = gui_data_store.colorize
    gui_data_store.colorize = True
    frame_market_indices: tk.Frame = _root.children["frame_market_indices"]
    for s in gui_data_store.market_indices.stocks:
      label: tk.Label = frame_market_indices.children.get(s.code)
      if label:
        text = f"{s.name[0]} {fraction_2(s.amplitude)}"
        if s.code == "sh000001":
          text = f"{s.name[0]} {fraction_2(s.amplitude)} {fraction_2(s.price)}"
        label.configure(text=text, fg=_colorize(gui_data_store, s))
    gui_data_store.colorize = value_colorize

    # frame of stock groups
    frame_stock_groups: tk.Frame = _root.children["frame_stock_groups"]
    for group in gui_data_store.stock_groups:
      for s in group.stocks:
        count = 0
        while True:
          label_name: tk.Label | None = frame_stock_groups.children.get(f"{s.code}name{count}")
          if not label_name:
            break
          str_name = s.name
          if gui_data_store.market_open and gui_data_store.price_arrow_up != None:
            str_name += " "
            if s.last_price != None and s.price != s.last_price:
              str_name += gui_data_store.price_arrow_up if s.price > s.last_price else gui_data_store.price_arrow_down
            else:
              str_name += "-"
          label_name.configure(text=str_name)
          label_price: tk.Label = frame_stock_groups.children[f"{s.code}price{count}"]
          label_price.configure(text=fraction_2(s.price))
          label_amp: tk.Label = frame_stock_groups.children[f"{s.code}amp{count}"]
          label_amp.configure(text=fraction_2(s.amplitude), fg=_colorize(gui_data_store, s))
          count += 1

    # frame of trading
    frame_trading: tk.Frame | None = _root.children.get("frame_trading")
    if frame_trading and gui_data_store.show_trading_stock:
      _update_trading_frame(frame_trading, gui_data_store.show_trading_stock)

    # clear old data, and wait for new data in the next loop
    if gui_data_store.market_open or gui_data_store.seconds_to_market_open >= 0:
      gui_data_store.is_updated_for_gui = False
  
  if not (gui_data_store and gui_data_store.is_updated_for_gui):
    _root.after(200, _listen_loop)


def create_window(cfg: dict, local: dict, data_store: DataStore) -> None:
  global _cfg, _theme, _font, _root
  _cfg = cfg
  _font = (_font[0], int(cfg["gui_font_size"]))
  _parse_theme_list()

  _root = tk.Tk()
  _root.resizable(False, False)
  _root.config(bg=_theme.bg_color)
  _root.protocol("WM_DELETE_WINDOW", _destroy_window)

  frame_btns = tk.Frame(_root, name="frame_btns")
  frame_btns.config(bg=_theme.bg_color)
  btns_attrs = {
    "按住拖动": (_drag_start, _drag_move, _drag_release),
    "窗口透明": _switch_transparent,
    "窗口置顶": _switch_topmost,
    "切换颜色": _switch_theme
  }.items()
  len_btns_attrs = len(btns_attrs)
  for i, (name, func) in enumerate(btns_attrs):
    label: tk.Label = tk.Label(frame_btns, bg="#e0e0e0", fg="#000", font=_font, 
                               text=f"{name} |" if i < len_btns_attrs - 1 else name)
    if isinstance(func, tuple):
      label.bind("<ButtonPress-1>", func[0])
      label.bind("<B1-Motion>", func[1])
      label.bind("<ButtonRelease-1>", func[2])
    else:
      label.bind("<Button-1>", func)
    label.grid(row=0, column=i)
  frame_btns.pack()

  # label of market status
  label_market_status = tk.Label(_root, name="label_market_status", text="loading",
                                 bg=_theme.bg_color, fg=_theme.font_color, font=_font)
  label_market_status.pack()

  # frame of market indices
  frame_market_indices = tk.Frame(_root, name="frame_market_indices")
  frame_market_indices.config(bg=_theme.bg_color)
  _create_market_indices_grids(frame_market_indices, data_store)
  frame_market_indices.pack()

  # frame of stock groups
  frame_stock_groups = tk.Frame(_root, name="frame_stock_groups")
  frame_stock_groups.config(bg=_theme.bg_color)
  _create_stock_groups_grids(frame_stock_groups, data_store)
  frame_stock_groups.pack()

  _root.after(200, _listen_loop)
  _root.mainloop()


def set_gui_data_store(data_store: DataStore) -> None:
  data_store.is_updated_for_gui = True
  global gui_data_store
  gui_data_store = data_store
