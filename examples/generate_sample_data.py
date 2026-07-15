from pathlib import Path
from datetime import date, timedelta
import csv, math, random

random.seed(7)
folder = Path("./sample_data")
folder.mkdir(exist_ok=True)

for symbol, drift, shock in [("TURN", 0.003, 0.018), ("TREND", 0.006, 0.010), ("WEAK", -0.002, 0.020)]:
    rows = []
    p = 10.0
    d = date(2026, 1, 1)
    for i in range(100):
        p = max(1, p * (1 + drift + random.gauss(0, shock)))
        vol = 100000 * (1 + random.random())
        if i > 85 and symbol == "TURN":
            p *= 1.008
            vol *= 2
        rows.append({
            "date": (d + timedelta(days=i)).isoformat(),
            "open": round(p * 0.99, 4),
            "high": round(p * 1.02, 4),
            "low": round(p * 0.98, 4),
            "close": round(p, 4),
            "volume": int(vol),
        })
    with (folder / f"{symbol}.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
print(folder)
