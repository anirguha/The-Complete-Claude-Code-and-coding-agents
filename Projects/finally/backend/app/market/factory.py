"""Chooses the market data source from the environment."""

import logging
import os
from collections.abc import Mapping

from .cache import PriceCache
from .interface import MarketDataSource
from .massive_client import DEFAULT_POLL_SECONDS, MassiveDataSource
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)


def create_market_data_source(
    cache: PriceCache, environ: Mapping[str, str] | None = None
) -> MarketDataSource:
    """Return Massive if MASSIVE_API_KEY is set and non-blank, else the simulator."""
    env = os.environ if environ is None else environ
    api_key = env.get("MASSIVE_API_KEY", "").strip()
    if not api_key:
        logger.info("MASSIVE_API_KEY not set: using the market simulator")
        return SimulatorDataSource(cache)
    poll_seconds = float(env.get("MASSIVE_POLL_SECONDS") or DEFAULT_POLL_SECONDS)
    logger.info("Using the Massive API, polling every %.1fs", poll_seconds)
    return MassiveDataSource(cache, api_key, poll_seconds)
