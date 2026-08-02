<p align="center">
  <b>简体中文</b> | <a href="README_en.md">English</a>
</p>

<h1 align="center">multi-market-stock-data</h1>

<p align="center">
  <b>A 股 · 港股 · 美股统一行情技能</b><br>
  统一代码规范 · 报价 · 历史 OHLCV · 股票搜索 · SMA/RSI · 零 API Key
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/dependencies-standard%20library-success" alt="Standard library only">
  <img src="https://img.shields.io/badge/markets-A%20%7C%20HK%20%7C%20US-2ea44f" alt="Markets A HK US">
  <img src="https://img.shields.io/badge/auth-zero-success" alt="Zero auth">
</p>

一个面向 Codex 和其他 AI 编程助手的跨市场股票数据 Skill。它参考 [a-stock-data](https://github.com/simonlin1212/a-stock-data) 与 [global-stock-data](https://github.com/simonlin1212/global-stock-data) 的直接 HTTP 取数方式，把 A 股、港股、美股的核心行情能力收敛到一个小而稳定的接口。

> 本项目分发的是数据访问代码，不分发市场数据。数据使用必须遵守各来源当前的服务条款、访问频率和再分发限制。

## 架构

```text
三市场核心行情 · 5 个能力层
│
├── 代码层       600519.SH / 00700.HK / AAPL → 统一 canonical symbol
├── 行情层       A 股/港股 Tencent Finance · 美股 Yahoo Finance Chart
├── K 线层       日线 OHLCV · A 股/港股前复权 · Yahoo fallback
├── 技术指标层   SMA5 · SMA20 · RSI14（本地计算，不依赖 pandas）
└── 工具层       东财全球搜索 · Yahoo 搜索 fallback · 三市场冒烟测试
```

与参考项目相比，本仓库当前聚焦可复用的跨市场基础能力；研报、财报、资金流、期权、SEC Filing 等专属层暂不宣称已实现。

## 快速开始

```bash
git clone https://github.com/ACBBZ/multi-market-stock-data.git
cd multi-market-stock-data

# 报价
python3 scripts/stock_data.py quote 600519 --market A
python3 scripts/stock_data.py quote 00700.HK
python3 scripts/stock_data.py quote AAPL --market US

# 最近 30 条日线，附 SMA5/SMA20/RSI14
python3 scripts/stock_data.py history 600519.SH --limit 30

# 搜索中文名、港股代码或美股代码
python3 scripts/stock_data.py search "腾讯" --limit 5

# 验证 A 股、港股、美股均可正常取数
python3 scripts/test_sources.py
```

不需要安装 `akshare`、`pandas` 或 API Key。实现仅使用 Python 标准库；网络请求需要访问公开数据端点。

## 能力清单

| 能力 | 命令 | 返回内容 |
|---|---|---|
| 实时/近实时报价 | `quote SYMBOL` | 价格、昨收、开高低、涨跌、成交量、币种、来源、UTC 获取时间 |
| 历史 K 线 | `history SYMBOL` | 日期、Open、High、Low、Close、Adj Close、Volume |
| 本地技术指标 | `history SYMBOL` | `sma5`、`sma20`、`rsi14` |
| 股票搜索 | `search QUERY` | 代码、名称、市场、交易所、证券类型 |
| 数据验证 | `scripts/test_sources.py` | 三市场报价、历史行数、最新日期与通过状态 |

所有命令输出 JSON，适合 Codex、Shell 或其他程序继续处理。

## 代码格式

| 市场 | 支持写法 | 规范化结果 |
|---|---|---|
| A 股 | `600519`、`600519.SH`、`SH600519` | `600519.SH` |
| A 股 | `000001.SZ`、`--market A` | `000001.SZ` |
| 港股 | `00700.HK`、`0700.HK`、`HK00700` | `00700.HK` |
| 美股 | `AAPL`、`BRK.B`、`--market US` | 原始 Yahoo ticker |

六位 A 股代码会按首位数字推断沪深市场；指数或其他有歧义的代码应显式传入 `.SH` / `.SZ` 或 `--market A`。市场参数与代码后缀冲突时，程序会报错，不会静默切换标的。

## 数据源与降级

| 市场 | 主源 | 备用源 | 备注 |
|---|---|---|---|
| A 股 | Tencent Finance | Yahoo Chart（`.SS` / `.SZ`） | 日线使用前复权接口 |
| 港股 | Tencent Finance | Yahoo Chart（`.HK`） | 代码自动补齐四位 |
| 美股 | Yahoo Finance Chart | — | 基础日线与报价 |
| 搜索 | Eastmoney 全球搜索 | Yahoo Finance Search | 支持中文名、港股与美股代码 |

程序会按市场选择主源；主源失败时最多按文档路径降级一次，并在错误中保留规范化代码和失败来源。

## Python 调用

```python
from scripts.stock_data import history, normalize_symbol, quote, search

print(normalize_symbol("HK700"))
print(quote("600519", market="A"))
bars = history("AAPL", market="US", limit=20)
print(bars["rows"][-1])
print(search("腾讯", limit=5))
```

## 合规与限制

- Tencent Finance、Eastmoney 和 Yahoo Finance 均为公开网页数据来源，但服务条款、访问限制和数据延迟可能变化；商业使用或再分发前应自行核实当前条款。
- 控制请求频率，避免批量抓取、并发轰击、高频交易和订单执行。
- Yahoo 历史时间戳按 UTC 转换为日期；周末、节假日或源端延迟会导致最新日期早于今天。
- 返回值是数据访问结果，不是投资建议、估值结论或交易信号。
- 需要研报、基本面、资金流、期权、SEC Filing 等功能时，应新增独立数据源适配器、标准化输出和对应测试，不要把未实现能力写进接口承诺。

详细路由、字段和扩展约定见 [`references/sources.md`](references/sources.md)，技能触发与调用规则见 [`SKILL.md`](SKILL.md)。

## 参考项目

- [a-stock-data](https://github.com/simonlin1212/a-stock-data)：A 股多数据源与降级策略参考。
- [global-stock-data](https://github.com/simonlin1212/global-stock-data)：港股/美股数据源分层与合规说明参考。

## 免责声明

本项目仅提供公开数据访问工具，不构成任何投资、交易、法律或合规建议。市场数据可能延迟、缺失或被来源修订。
