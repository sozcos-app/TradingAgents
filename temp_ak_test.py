import akshare as ak
import pandas as pd

# 1. 社融 - 看看 macro_china_shrzgm 返回什么日期格式
print("=== macro_china_shrzgm ===")
try:
    df = ak.macro_china_shrzgm()
    print("Columns:", list(df.columns))
    print(df.head(3).to_string())
except Exception as e:
    print(f"Error: {e}")

print()

# 2. DR007 - 看看 rate_interbank 参数
print("=== rate_interbank ===")
try:
    import inspect
    sig = inspect.signature(ak.rate_interbank)
    print("Signature:", sig)
except Exception as e:
    print(f"Error: {e}")

# Try without args
try:
    df = ak.rate_interbank()
    print("Columns:", list(df.columns))
    print(df.head(2).to_string())
except Exception as e:
    print(f"No-arg Error: {e}")

print()

# 3. 汇率 - 找替代
print("=== currency functions ===")
funcs = [f for f in dir(ak) if 'currency' in f.lower()]
print("Currency funcs:", funcs)

# Try currency_boc_safe or similar
for func_name in funcs:
    print(f"\n--- {func_name} ---")
    try:
        func = getattr(ak, func_name)
        sig = inspect.signature(func)
        print(f"  Signature: {sig}")
    except Exception as e:
        print(f"  Error: {e}")

print()

# 4. 北向资金 - 找替代
print("=== northbound functions ===")
funcs = [f for f in dir(ak) if 'hsgt' in f.lower() or 'north' in f.lower()]
print("Hsgt/north funcs:", funcs)

# Try stock_hsgt_north_net_flow_in_em
for func_name in funcs[:5]:
    print(f"\n--- {func_name} ---")
    try:
        func = getattr(ak, func_name)
        sig = inspect.signature(func)
        print(f"  Signature: {sig}")
    except Exception as e:
        print(f"  Error: {e}")
