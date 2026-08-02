<p align="center">
  <a href="README.md">简体中文</a> | <b>English</b>
</p>

<h1 align="center">multi-market-stock-data</h1>

<p align="center">
  <b>Unified market-data skill for A-shares, Hong Kong stocks, and US equities</b><br>
  Symbol normalization · Quotes · Historical OHLCV · Search · SMA/RSI · Zero API keys
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/dependencies-standard%20library-success" alt="Standard library only">
  <img src="https://img.shields.io/badge/markets-A%20%7C%20HK%20%7C%20US-2ea44f" alt="Markets A HK US">
  <img src="https://img.shields.io/badge/auth-zero-success" alt="Zero auth">
</p>

A cross-market stock-data skill for Codex and other AI coding assistants. Inspired by the direct HTTP approach in [a-stock-data](https://github.com/simonlin1212/a-stock-data) and [global-stock-data](https://github.com/simonlin1212/global-stock-data), this repository provides one small, stable interface for core quotes and historical data across mainland China, Hong Kong, and US markets.

> This project distributes data-access code, not market data. Users must follow each source's current terms of service, rate limits, and redistribution restrictions.

## Architecture

```text
Core multi-market data · 5 capability layers
│
├── Symbol layer       600519.SH / 00700.HK / AAPL → canonical symbols
├── Quote layer        Tencent Finance for A/HK · Yahoo Finance Chart for US
├── K-line layer       Daily OHLCV · adjusted A/HK history · Yahoo fallback
├── Technical layer    SMA5 · SMA20 · RSI14 (computed locally, no pandas)
└── Tools layer        Eastmoney global search · Yahoo fallback · smoke tests
```

This repository currently focuses on reusable cross-market market-data functionality. Specialized layers such as research reports, financial statements, fund flow, options, and SEC filings are intentionally not advertised as implemented.

## Quick start

```bash
git clone https://github.com/ACBBZ/multi-market-stock-data.git
cd multi-market-stock-data

# Quotes
python3 scripts/stock_data.py quote 600519 --market A
python3 scripts/stock_data.py quote 00700.HK
python3 scripts/stock_data.py quote AAPL --market US

# Last 30 daily bars with SMA5/SMA20/RSI14
python3 scripts/stock_data.py history 600519.SH --limit 30

# Search Chinese names, HK symbols, or US tickers
python3 scripts/stock_data.py search "Tencent" --limit 5

# Validate all three markets
python3 scripts/test_sources.py
```

No `akshare`, `pandas`, or API key is required. The implementation uses only the Python standard library; network access to public data endpoints is required.

## Capabilities

| Capability | Command | Returned data |
|---|---|---|
| Live or near-live quote | `quote SYMBOL` | Price, previous close, OHLC, change, volume, currency, source, UTC retrieval time |
| Historical K-line | `history SYMBOL` | Date, Open, High, Low, Close, Adj Close, Volume |
| Local technical indicators | `history SYMBOL` | `sma5`, `sma20`, `rsi14` |
| Stock search | `search QUERY` | Symbol, name, market, exchange, security type |
| Data validation | `scripts/test_sources.py` | Quote, history row count, latest date, and pass status for all markets |

Every command emits JSON for direct use by Codex, shell scripts, or other programs.

## Symbol formats

| Market | Accepted forms | Canonical result |
|---|---|---|
| A-shares | `600519`, `600519.SH`, `SH600519` | `600519.SH` |
| A-shares | `000001.SZ`, `--market A` | `000001.SZ` |
| Hong Kong | `00700.HK`, `0700.HK`, `HK00700` | `00700.HK` |
| US | `AAPL`, `BRK.B`, `--market US` | Native Yahoo ticker |

Six-digit A-share codes are inferred from their leading digits. For indices or other ambiguous codes, provide `.SH` / `.SZ` or `--market A` explicitly. If the market argument conflicts with a symbol suffix, the program raises an error instead of silently changing the instrument.

## Sources and fallback

| Market | Primary source | Fallback | Notes |
|---|---|---|---|
| A-shares | Tencent Finance | Yahoo Chart (`.SS` / `.SZ`) | Daily history uses the adjusted endpoint |
| Hong Kong | Tencent Finance | Yahoo Chart (`.HK`) | Codes are padded to four digits |
| US | Yahoo Finance Chart | — | Basic daily quotes and history |
| Search | Eastmoney global search | Yahoo Finance Search | Chinese names, HK symbols, and US tickers |

The client chooses the primary source by market. If it fails, it follows the documented fallback once and preserves the normalized symbol and failed source in the error message.

## Python API

```python
from scripts.stock_data import history, normalize_symbol, quote, search

print(normalize_symbol("HK700"))
print(quote("600519", market="A"))
bars = history("AAPL", market="US", limit=20)
print(bars["rows"][-1])
print(search("Tencent", limit=5))
```

## Compliance and limitations

- Tencent Finance, Eastmoney, and Yahoo Finance are public web data sources, but their terms, rate limits, and data delays may change. Verify current terms before commercial use or redistribution.
- Keep request volume low. Do not use this project for high-frequency trading, order execution, or large-scale scraping.
- Yahoo timestamps are converted from UTC to calendar dates; weekends, holidays, or source delays can make the newest date older than today.
- Results are data-access outputs, not investment advice, valuation conclusions, or trading signals.
- If adding research reports, fundamentals, fund flow, options, or SEC filing layers, use separate source adapters, normalized schemas, and dedicated tests. Do not promise unsupported capabilities.

See [`references/sources.md`](references/sources.md) for routing, fields, and extension notes. See [`SKILL.md`](SKILL.md) for Codex activation and usage rules.

## Reference projects

- [a-stock-data](https://github.com/simonlin1212/a-stock-data): reference for multi-source A-share data and fallback strategies.
- [global-stock-data](https://github.com/simonlin1212/global-stock-data): reference for Hong Kong/US data-source layering and compliance notes.

## Disclaimer

This project provides public-data access tools only. It is not investment, trading, legal, or compliance advice. Market data may be delayed, incomplete, or revised by the source.
