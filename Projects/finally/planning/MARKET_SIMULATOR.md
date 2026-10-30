# Market Simulator

How FinAlly simulates stock prices when no `MASSIVE_API_KEY` is set. It is the default source, needs no network or API key, and implements the same interface as Massive (see [`MASSIVE_INTERFACE.md`](MASSIVE_INTERFACE.md)).

**Status:** Design, to be built in `backend/app/market/`. The code below comes from a prototype that passed its tests, and the numbers in this document were measured from it.

## Requirements

From `PLAN.md` Section 6:

- Geometric Brownian motion (GBM) with drift and volatility per ticker
- Updates about every 500ms
- Correlated moves across tickers, such as tech stocks moving together
- Occasional sudden moves of 2-5% on one ticker
- Realistic seed prices
- An in-process background task with no external dependencies

## The price model

Each tick, a ticker's price is multiplied by a random factor:

```
S(t+dt) = S(t) * exp( (mu - sigma²/2) * dt  +  sigma * sqrt(dt) * Z  +  event )
```

| Symbol | Meaning | Example |
| ------- | ------------------------------------------ | -------- |
| `mu` | Annualized drift | `0.05` |
| `sigma` | Annualized volatility | `0.22` |
| `dt` | One tick as a fraction of a trading year | `8.48e-8` |
| `Z` | A correlated standard normal random number | |
| `event` | Usually 0, rarely about ±2-5% | |

GBM suits this well: because the price is multiplied by a positive number, it can never reach zero or go negative, and percentage moves are the same size whether a stock costs $50 or $800.

### Time step

`dt` treats wall-clock time as market time, with no overnight gaps:

```
dt = 0.5 s / (252 days * 6.5 hours * 3600 s) = 8.48e-8
```

An hour of watching the app is therefore an hour of trading, and `sigma` keeps its usual meaning. Drift is too small to see at this scale, at about 0.003% an hour for `mu = 0.05`, so short-term movement is almost entirely random.

### Correlated moves

Each ticker's `Z` is a mix of shared and individual random numbers, drawn fresh every tick:

```
Z = sqrt(rho_market) * M  +  sqrt(rho_sector - rho_market) * S  +  sqrt(1 - rho_sector) * e
```

- `M` is one market shock, shared by all tickers.
- `S` is one shock per sector, shared within that sector.
- `e` is one shock per ticker.

The three weights' squares add up to 1, so `Z` remains a standard normal and `sigma` stays accurate. Two tickers correlate by exactly the variance they share:

| Pair | Correlation |
| ------------------------------------------------------ | ----------- |
| Tech: AAPL, GOOGL, MSFT, AMZN, NVDA, META, NFLX | 0.6 |
| Finance: JPM, V | 0.5 |
| Different sectors, or any ticker with no sector, such as TSLA or a newly added one | 0.3 |

**This replaces the Cholesky decomposition** described in `MARKET_DATA_SUMMARY.md`. Both produce the same correlations for this sector structure, but the shared-shock approach is simpler for this project:

- It needs no numpy and no matrix, and no rebuilding when a ticker is added or removed.
- It can't fail. A Cholesky decomposition raises an error if the matrix is invalid, whereas this always gives a valid result.
- Each step takes time proportional to the number of tickers: about 8µs for 10 tickers and 57µs for 100, far inside the 500ms tick. That is fast enough to run directly on the event loop.

What it gives up is arbitrary pairwise correlations, which the plan doesn't need.

### Random events

On each tick, each ticker has a 0.05% chance of an event: a sudden move of 2-5%, equally likely up or down. With 10 tickers at 2 ticks a second, that's an event somewhere about every 100 seconds, and on any one ticker about every 17 minutes.

Two choices differ from the earlier design:

- **The probability is 0.0005, not 0.001.** Events have a much bigger effect on prices than ordinary movement, as the table shows.
- **Events are log returns, not simple percentages.** Going +5% and then -5% as simple percentages loses money (`1.05 * 0.95 = 0.9975`), which would slowly drag prices down. Log returns cancel exactly.

Measured over 300 one-hour runs of AAPL (`sigma = 0.22`):

| Event probability | Typical price move in one hour |
| ----------------- | ------------------------------ |
| 0 (GBM only) | 0.5% |
| **0.0005 (chosen)** | **6.9%** |
| 0.001 (earlier design) | 9.6% |

So **events drive most long-run movement**, and prices move far more than a real stock would. This is a deliberate trade for a lively demo, and lowering `EVENT_PROBABILITY` calms it down. A session left running for a full day would typically see moves of about a third.

### What a tick looks like

Prices are stored at full precision in the simulator and rounded to cents in the cache, so small moves can show as no change:

| Ticker | Seed price | `sigma` | Average move per tick | Ticks with no visible change |
| ------ | ---------- | ------- | --------------------- | ---------------------------- |
| NVDA | $800 | 0.40 | $0.075 | 4% |
| NFLX | $600 | 0.35 | $0.049 | 6% |
| TSLA | $250 | 0.50 | $0.029 | 11% |
| MSFT | $420 | 0.20 | $0.020 | 16% |
| AAPL | $190 | 0.22 | $0.010 | 31% |
| JPM | $195 | 0.18 | $0.008 | 36% |

That gives a realistic pattern: most prices flash on most ticks, with an occasional pause.

## Seed prices and parameters

AAPL and GOOGL use the values from `PLAN.md`. The rest are illustrative, not current market prices, and they don't need updating, since the simulator doesn't claim to show real ones.

A ticker that isn't in the table gets `mu = 0.05`, `sigma = 0.25`, no sector, and a seed price between $50 and $300. The seed is derived from the symbol, so a ticker always starts at the same price, which keeps tests repeatable and stops a ticker's price jumping to a new random level if it is removed and added back.

## Code structure

Two classes keep the maths separate from the async plumbing:

```
backend/app/market/
├── seed_prices.py   # Constants: TickerParams, KNOWN_TICKERS, correlations
└── simulator.py     # GBMSimulator (the model), SimulatorDataSource (the task)

                 SimulatorDataSource   implements MarketDataSource
                 │  background task, every 500ms:
                 │    prices = simulator.step()
                 │    cache.update(ticker, price, now)
                 ▼
                 GBMSimulator          pure: no clock, no I/O, seeded rng
```

| Class | Knows about | Tested by |
| --------------------- | --------------------------------- | -------------------------------- |
| `GBMSimulator` | Maths and random numbers only | Statistics, with a fixed seed |
| `SimulatorDataSource` | asyncio, the clock, the cache | Short async runs with a fast tick |

### `seed_prices.py`

```python
"""Starting prices and per-ticker model parameters for the simulator."""

import random
from dataclasses import dataclass

DEFAULT_MU = 0.05
DEFAULT_SIGMA = 0.25
UNKNOWN_SEED_RANGE = (50.0, 300.0)

CROSS_SECTOR_CORR = 0.3  # correlation between any two tickers in different sectors
SECTOR_CORR = {"tech": 0.6, "finance": 0.5}  # correlation within a sector


@dataclass(frozen=True, slots=True)
class TickerParams:
    seed_price: float
    mu: float = DEFAULT_MU  # annualized drift
    sigma: float = DEFAULT_SIGMA  # annualized volatility
    sector: str | None = None  # a key of SECTOR_CORR, or None for market-only


KNOWN_TICKERS: dict[str, TickerParams] = {
    "AAPL": TickerParams(190.0, 0.05, 0.22, "tech"),
    "GOOGL": TickerParams(175.0, 0.05, 0.25, "tech"),
    "MSFT": TickerParams(420.0, 0.05, 0.20, "tech"),
    "AMZN": TickerParams(185.0, 0.05, 0.28, "tech"),
    "NVDA": TickerParams(800.0, 0.08, 0.40, "tech"),
    "META": TickerParams(500.0, 0.05, 0.30, "tech"),
    "NFLX": TickerParams(600.0, 0.05, 0.35, "tech"),
    "TSLA": TickerParams(250.0, 0.03, 0.50),  # high vol, moves on its own
    "JPM": TickerParams(195.0, 0.04, 0.18, "finance"),
    "V": TickerParams(280.0, 0.04, 0.17, "finance"),
}


def params_for(ticker: str) -> TickerParams:
    """Return a ticker's parameters. An unknown ticker's seed depends only on its symbol."""
    known = KNOWN_TICKERS.get(ticker)
    if known is not None:
        return known
    return TickerParams(random.Random(ticker).uniform(*UNKNOWN_SEED_RANGE))
```

### `simulator.py`

```python
"""The default market data source: correlated GBM prices with random events."""

import asyncio
import logging
import math
import random
import time
from collections.abc import Iterable

from .cache import PriceCache
from .interface import MarketDataSource
from .models import SourceStatus, normalize_ticker
from .seed_prices import CROSS_SECTOR_CORR, SECTOR_CORR, TickerParams, params_for

logger = logging.getLogger(__name__)

TICK_SECONDS = 0.5
TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600
EVENT_PROBABILITY = 0.0005  # per ticker, per tick
EVENT_SIZE_RANGE = (0.02, 0.05)


class GBMSimulator:
    """Pure price model: no clock, no I/O, deterministic for a given rng."""

    def __init__(
        self,
        tick_seconds: float = TICK_SECONDS,
        event_probability: float = EVENT_PROBABILITY,
        rng: random.Random | None = None,
    ) -> None:
        self._dt = tick_seconds / TRADING_SECONDS_PER_YEAR
        self._event_probability = event_probability
        self._rng = rng or random.Random()
        self._params: dict[str, TickerParams] = {}
        self._prices: dict[str, float] = {}

    def add_ticker(self, ticker: str) -> float:
        """Start simulating a ticker, if new, and return its current price."""
        if ticker not in self._prices:
            self._params[ticker] = params_for(ticker)
            self._prices[ticker] = self._params[ticker].seed_price
        return self._prices[ticker]

    def remove_ticker(self, ticker: str) -> None:
        self._params.pop(ticker, None)
        self._prices.pop(ticker, None)

    def step(self) -> dict[str, float]:
        """Advance every ticker by one tick and return the new prices."""
        gauss = self._rng.gauss
        market = gauss(0.0, 1.0)
        sectors = {name: gauss(0.0, 1.0) for name in SECTOR_CORR}
        for ticker, params in self._params.items():
            z = self._correlated_normal(params.sector, market, sectors)
            drift = (params.mu - 0.5 * params.sigma**2) * self._dt
            diffusion = params.sigma * math.sqrt(self._dt) * z
            self._prices[ticker] *= math.exp(drift + diffusion + self._event_return())
        return dict(self._prices)

    def _correlated_normal(
        self, sector: str | None, market: float, sectors: dict[str, float]
    ) -> float:
        """Mix shared and individual shocks into one standard normal.

        Two tickers correlate by the variance they share: CROSS_SECTOR_CORR
        from the market shock, plus the rest of SECTOR_CORR from a sector shock.
        """
        sector_corr = SECTOR_CORR[sector] if sector else CROSS_SECTOR_CORR
        z = math.sqrt(CROSS_SECTOR_CORR) * market
        if sector:
            z += math.sqrt(sector_corr - CROSS_SECTOR_CORR) * sectors[sector]
        return z + math.sqrt(1.0 - sector_corr) * self._rng.gauss(0.0, 1.0)

    def _event_return(self) -> float:
        """Return a log return of about +/-2-5% on the rare tick with an event, else 0."""
        if self._rng.random() >= self._event_probability:
            return 0.0
        size = self._rng.uniform(*EVENT_SIZE_RANGE)
        return size if self._rng.random() < 0.5 else -size


class SimulatorDataSource(MarketDataSource):
    """Runs a GBMSimulator in a background task and writes prices to the cache."""

    def __init__(
        self,
        cache: PriceCache,
        tick_seconds: float = TICK_SECONDS,
        simulator: GBMSimulator | None = None,
    ) -> None:
        self._cache = cache
        self._tick_seconds = tick_seconds
        self._simulator = simulator or GBMSimulator(tick_seconds=tick_seconds)
        self._tickers: set[str] = set()
        self._task: asyncio.Task[None] | None = None
        self._last_success_at: float | None = None
        self._last_error: str | None = None

    async def start(self, tickers: Iterable[str]) -> None:
        for ticker in tickers:
            await self.add_ticker(ticker)
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="market-simulator")

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def add_ticker(self, ticker: str) -> None:
        symbol = normalize_ticker(ticker)
        if symbol not in self._tickers:
            self._tickers.add(symbol)
            # Priced now, so a ticker can be traded the moment it is added.
            self._cache.update(symbol, self._simulator.add_ticker(symbol))

    async def remove_ticker(self, ticker: str) -> None:
        symbol = normalize_ticker(ticker)
        self._tickers.discard(symbol)
        self._simulator.remove_ticker(symbol)
        self._cache.remove(symbol)

    def get_tickers(self) -> list[str]:
        return sorted(self._tickers)

    def status(self) -> SourceStatus:
        return SourceStatus(
            "simulator", "simulated", self._last_success_at, self._last_error
        )

    async def _run(self) -> None:
        while True:
            try:
                now = time.time()
                for ticker, price in self._simulator.step().items():
                    self._cache.update(ticker, price, now)
                self._last_success_at, self._last_error = now, None
            except Exception as exc:  # one bad tick must not end the price feed
                logger.exception("Simulator tick failed")
                self._last_error = str(exc)
            await asyncio.sleep(self._tick_seconds)
```

## Behaviour

| Situation | Behaviour |
| ----------------------------- | --------------------------------------------------------------------------- |
| Startup | The cache is filled with seed prices before `start()` returns, so prices are available immediately |
| Adding a ticker | Priced at once, so it can be traded straight away. Any valid symbol is accepted |
| Adding a malformed symbol | Raises `InvalidTickerError` |
| Removing a ticker | Dropped from the simulator and the cache |
| Removing and re-adding | Restarts from its seed price |
| An error during a tick | Logged and recorded in `status()`. The next tick still runs |
| `stop()` | Cancels the task. Safe to call twice |

**Known limitation:** prices aren't saved, so a restart returns every ticker to its seed price. Positions in the database keep their average cost, so unrealized P&L will jump after a restart. Persisting the last prices would fix this, but it isn't worth the extra code for a demo.

## Testing

Tests live in `backend/tests/market/`. The prototype's statistical tests use a fixed seed, so they don't fail at random:

| Test | Checks |
| ----------------- | ------------------------------------------------------------------------ |
| Determinism | Two simulators with the same seed produce identical prices |
| Volatility | Over 200,000 ticks, measured `sigma` is within 2% of the target for every ticker |
| Correlation | Measured correlations are within 0.02 of 0.6, 0.5 and 0.3 |
| Events | Over 400,000 ticks, the rate is within 15% of target and sizes stay in range |
| Unknown tickers | The seed is in range and the same each time |
| Source lifecycle | Start, add, remove, malformed symbol, double stop, no writes after stop |
| Error recovery | A failing tick doesn't end the task |

A statistical test looks like this:

```python
import math
import random
import statistics

import pytest

from app.market.seed_prices import KNOWN_TICKERS
from app.market.simulator import TRADING_SECONDS_PER_YEAR, GBMSimulator


def test_sigma_matches_target():
    simulator = GBMSimulator(event_probability=0.0, rng=random.Random(7))
    simulator.add_ticker("AAPL")
    previous = simulator.step()["AAPL"]
    returns = []
    for _ in range(200_000):
        price = simulator.step()["AAPL"]
        returns.append(math.log(price / previous))
        previous = price
    dt = 0.5 / TRADING_SECONDS_PER_YEAR
    measured = statistics.stdev(returns) / math.sqrt(dt)
    assert measured == pytest.approx(KNOWN_TICKERS["AAPL"].sigma, rel=0.02)
```
