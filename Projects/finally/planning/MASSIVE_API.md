# Massive API Reference

Research notes on the Massive REST API (formerly Polygon.io) for getting real-time and end-of-day US stock prices for multiple tickers. The design built on these notes is in [`MASSIVE_INTERFACE.md`](MASSIVE_INTERFACE.md).

**Researched 2026-10-30** against the live API, the official docs, and the `massive` 2.9.1 Python client.

## How this was checked

| Label | Meaning |
| ------------ | ---------------------------------------------------------------------------------------------- |
| **Tested** | Called on the live API on 2026-10-30, through Massive's MCP connector or `curl`, using a key whose access matches the free Basic plan |
| **Documented** | Taken from Massive's docs or pricing pages |
| **Client source** | Read from the `massive` 2.9.1 source, and run against a local imitation of the API |

The key could not reach the snapshot or last-trade endpoints, so **those two are documented but not tested**. See [Still unverified](#still-unverified).

## Key findings

1. **The free plan cannot show live prices.** Basic is end-of-day only and has no snapshot access. `PLAN.md` Section 6 assumes it can poll prices every 15 seconds, which does not work.
2. **The multi-ticker snapshot is the right endpoint for live prices.** One request returns every ticker, and it needs Stocks Starter ($29/month) or higher.
3. **Real-time prices need Stocks Advanced ($199/month).** Starter and Developer are delayed 15 minutes.
4. **The daily market summary is the right endpoint for end-of-day prices.** One request returns about 12,600 tickers, so it fits within the free plan's 5 requests a minute.
5. **Starter snapshots should not include `lastTrade`.** Starter excludes trade data, and the docs say the field is only returned if the plan includes trades. Code that reads `last_trade.price` without a fallback will break on Starter.

## Basics

| Item | Value |
| ----------------- | ------------------------------------------------------------------------------------ |
| REST base URL | `https://api.massive.com` (`https://api.polygon.io` still works) |
| Python client | `pip install massive` (2.9.1, Python 3.10+), imported as `from massive import RESTClient` |
| Authentication | `Authorization: Bearer <key>` header, or an `?apiKey=<key>` query parameter |
| Ticker format | Case-sensitive and uppercase, such as `AAPL` or `BRK.B` |
| Rate limit | 5 requests a minute on Basic, unlimited on paid plans |

Prefer the header, which is what the Python client sends, because query strings end up in logs.

### Plans for stocks

Prices and features from [massive.com/stocks](https://massive.com/stocks), as listed on 2026-10-30. Check that page before relying on them.

| | Basic | Starter | Developer | Advanced |
| ----------------- | ---------- | -------------- | -------------- | --------- |
| Price per month | $0 | $29 | $79 | $199 |
| API calls | 5/min | Unlimited | Unlimited | Unlimited |
| Data recency | End-of-day | 15-min delayed | 15-min delayed | Real-time |
| History | 2 years | 5 years | 10 years | 20+ years |
| Snapshots | No | Yes | Yes | Yes |
| Minute bars | Yes | Yes | Yes | Yes |
| Trades | No | No | Yes | Yes |
| Quotes | No | No | No | Yes |
| WebSockets | No | Yes | Yes | Yes |

Limits apply per asset class: a paid options plan does not lift the 5-a-minute limit on stocks requests. Massive says a 429 on a plan you pay for "is worth reporting rather than retrying".

### Which endpoint to use

| Need | Endpoint | Tickers per call | Lowest plan | Status |
| ----------------------------- | --------------------------------------------------- | ---------------- | ----------- | ---------- |
| **Latest prices, many tickers** | `GET /v2/snapshot/locale/us/markets/stocks/tickers` | Many | Starter | Documented |
| Latest prices, newer format | `GET /v3/snapshot` | Up to 250 | Starter | Documented |
| Latest trade | `GET /v2/last/trade/{ticker}` | 1 | Developer | Documented |
| **Closing prices, all tickers** | `GET /v2/aggs/grouped/locale/us/market/stocks/{date}` | All | Basic | Tested |
| Last trading day's bar | `GET /v2/aggs/ticker/{ticker}/prev` | 1 | Basic | Tested |
| One day with extended hours | `GET /v1/open-close/{ticker}/{date}` | 1 | Basic | Tested |
| Bars over a date range | `GET /v2/aggs/ticker/{ticker}/range/{n}/{span}/{from}/{to}` | 1 | Basic | Tested |
| Does this ticker exist? | `GET /v3/reference/tickers/{ticker}` | 1 | Basic | Tested |
| Is the market open? | `GET /v1/marketstatus/now` | n/a | Basic | Tested |

## Real-time and delayed prices

### Multi-ticker snapshot (recommended)

Returns the latest data for the listed tickers in one request. Leave out `tickers` to get the whole market, more than 10,000 tickers.

```bash
curl -H "Authorization: Bearer $MASSIVE_API_KEY" \
  "https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,MSFT,NVDA"
```

```python
import os
from massive import RESTClient

client = RESTClient(os.environ["MASSIVE_API_KEY"])

for snapshot in client.get_snapshot_all("stocks", ["AAPL", "MSFT", "NVDA"]):
    trade = snapshot.last_trade  # None if the plan excludes trades
    print(snapshot.ticker, trade.price if trade else snapshot.min.close)
```

Response, from the API docs:

```json
{
  "count": 1,
  "status": "OK",
  "tickers": [
    {
      "ticker": "BCAT",
      "todaysChange": -0.124,
      "todaysChangePerc": -0.601,
      "updated": 1605192894630916600,
      "day": { "o": 20.64, "h": 20.64, "l": 20.506, "c": 20.506, "v": 37216, "vw": 20.616 },
      "min": { "t": 1684428600000, "o": 20.506, "h": 20.506, "l": 20.506, "c": 20.506, "v": 5000, "vw": 20.5105, "av": 37216, "n": 1 },
      "prevDay": { "o": 20.79, "h": 21, "l": 20.5, "c": 20.63, "v": 292738, "vw": 20.6939 },
      "lastTrade": { "p": 20.506, "s": 2416, "t": 1605192894630916600, "x": 4, "i": "71675577320245", "c": [14, 41] },
      "lastQuote": { "P": 20.6, "S": 22, "p": 20.5, "s": 13, "t": 1605192959994246100 }
    }
  ]
}
```

| JSON field | Client attribute | Notes |
| ------------------ | ----------------------------- | --------------------------------------------------- |
| `lastTrade.p` | `last_trade.price` | Only returned if the plan includes trades |
| `lastTrade.t` | `last_trade.sip_timestamp` | **Nanoseconds** |
| `min.c`, `min.t` | `min.close`, `min.timestamp` | Latest minute bar, timestamp in **milliseconds** |
| `day.c` | `day.close` | Today's bar so far |
| `prevDay.c` | `prev_day.close` | Previous day's close |
| `updated` | `updated` | Nanoseconds in the sample response |
| `todaysChangePerc` | `todays_change_percent` | Change since the previous day's close |
| `lastQuote` | `last_quote` | Only returned if the plan includes quotes |

Things to handle:

- **Daily reset.** Snapshot data is cleared at 3:30 AM Eastern and refills from about 4:00 AM, so fields can be missing or zero overnight. (The client's docstring says 12 AM. The REST docs are the more likely to be current.)
- **Price fallback.** Read `lastTrade`, then `min`, then `day`, then `prevDay`, and treat zero as missing.
- **Mixed timestamp units.** Convert by magnitude rather than assuming one unit.

### Unified snapshot

A newer format with session fields and a limit of 250 tickers. It has no advantage for this project, so FinAlly uses the multi-ticker snapshot.

```python
import os
from massive import RESTClient

client = RESTClient(os.environ["MASSIVE_API_KEY"])

for item in client.list_universal_snapshots(type="stocks", ticker_any_of=["AAPL", "MSFT"]):
    print(item.ticker, item.session.close, item.session.previous_close)
```

### Last trade

One request per ticker, and it needs Developer or higher. Use it only when you need the exact last trade of one symbol.

```python
import os
from massive import RESTClient

client = RESTClient(os.environ["MASSIVE_API_KEY"])

trade = client.get_last_trade("AAPL")
print(trade.price, trade.sip_timestamp)
```

## End-of-day prices

All responses in this section are real, from 2026-10-29.

### Daily market summary (recommended)

One request returns the bar of every US stock for one date. On 2026-10-29 that was 12,597 tickers.

```bash
curl -H "Authorization: Bearer $MASSIVE_API_KEY" \
  "https://api.massive.com/v2/aggs/grouped/locale/us/market/stocks/2026-10-29"
```

```python
import os
from massive import RESTClient

client = RESTClient(os.environ["MASSIVE_API_KEY"])

watched = {"AAPL", "MSFT", "NVDA"}
bars = client.get_grouped_daily_aggs("2026-10-29")  # [] on a non-trading day
closes = {bar.ticker: bar.close for bar in bars if bar.ticker in watched}
print(closes)
```

Each result looks like this:

```json
{ "T": "SPUS", "o": 59.75, "h": 59.785, "l": 59.5, "c": 59.77, "v": 327254.665452, "vw": 59.6292, "n": 9935, "t": 1793304000000 }
```

Finding the date takes one more request, because the summary needs a trading day and today may not be one. Ask for the previous bar of an always-traded ticker such as `SPY`, then use its date. That is two requests in total, however many tickers you track. Convert the timestamp using the Eastern time zone:

```python
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from massive import RESTClient

client = RESTClient(os.environ["MASSIVE_API_KEY"])

previous = client.get_previous_close_agg("SPY")  # a list, despite the type hint
date = datetime.fromtimestamp(previous[0].timestamp / 1000, ZoneInfo("America/New_York")).date()
bars = client.get_grouped_daily_aggs(date.isoformat())
print(date, len(bars))
```

### Previous day bar

Tested at 13:10 Eastern on Friday 2026-10-30, during trading hours. It returned Thursday's bar:

```json
{ "T": "AAPL", "o": 348, "h": 351.43, "l": 347.3, "c": 348.91, "v": 42582126.0, "vw": 349.3528, "n": 736010, "t": 1793304000000 }
```

```python
import os
from massive import RESTClient

client = RESTClient(os.environ["MASSIVE_API_KEY"])

bars = client.get_previous_close_agg("AAPL")
print(bars[0].close if bars else "no data")
```

An unknown ticker returns no records rather than an error.

### One day with extended hours

One request gives the regular session plus the pre-market and after-hours prices.

```python
import os
from massive import RESTClient

client = RESTClient(os.environ["MASSIVE_API_KEY"])

day = client.get_daily_open_close_agg("AAPL", "2026-10-29")
print(day.open, day.close, day.pre_market, day.after_hours)
```

```json
{ "from": "2026-10-29", "symbol": "AAPL", "open": 348, "high": 351.43, "low": 347.3, "close": 348.91, "volume": 42582126.245661, "afterHours": 352.05, "preMarket": 346.33 }
```

### Bars over a date range

For history charts. `list_aggs` follows pagination for you. `timespan` can be `second`, `minute`, `hour`, `day`, `week`, `month`, `quarter` or `year`, and `limit` goes up to 50,000.

```python
import os
from massive import RESTClient

client = RESTClient(os.environ["MASSIVE_API_KEY"])

for bar in client.list_aggs("AAPL", 1, "day", "2026-10-26", "2026-10-30"):
    print(bar.timestamp, bar.close)
```

Tested results:

- Asking for 10-26 to 10-30 during trading on 10-30 returned four bars. On Basic, the current day has no partial bar.
- Minute bars include extended hours. The last 2026-10-29 bar started at 19:59 Eastern.

### Timestamps are not consistent

The same trading day has different `t` values depending on the endpoint:

| Endpoint | Value on 2026-10-29 | Means | Docs say |
| ------------------ | --------------- | ------------ | ---------------- |
| Daily market summary | `1793304000000` | 16:00 Eastern | End of window |
| Previous day bar | `1793304000000` | 16:00 Eastern | **Start of window** |
| Range, daily bars | `1793246400000` | 00:00 Eastern | Not stated |

Converting to an Eastern date gives 2026-10-29 for all three. Do not compare `t` values across endpoints.

## Supporting endpoints

### Does a ticker exist?

The clean way to validate a symbol: a known ticker returns details and an unknown one returns a 404.

```python
import os
from massive import RESTClient
from massive.exceptions import BadResponse

client = RESTClient(os.environ["MASSIVE_API_KEY"])

try:
    details = client.get_ticker_details("PYPL")
    print(details.name, details.active)
except BadResponse as error:
    print("Lookup failed:", error)
```

Tested: `PYPL` and `BRK.B` return details, and `ZZZZQ` returns `{"status":"NOT_FOUND","request_id":"...","message":"Ticker not found."}`.

### Is the market open?

```python
import os
from massive import RESTClient

client = RESTClient(os.environ["MASSIVE_API_KEY"])

status = client.get_market_status()
print(status.market, status.early_hours, status.after_hours)
```

`market` was `open` when tested. FinAlly does not need this call, because a poll outside trading hours simply returns unchanged data.

## Errors

The client has two behaviours that are easy to miss:

- **`BadResponse` has no status code.** Its only content is the response body, as a string, so you have to read the body to tell errors apart.
- **429 and 5xx responses raise urllib3's `MaxRetryError`, not `BadResponse`.** The client retries 413, 429, 499, 500, 502, 503 and 504, and raises once retries run out. Catch both types.

| Situation | HTTP | Body | Client raises | Status |
| ---------------- | ---- | ----------------------------------------------------------------- | ---------------- | ---------- |
| No key | 401 | `{"status":"ERROR","error":"API Key was not provided"}` | `BadResponse` | Tested |
| Invalid key | 401 | `{"status":"ERROR","error":"Unknown API Key"}` | `BadResponse` | Tested |
| Unknown ticker | 404 | `{"status":"NOT_FOUND","message":"Ticker not found."}` | `BadResponse` | Tested |
| Plan excludes data | 403 | `{"status":"NOT_AUTHORIZED","message":"You are not entitled..."}` | `BadResponse` | Not tested |
| Over the rate limit | 429 | | `MaxRetryError` | Limit tested, exception from client source |
| Server error | 5xx | | `MaxRetryError` | Client source |

```python
import os
from massive import RESTClient
from massive.exceptions import BadResponse
from urllib3.exceptions import HTTPError

# retries=0 stops failed calls spending the free plan's 5 requests a minute.
client = RESTClient(os.environ["MASSIVE_API_KEY"], connect_timeout=3.0, read_timeout=5.0, retries=0)

try:
    snapshots = client.get_snapshot_all("stocks", ["AAPL", "MSFT"])
except BadResponse as error:  # 4xx: read the body to see why
    text = str(error).lower()
    if "not_authorized" in text or "not entitled" in text:
        print("This plan does not include snapshots")
    else:
        print("Request rejected:", error)
except HTTPError as error:  # 429, 5xx, timeouts and connection failures
    print("Try again later:", error)
```

The client also blocks. In async code, call it with `asyncio.to_thread()`, or it will stall the event loop:

```python
import asyncio
import os
from massive import RESTClient

client = RESTClient(os.environ["MASSIVE_API_KEY"])

async def fetch(tickers: list[str]):
    return await asyncio.to_thread(client.get_snapshot_all, "stocks", tickers)

print(len(asyncio.run(fetch(["AAPL", "MSFT"]))))
```

## WebSockets

Starter and above also offer streaming. FinAlly stays with REST, as `PLAN.md` specifies: polling costs one request per cycle, needs no connection management, and can be replaced later without affecting anything downstream of the price cache.

## Still unverified

The available key has Basic access, so these need a Starter or higher key to confirm:

1. **The 403 body.** The live API was never seen returning it. The wording above comes from an open-source client's test fixtures, so the detection code matches two phrases.
2. **Whether Starter really omits `lastTrade`.** This follows from the docs, and the design handles both cases.
3. **How often Starter's price changes.** If `min.close` is the only source, it would change about once a minute even with faster polling.
4. **How a snapshot treats an unknown ticker.** It may leave the ticker out or return an error. FinAlly validates tickers first, so neither matters in normal use.
5. **The unit of `updated`.** The sample shows nanoseconds, and the field's description does not say.
6. **Snapshot field names on the live API.** Parsing was tested only against the documented sample format.

This command settles items 1 to 3 and 6 for any key:

```bash
curl -i -H "Authorization: Bearer $MASSIVE_API_KEY" \
  "https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,MSFT"
```

## Sources

- [Stock plans and features](https://massive.com/stocks) and [pricing](https://massive.com/pricing)
- [Request limits](https://massive.com/knowledge-base/article/what-is-the-request-limit-for-massives-restful-apis)
- [Full market snapshot](https://massive.com/docs/rest/stocks/snapshots/full-market-snapshot), [unified snapshot](https://massive.com/docs/rest/stocks/snapshots/unified-snapshot), [last trade](https://massive.com/docs/rest/stocks/trades-quotes/last-trade)
- [Daily market summary](https://massive.com/docs/rest/stocks/aggregates/daily-market-summary), [previous day bar](https://massive.com/docs/rest/stocks/aggregates/previous-day-bar)
- [Python client on GitHub](https://github.com/massive-com/client-python) and [on PyPI](https://pypi.org/project/massive/)
