#!/usr/bin/env python3
"""Small, dependency-free market-data client for A-shares, HK, and US equities."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote as urlquote, urlencode
from urllib.request import Request, urlopen

UA = "multi-market-stock-data/0.1 (+https://github.com/ACBBZ/multi-market-stock-data)"
TIMEOUT = 15


class StockDataError(RuntimeError):
    """Raised when a source cannot produce a valid response."""


@dataclass(frozen=True)
class Instrument:
    market: str
    canonical: str
    yahoo: str
    tencent: str | None


def _market_name(market: str | None) -> str | None:
    if market is None:
        return None
    value = market.strip().upper().replace("-", "")
    aliases = {"CN": "A", "ASHARE": "A", "ASHARES": "A", "A股": "A"}
    value = aliases.get(value, value)
    if value not in {"A", "HK", "US"}:
        raise ValueError("market must be A, HK, or US")
    return value


def normalize_symbol(symbol: str, market: str | None = None) -> Instrument:
    """Normalize common symbol spellings without silently changing exchanges."""
    raw = re.sub(r"\s+", "", str(symbol)).upper()
    if not raw:
        raise ValueError("symbol is empty")
    requested = _market_name(market)

    cn_match = re.fullmatch(r"(SH|SZ)(\d{6})", raw) or re.fullmatch(r"(\d{6})\.(SH|SZ)", raw)
    if cn_match:
        if raw.startswith(("SH", "SZ")):
            exchange, code = cn_match.group(1), cn_match.group(2)
        else:
            code, exchange = cn_match.group(1), cn_match.group(2)
        if requested and requested != "A":
            raise ValueError(f"{symbol!r} is an A-share symbol, not {requested}")
        return Instrument("A", f"{code}.{exchange}", f"{code}.{('SS' if exchange == 'SH' else 'SZ')}", exchange.lower() + code)

    if re.fullmatch(r"\d{6}", raw):
        if requested and requested != "A":
            raise ValueError(f"six-digit symbol {symbol!r} requires market A")
        exchange = "SH" if raw[0] in {"6", "9"} else "SZ"
        suffix = "SS" if exchange == "SH" else "SZ"
        return Instrument("A", f"{raw}.{exchange}", f"{raw}.{suffix}", exchange.lower() + raw)

    hk_match = re.fullmatch(r"HK(\d{1,5})", raw) or re.fullmatch(r"(\d{1,5})\.HK", raw)
    if hk_match:
        code = hk_match.group(1).zfill(4)
        if requested and requested != "HK":
            raise ValueError(f"{symbol!r} is a Hong Kong symbol, not {requested}")
        return Instrument("HK", f"{code}.HK", f"{code}.HK", "hk" + code)

    if requested == "HK" and re.fullmatch(r"\d{1,5}", raw):
        code = raw.zfill(4)
        return Instrument("HK", f"{code}.HK", f"{code}.HK", "hk" + code)

    if raw.endswith(".US"):
        raw = raw[:-3]
    if requested and requested != "US":
        raise ValueError(f"{symbol!r} is not a recognized {requested} symbol")
    if not re.fullmatch(r"[A-Z][A-Z0-9.\-]*", raw):
        raise ValueError(f"unsupported symbol format: {symbol!r}")
    return Instrument("US", raw, raw, None)


def _json_get(url: str, params: dict[str, Any] | None = None) -> Any:
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": UA, "Accept": "application/json,*/*"})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            body = response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise StockDataError(f"HTTP request failed: {url}: {exc}") from exc
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StockDataError(f"invalid JSON from {url}") from exc


def _text_get(url: str) -> str:
    request = Request(url, headers={"User-Agent": UA, "Accept": "text/plain,*/*"})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            body = response.read()
            charset = response.headers.get_content_charset() or "gbk"
    except (HTTPError, URLError, TimeoutError) as exc:
        raise StockDataError(f"HTTP request failed: {url}: {exc}") from exc
    return body.decode(charset, errors="replace")


def _number(value: Any) -> float | None:
    if value in (None, "", "-", "--"):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _int_number(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_tencent_payload(text: str) -> list[str]:
    match = re.search(r'="(.*?)";?\s*$', text.strip(), flags=re.S)
    if not match:
        raise StockDataError("Tencent returned no quote payload")
    fields = match.group(1).split("~")
    if len(fields) < 35:
        raise StockDataError("Tencent quote payload is incomplete")
    return fields


def _quote_tencent(inst: Instrument) -> dict[str, Any]:
    if not inst.tencent:
        raise StockDataError("Tencent quote is not used for US equities")
    fields = _parse_tencent_payload(_text_get(f"https://qt.gtimg.cn/q={inst.tencent}"))
    price = _number(fields[3])
    if price is None:
        raise StockDataError(f"Tencent returned no price for {inst.canonical}")
    currency = fields[82] if len(fields) > 82 and fields[82] else ("CNY" if inst.market == "A" else "HKD")
    return {
        "symbol": inst.canonical, "market": inst.market, "name": fields[1], "price": price,
        "previous_close": _number(fields[4]), "open": _number(fields[5]), "high": _number(fields[33]),
        "low": _number(fields[34]), "change": _number(fields[31]), "change_percent": _number(fields[32]),
        "volume": _int_number(fields[6]), "amount": _number(fields[37]), "currency": currency,
        "source": "Tencent Finance", "retrieved_at": _now(),
    }


def _yahoo_chart(inst: Instrument, range_: str = "1y") -> dict[str, Any]:
    data = _json_get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{urlquote(inst.yahoo, safe='.-')}",
        {"range": range_, "interval": "1d", "events": "div,splits"},
    )
    result = (data.get("chart") or {}).get("result")
    if not result:
        error = (data.get("chart") or {}).get("error") or {}
        raise StockDataError(f"Yahoo returned no chart for {inst.canonical}: {error.get('description', error)}")
    return result[0]


def _history_yahoo(inst: Instrument, range_: str, limit: int | None) -> list[dict[str, Any]]:
    result = _yahoo_chart(inst, range_)
    timestamps = result.get("timestamp") or []
    quote_block = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    adjusted = ((result.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose") or []
    rows = []
    for index, timestamp in enumerate(timestamps):
        close = (quote_block.get("close") or [None] * len(timestamps))[index]
        if close is None:
            continue
        rows.append({
            "date": datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat(),
            "open": quote_block.get("open", [None] * len(timestamps))[index],
            "high": quote_block.get("high", [None] * len(timestamps))[index],
            "low": quote_block.get("low", [None] * len(timestamps))[index],
            "close": close, "adj_close": adjusted[index] if index < len(adjusted) else None,
            "volume": quote_block.get("volume", [None] * len(timestamps))[index],
        })
    return rows[-limit:] if limit else rows


def _history_tencent(inst: Instrument, limit: int) -> list[dict[str, Any]]:
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={inst.tencent},day,,,{limit},qfq"
    data = _json_get(url)
    entry = ((data.get("data") or {}).get(inst.tencent or "")) or {}
    raw_rows = entry.get("qfqday") or entry.get("day") or []
    if not raw_rows:
        raise StockDataError(f"Tencent returned no historical rows for {inst.canonical}")
    return [
        {"date": row[0], "open": _number(row[1]), "close": _number(row[2]), "high": _number(row[3]),
         "low": _number(row[4]), "volume": _number(row[5]), "adj_close": _number(row[2])}
        for row in raw_rows if len(row) >= 6
    ]


def _with_indicators(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    closes = [row.get("close") for row in rows]
    for index, row in enumerate(rows):
        for window in (5, 20):
            values = [x for x in closes[max(0, index - window + 1): index + 1] if x is not None]
            row[f"sma{window}"] = round(sum(values) / len(values), 6) if len(values) == window else None
        if index < 14:
            row["rsi14"] = None
            continue
        changes = [closes[j] - closes[j - 1] for j in range(index - 13, index + 1)]
        gains = sum(max(change, 0) for change in changes) / 14
        losses = sum(max(-change, 0) for change in changes) / 14
        row["rsi14"] = round(100 if losses == 0 else 100 - 100 / (1 + gains / losses), 6)
    return rows


def quote(symbol: str, market: str | None = None) -> dict[str, Any]:
    inst = normalize_symbol(symbol, market)
    errors: list[str] = []
    sources: Iterable[str] = ("tencent", "yahoo") if inst.market in {"A", "HK"} else ("yahoo",)
    for source in sources:
        try:
            if source == "tencent":
                return _quote_tencent(inst)
            rows = _history_yahoo(inst, "5d", 5)
            if not rows:
                raise StockDataError("Yahoo returned no usable rows")
            meta = _yahoo_chart(inst, "5d").get("meta") or {}
            last = rows[-1]
            previous = meta.get("previousClose") or (rows[-2]["close"] if len(rows) > 1 else None)
            return {
                "symbol": inst.canonical, "market": inst.market,
                "name": meta.get("longName") or meta.get("shortName") or inst.canonical,
                "price": last["close"], "previous_close": previous, "open": last.get("open"),
                "high": last.get("high"), "low": last.get("low"),
                "change": last["close"] - previous if previous is not None else None,
                "change_percent": (last["close"] / previous - 1) * 100 if previous else None,
                "volume": last.get("volume"), "amount": None, "currency": meta.get("currency"),
                "source": "Yahoo Finance Chart", "retrieved_at": _now(),
            }
        except (StockDataError, ValueError, KeyError, IndexError) as exc:
            errors.append(f"{source}: {exc}")
    raise StockDataError(f"all quote sources failed for {inst.canonical}; {' | '.join(errors)}")


def history(symbol: str, market: str | None = None, limit: int = 30, range_: str = "1y", indicators: bool = True) -> dict[str, Any]:
    if limit < 1 or limit > 5000:
        raise ValueError("limit must be between 1 and 5000")
    inst = normalize_symbol(symbol, market)
    errors: list[str] = []
    sources: Iterable[str] = ("tencent", "yahoo") if inst.market in {"A", "HK"} else ("yahoo",)
    for source in sources:
        try:
            rows = _history_tencent(inst, limit) if source == "tencent" else _history_yahoo(inst, range_, limit)
            if not rows:
                raise StockDataError("source returned no rows")
            if indicators:
                rows = _with_indicators(rows)
            currency = "CNY" if inst.market == "A" else "HKD" if inst.market == "HK" else "USD"
            return {"symbol": inst.canonical, "market": inst.market, "currency": currency,
                    "source": "Tencent Finance" if source == "tencent" else "Yahoo Finance Chart",
                    "retrieved_at": _now(), "rows": rows}
        except (StockDataError, ValueError, KeyError, IndexError) as exc:
            errors.append(f"{source}: {exc}")
    raise StockDataError(f"all history sources failed for {inst.canonical}; {' | '.join(errors)}")


def search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    if not query.strip():
        raise ValueError("query is empty")
    if re.fullmatch(r"\d{6}(?:\.(?:SH|SZ))?", query.strip().upper()):
        inst = normalize_symbol(query)
        return [{"symbol": inst.canonical, "market": inst.market, "yahoo": inst.yahoo}]
    # Eastmoney's global suggest endpoint supports Chinese names, HK codes, and US tickers.
    payload = _json_get("https://searchapi.eastmoney.com/api/suggest/get", {
        "input": query, "type": 14,
        "token": "D43BF722C8E33BDC906FB84D85E3268", "count": limit,
    })
    suggestions = ((payload.get("QuotationCodeTable") or {}).get("Data") or [])
    results = []
    for item in suggestions[:limit]:
        mkt = str(item.get("MktNum", ""))
        classify = str(item.get("Classify", ""))
        if classify == "AStock":
            item_market = "A"
        elif mkt == "116":
            item_market = "HK"
        elif mkt in {"105", "106", "107"}:
            item_market = "US"
        else:
            continue
        results.append({"symbol": item.get("Code"), "name": item.get("Name"), "market": item_market,
                        "exchange": item.get("JYS"), "security_type": item.get("SecurityTypeName")})
    if results:
        return results
    # Keep a secondary path for symbols that Yahoo knows but Eastmoney does not.
    fallback = _json_get("https://query1.finance.yahoo.com/v1/finance/search", {"q": query, "quotesCount": limit, "newsCount": 0})
    return [{"symbol": item.get("symbol"), "name": item.get("longname") or item.get("shortname"),
             "exchange": item.get("exchange"), "quote_type": item.get("quoteType")}
            for item in (fallback.get("quotes") or [])[:limit]]


def _main() -> int:
    parser = argparse.ArgumentParser(description="Fetch A-share, HK, and US stock data as JSON")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("quote", "history"):
        command = sub.add_parser(name)
        command.add_argument("symbol")
        command.add_argument("--market", choices=("A", "HK", "US"))
        if name == "history":
            command.add_argument("--limit", type=int, default=30)
            command.add_argument("--range", dest="range_", default="1y")
            command.add_argument("--no-indicators", action="store_true")
    search_parser = sub.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    try:
        if args.command == "quote":
            output = quote(args.symbol, args.market)
        elif args.command == "history":
            output = history(args.symbol, args.market, args.limit, args.range_, not args.no_indicators)
        else:
            output = search(args.query, args.limit)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (StockDataError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
