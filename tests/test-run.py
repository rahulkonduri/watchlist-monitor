import pandas as pd
from monitor.triggers import evaluate

# Synthetic: stock up 10% + oversold RSI conditions
closes = [100] * 20 + [95, 94, 93, 92, 91, 90]  # 10% drop
hist = pd.DataFrame({"Close": closes})

cfg = {
    "triggers": {
        "daily_move_pct": 5.0,
        "rsi_oversold": 35,
        "ma_short": 2,
        "ma_long": 4,
    }
}

result = evaluate("TEST", hist, cfg)
print(f"Alerts: {result['alerts']}")