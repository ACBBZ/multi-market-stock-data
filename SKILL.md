---
name: multi-market-stock-data
description: Fetch and validate public market data for mainland China A-shares, Hong Kong stocks, and US equities. Use when Codex needs cross-market quotes, historical OHLCV data, symbol normalization, stock search, or lightweight technical indicators, especially for requests mentioning A股、港股、美股、行情、K线、历史价格、股票搜索 or market-data validation.
---

# Multi-market stock data

## Overview

Use the bundled `scripts/stock_data.py` command-line tool or import its functions to fetch normalized quote and historical data across A-shares, Hong Kong stocks, and US equities. The tool uses the same direct-HTTP style as the reference `a-stock-data` and `global-stock-data` skills, but keeps the initial interface small and deterministic.

## Operating rules

- Normalize the symbol before making a request. Do not silently guess when an explicit exchange suffix or market argument conflicts with the code.
- Prefer Tencent's public quote/K-line endpoints for A-shares and Hong Kong stocks; prefer Yahoo Finance Chart for US equities and as a fallback for other markets.
- Treat returned timestamps and prices as source data, not investment advice. Report the source, retrieval time, currency, and whether the result is delayed or historical.
- Keep request volume low and sequential. Cache nothing by default, do not scrape HTML pages, and do not add API keys to the skill.
- If a source returns an empty result, distinguish “no data for this symbol/date” from a transport or parsing error. Surface the error rather than fabricating a result.
- For requests needing filings, options, fund flow, or exchange-specific fundamentals, read `references/sources.md` and extend the script only when the user explicitly asks for that layer.

## Quick workflow

1. Choose the market explicitly when the symbol is ambiguous.
2. Run the bundled script with `quote`, `history`, or `search`.
3. Inspect `source`, `currency`, `retrieved_at`, row count, and the newest timestamp before interpreting the data.
4. For cross-market comparisons, preserve each market's native currency and timezone; convert only when the user requests it.

Examples:

```bash
python3 /Users/tom/.codex/skills/multi-market-stock-data/scripts/stock_data.py quote 600519 --market A
python3 /Users/tom/.codex/skills/multi-market-stock-data/scripts/stock_data.py quote 00700.HK
python3 /Users/tom/.codex/skills/multi-market-stock-data/scripts/stock_data.py quote AAPL --market US
python3 /Users/tom/.codex/skills/multi-market-stock-data/scripts/stock_data.py history 600519.SH --limit 30
python3 /Users/tom/.codex/skills/multi-market-stock-data/scripts/stock_data.py search "腾讯"
```

The command prints JSON so it can be consumed directly by Codex or another program. Library entry points are `normalize_symbol`, `quote`, `history`, and `search`.

## Symbol conventions

- A-shares: `600519`, `600519.SH`, `SH600519`, `000001.SZ`, or `--market A`. Six-digit codes without a suffix are inferred from the leading digits; pass the exchange for ambiguous indices.
- Hong Kong: `00700.HK`, `0700.HK`, `HK00700`, or `--market HK`. The canonical Yahoo form is four-digit padded plus `.HK`.
- US: `AAPL`, `BRK.B`, or `--market US`. Symbols are sent to Yahoo in their native form.

## Validation checklist

- Verify that the response is non-empty and has a matching canonical symbol.
- Verify that quote data has a numeric price and that historical rows have dates and close values.
- Check that the latest historical date is plausible for the source's exchange timezone; weekends and holidays can legitimately produce an older date.
- When a request fails, retry through the documented fallback once, then return the source error and the normalized symbol.

## Bundled resources

### `scripts/stock_data.py`

Core implementation and CLI. It uses Python's standard library only.

### `scripts/test_sources.py`

Live smoke test for one representative A-share, Hong Kong stock, and US equity. Run it after changing endpoint logic or when the user asks whether acquisition is working.

### `references/sources.md`

Source routing, symbol mappings, known limitations, and compliance notes.
