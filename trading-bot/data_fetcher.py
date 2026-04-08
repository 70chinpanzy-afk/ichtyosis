"""Fetch OHLCV data from exchange using ccxt."""

import ccxt
import pandas as pd
from config import SYMBOL, TIMEFRAME, EXCHANGE


def fetch_ohlcv(symbol: str = SYMBOL, timeframe: str = TIMEFRAME,
                limit: int = 1000, exchange_id: str = EXCHANGE) -> pd.DataFrame:
    """Fetch OHLCV candlestick data.

    Returns DataFrame with columns: timestamp, open, high, low, close, volume
    """
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({"enableRateLimit": True})

    print(f"Fetching {limit} candles of {symbol} {timeframe} from {exchange_id}...")
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df.astype(float)

    print(f"Fetched {len(df)} candles: {df.index[0]} → {df.index[-1]}")
    return df


if __name__ == "__main__":
    df = fetch_ohlcv(limit=100)
    print(df.tail(10))
