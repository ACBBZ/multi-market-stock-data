#!/usr/bin/env python3
"""Live smoke test for the three supported markets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stock_data import StockDataError, history, quote  # noqa: E402


CASES = [("A-share", "600519", "A"), ("Hong Kong", "00700.HK", None), ("US", "AAPL", "US")]


def main() -> int:
    results = []
    failed = False
    for label, symbol, market in CASES:
        try:
            q = quote(symbol, market)
            h = history(symbol, market, limit=3, indicators=False)
            ok = q.get("price") is not None and len(h.get("rows", [])) > 0
            failed = failed or not ok
            results.append({"market": label, "symbol": q.get("symbol"), "source": q.get("source"), "price": q.get("price"), "history_rows": len(h.get("rows", [])), "latest_date": h["rows"][-1].get("date"), "ok": ok})
        except (StockDataError, ValueError, KeyError, IndexError) as exc:
            failed = True
            results.append({"market": label, "symbol": symbol, "ok": False, "error": str(exc)})
    print(json.dumps({"ok": not failed, "results": results}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
