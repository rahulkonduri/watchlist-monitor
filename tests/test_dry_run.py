import pandas as pd
from monitor.triggers import evaluate

# Synthetic: stock down 10% over last few days
closes = [100] * 20 + [95, 94, 93, 92, 91, 90]
hist = pd.DataFrame({"Close": closes})

cfg = {
    "triggers": {
        "daily_move_pct": 0.1,     # almost any move triggers
        "rsi_oversold": 99,         # RSI never goes this high
        "ma_short": 2,
        "ma_long": 4,
    }
}

result = evaluate("TEST", hist, cfg)
print(f"Price: ${result['price']:.2f}")
print(f"Daily change: {result['change_pct']:+.2f}%")
print(f"RSI(14): {result['rsi']:.1f}")
print(f"MA cross: {result['ma_cross']}")
print(f"\nAlerts ({len(result['alerts'])}):")
for alert in result['alerts']:
    print(f"  - {alert}")
