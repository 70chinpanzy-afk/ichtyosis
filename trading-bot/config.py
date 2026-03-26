"""Trading bot configuration."""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
CHART_DIR = BASE_DIR / "charts"
RESULT_DIR = BASE_DIR / "results"
CHART_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

# Data settings
SYMBOL = "BTC/USDT"
SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
TIMEFRAME = "4h"
EXCHANGE = "binance"

# Chart generation
CHART_WINDOW_SIZE = 60  # Number of candles per chart image
CHART_SLIDE_STEP = 5    # Slide step for rolling window

# Numerical pre-filter thresholds
PREFILTER_MIN_SWING_PCT = 2.0   # Minimum swing size as % of price (relaxed for more candidates)
PREFILTER_LOOKBACK = 30         # Candles to look back for pattern detection

# Gemini API
GEMINI_MODEL = "gemini-2.5-flash"  # Paid tier: high rate limits
GEMINI_RPM_LIMIT = 1000  # Paid tier allows much higher RPM
GEMINI_SLEEP_SEC = 1.0  # Minimal sleep with paid tier

# Backtesting
INITIAL_CAPITAL = 10000.0
POSITION_SIZE_PCT = 1.0   # Use 100% of capital per trade
ATR_PERIOD = 14
ATR_SL_MULTIPLIER = 1.0   # Stop loss = ATR * multiplier (tight for small losses)
ATR_TP_MULTIPLIER = 2.0   # Take profit = ATR * multiplier (2:1 reward-risk)
COMMISSION_PCT = 0.001     # Commission rate (0.1% Binance spot)

# Patterns to detect
PATTERNS = [
    "double_bottom",
    "double_top",
    "head_and_shoulders",
    "inverse_head_and_shoulders",
    "ascending_triangle",
    "descending_triangle",
]
