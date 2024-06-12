import re

stock_code_pattern = re.compile(r'^(300[\d]{3}|688[\d]{3}|60[\d]{4}|00[\d]{4}|8[\d]{5})$')

# verify stock code is valid or not
def verify_stock_code(stock_code: str, is_market_index: bool = False) -> bool:
  if is_market_index:
    return len(stock_code) == 8
  if len(stock_code) == 8:
    if stock_code.startswith("sh") or stock_code.startswith("sz") or stock_code.startswith("bj"):
      return verify_stock_code(stock_code[2:])
    else:
      return False
  if len(stock_code) == 6:
    return stock_code_pattern.match(stock_code)
  return False

# add sh/sz prefix to stock code
def add_sh_sz_prefix(stock_code: str) -> str:
  if stock_code.startswith("6"):
    return "sh" + stock_code
  elif stock_code.startswith("0") or stock_code.startswith("3"):
    return "sz" + stock_code
  elif stock_code.startswith("8"):
    return "bj" + stock_code
  return stock_code