"""Live terminal demo of the FinAlly market data simulator.

Runs the real pipeline the app uses (SimulatorDataSource writing to PriceCache),
draws it as a dashboard, then prints a session summary and a check of the
model's ticker correlations. Needs no API keys.

    uv run market_data_demo.py                     # 30 seconds, default tickers
    uv run market_data_demo.py --duration 0        # until Ctrl+C
    uv run market_data_demo.py --speed 60          # one real second = one trading minute
    uv run market_data_demo.py --tickers AAPL PYPL --seed 42
    uvx --with . python market_data_demo.py        # same, in a throwaway environment
"""

import argparse
import asyncio
import math
import random
import statistics
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from itertools import combinations

from app.market import InvalidTickerError, PriceCache, PriceUpdate, normalize_ticker
from app.market.seed_prices import (
    CROSS_SECTOR_CORR,
    KNOWN_TICKERS,
    SECTOR_CORR,
    params_for,
)
from app.market.simulator import TICK_SECONDS, GBMSimulator, SimulatorDataSource

DEMO_EVENT_PROBABILITY = 0.005  # 10x the app's rate, so a short demo shows some events
BIG_MOVE = 0.015  # a one-tick move this large is logged; ordinary ticks are far smaller
REFRESH_SECONDS = 0.1
SPARK_WIDTH = 40
SPARK_CHARS = "▁▂▃▄▅▆▇█"
MAX_MOVES_SHOWN = 6
MODEL_CHECK_TICKS = 5000

USE_ANSI = sys.stdout.isatty()
GREEN, RED, YELLOW, DIM, BOLD = "32", "31", "33", "2", "1"
ENTER_SCREEN, LEAVE_SCREEN = "\x1b[?1049h\x1b[?25l", "\x1b[?25h\x1b[?1049l"


def paint(text: str, code: str | None) -> str:
    return f"\x1b[{code}m{text}\x1b[0m" if USE_ANSI and code else text


def signed_color(value: float) -> str | None:
    return GREEN if value > 0 else RED if value < 0 else None


def sparkline(prices: deque[float]) -> str:
    """Scale prices to the window's own range, so small moves stay visible."""
    if not prices:
        return ""
    low, high = min(prices), max(prices)
    if high == low:
        return SPARK_CHARS[0] * len(prices)
    top = len(SPARK_CHARS) - 1
    return "".join(SPARK_CHARS[round((p - low) / (high - low) * top)] for p in prices)


@dataclass
class Track:
    """What the demo has seen of one ticker since it started."""

    start: float
    latest: PriceUpdate
    low: float
    high: float
    ticks: int = 0
    history: deque[float] = field(default_factory=lambda: deque(maxlen=SPARK_WIDTH))

    @property
    def change_pct(self) -> float:
        return (self.latest.price / self.start - 1) * 100


class Session:
    """Reads the price cache the way SSE does and keeps what the display needs."""

    def __init__(self, cache: PriceCache) -> None:
        self.cache = cache
        self.tracks: dict[str, Track] = {}
        self.moves: deque[str] = deque(maxlen=MAX_MOVES_SHOWN)
        self.started_at = time.monotonic()

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started_at

    def sample(self) -> list[str]:
        """Take in new prices and return log lines for any big moves among them."""
        new_moves = []
        for ticker, update in self.cache.get_all().items():
            track = self.tracks.get(ticker)
            if track is None:
                track = Track(update.price, update, update.price, update.price)
                track.history.append(update.price)
                self.tracks[ticker] = track
            elif update.timestamp > track.latest.timestamp:
                move = update.price / track.latest.price - 1
                if abs(move) >= BIG_MOVE:
                    new_moves.append(
                        f"{self.elapsed:6.1f}s  {ticker:<7} {move * 100:+.2f}%  "
                        f"${track.latest.price:,.2f} -> ${update.price:,.2f}"
                    )
                track.latest = update
                track.ticks += 1
                track.low = min(track.low, update.price)
                track.high = max(track.high, update.price)
                track.history.append(update.price)
        self.moves.extend(new_moves)
        return new_moves


def render(
    session: Session, source: SimulatorDataSource, args: argparse.Namespace
) -> str:
    status = source.status()
    remaining = (
        "Ctrl+C to stop"
        if args.duration == 0
        else f"{args.duration:g}s run, Ctrl+C to stop"
    )
    lines = [
        paint("FinAlly market simulator", BOLD)
        + f"   source={status.source} mode={status.mode}"
        + f"   elapsed={session.elapsed:.1f}s ({remaining})",
        paint(
            f"tick={TICK_SECONDS}s  speed={args.speed:g}x  events={args.event_probability:g}"
            f" per ticker per tick  cache updates={session.cache.version}",
            DIM,
        ),
        "",
        paint(f"{'TICKER':<7} {'PRICE':>10}   {'TICK':>7} {'SESSION':>8}  TREND", BOLD),
    ]
    for ticker, track in sorted(session.tracks.items()):
        update = track.latest
        arrow = {"up": "▲", "down": "▼", "flat": " "}[update.direction]
        color = signed_color(update.change)
        lines.append(
            f"{ticker:<7} {paint(f'{update.price:>10,.2f}', color)} "
            f"{paint(f'{arrow} {update.change:>+7.2f}', color)} "
            f"{paint(f'{track.change_pct:>+7.2f}%', signed_color(track.change_pct))}  "
            f"{paint(sparkline(track.history), YELLOW)}"
        )
    lines += ["", paint(f"BIG MOVES (one tick, {BIG_MOVE:.1%} or more)", BOLD)]
    lines += list(session.moves) or [paint("none yet", DIM)]
    return "".join(f"{line}\x1b[K\n" for line in lines)


async def run(
    session: Session, source: SimulatorDataSource, args: argparse.Namespace
) -> None:
    deadline = time.monotonic() + args.duration if args.duration else math.inf
    await source.start(args.tickers)
    try:
        while time.monotonic() < deadline:
            new_moves = session.sample()
            if USE_ANSI:
                sys.stdout.write("\x1b[H" + render(session, source, args) + "\x1b[J")
                sys.stdout.flush()
            else:
                for move in new_moves:
                    print(move, flush=True)
            await asyncio.sleep(REFRESH_SECONDS)
        session.sample()
    finally:
        await source.stop()


def print_summary(session: Session) -> None:
    print(paint(f"\nSession summary ({session.elapsed:.1f}s)", BOLD))
    print(
        f"{'TICKER':<7} {'START':>10} {'END':>10} {'CHANGE':>8} {'LOW':>10} {'HIGH':>10} {'TICKS':>6}"
    )
    for ticker, t in sorted(session.tracks.items()):
        change = paint(f"{t.change_pct:>+7.2f}%", signed_color(t.change_pct))
        print(
            f"{ticker:<7} {t.start:>10,.2f} {t.latest.price:>10,.2f} {change} "
            f"{t.low:>10,.2f} {t.high:>10,.2f} {t.ticks:>6}"
        )


def print_model_check(seed: int | None) -> None:
    """Measure correlation over many ticks: a short live session is too noisy to show it."""
    simulator = GBMSimulator(event_probability=0.0, rng=random.Random(seed))
    for ticker in KNOWN_TICKERS:
        simulator.add_ticker(ticker)
    returns: dict[str, list[float]] = {ticker: [] for ticker in KNOWN_TICKERS}
    previous = simulator.step()
    for _ in range(MODEL_CHECK_TICKS):
        current = simulator.step()
        for ticker, series in returns.items():
            series.append(math.log(current[ticker] / previous[ticker]))
        previous = current

    groups: dict[str, tuple[float, list[float]]] = {
        **{f"within {name}": (corr, []) for name, corr in SECTOR_CORR.items()},
        "across sectors": (CROSS_SECTOR_CORR, []),
    }
    for a, b in combinations(KNOWN_TICKERS, 2):
        sector_a, sector_b = params_for(a).sector, params_for(b).sector
        group = (
            f"within {sector_a}"
            if sector_a and sector_a == sector_b
            else "across sectors"
        )
        groups[group][1].append(statistics.correlation(returns[a], returns[b]))

    print(
        paint(
            f"\nModel check: return correlation over {MODEL_CHECK_TICKS:,} ticks", BOLD
        )
    )
    print(f"{'PAIRS':<16} {'TARGET':>7} {'MEASURED':>9}")
    for name, (target, values) in groups.items():
        print(f"{name:<16} {target:>7.2f} {statistics.fmean(values):>9.2f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Live demo of the market data simulator."
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=30.0,
        help="seconds to run; 0 runs until Ctrl+C (default: 30)",
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=list(KNOWN_TICKERS),
        metavar="TICKER",
        help="symbols to simulate; unknown ones get a generated seed price (default: the app's 10)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="simulated time per real second (default: 1)",
    )
    parser.add_argument(
        "--event-probability",
        type=float,
        default=DEMO_EVENT_PROBABILITY,
        help=f"chance of a 2-5%% jump per ticker per tick (default: {DEMO_EVENT_PROBABILITY})",
    )
    parser.add_argument(
        "--seed", type=int, help="random seed for a repeatable price path"
    )
    args = parser.parse_args()

    if args.duration < 0:
        parser.error("--duration must not be negative")
    if args.speed <= 0:
        parser.error("--speed must be positive")
    if not 0 <= args.event_probability <= 1:
        parser.error("--event-probability must be between 0 and 1")
    try:
        args.tickers = list(dict.fromkeys(normalize_ticker(t) for t in args.tickers))
    except InvalidTickerError as exc:
        parser.error(str(exc))
    return args


def main() -> None:
    args = parse_args()
    cache = PriceCache()
    simulator = GBMSimulator(
        tick_seconds=TICK_SECONDS * args.speed,
        event_probability=args.event_probability,
        rng=random.Random(args.seed),
    )
    source = SimulatorDataSource(cache, simulator=simulator)
    session = Session(cache)

    if USE_ANSI:
        sys.stdout.write(ENTER_SCREEN)
    try:
        asyncio.run(run(session, source, args))
    except KeyboardInterrupt:
        pass
    finally:
        if USE_ANSI:
            sys.stdout.write(LEAVE_SCREEN)
            sys.stdout.flush()

    print_summary(session)
    if session.moves:
        print(paint("\nBig moves", BOLD))
        print("\n".join(session.moves))
    print_model_check(args.seed)


if __name__ == "__main__":
    main()
