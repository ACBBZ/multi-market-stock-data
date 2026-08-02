# Source routing and limitations

## Routing

| Market | Quote/history primary | Fallback | Native symbol forms |
|---|---|---|---|
| A-share | Tencent Finance (`qt.gtimg.cn`, `web.ifzq.gtimg.cn`) | Yahoo Chart (`.SS` / `.SZ`) | `600519`, `600519.SH`, `SH600519`, `000001.SZ` |
| Hong Kong | Tencent Finance (`hk` prefix) | Yahoo Chart (`.HK`) | `00700.HK`, `0700.HK`, `HK00700` |
| US | Yahoo Finance Chart | None | `AAPL`, `BRK.B` |

`stock_data.py` uses the chart endpoint rather than HTML pages. Yahoo Chart currently accepts the public chart request without a crumb for the basic OHLCV path; this can change, so keep the fallback and error reporting intact.

## Returned fields

- `quote`: canonical symbol, market, name, price, previous close, OHLC, change, volume, currency, source, and UTC retrieval time.
- `history`: canonical symbol, market, currency, source, UTC retrieval time, and rows with date/OHLCV. Optional `sma5`, `sma20`, and `rsi14` are calculated locally from returned closes.
- No field is a recommendation, target price, or guarantee of real-time execution quality.

## Compliance and operational notes

- Tencent Finance, Eastmoney, Sina, and Yahoo are public web data sources with terms and rate limits that may change. Use low request volume, identify the source in outputs, and verify current terms before commercial redistribution.
- The reference `global-stock-data` skill correctly treats SEC EDGAR, Treasury, and CFTC as a different compliance tier from Yahoo/CBOE/FINRA. This skill does not silently add those layers.
- Do not use the skill for high-frequency trading, order placement, or scraping large portions of a market.
- Yahoo history is timestamped in UTC before being represented as a calendar date; exchange holidays and weekends can make the newest row older than today.

## Extending the skill

Add a new source only behind a small helper, preserve the normalized output schema, add one smoke test, and document its terms and fallback behavior here. Keep market-specific layers separate instead of making one endpoint handle incompatible symbol formats.
