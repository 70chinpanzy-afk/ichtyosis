"""GMO Coin REST API client for automated trading.

Supports both Spot and Margin (leverage) trading.
Docs: https://api.coin.z.com/docs/en/

Required .env vars:
    GMO_API_KEY=xxx
    GMO_API_SECRET=xxx
"""

import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_PUBLIC = "https://api.coin.z.com/public"
BASE_PRIVATE = "https://api.coin.z.com/private"


class GMOClient:
    """Thin wrapper around GMO Coin REST API."""

    def __init__(self, api_key: str = "", api_secret: str = ""):
        self.api_key = api_key or os.getenv("GMO_API_KEY", "")
        self.api_secret = api_secret or os.getenv("GMO_API_SECRET", "")
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def _sign(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        text = timestamp + method + path + body
        return hmac.new(
            self.api_secret.encode(), text.encode(), hashlib.sha256
        ).hexdigest()

    def _headers(self, timestamp: str, sign: str) -> dict:
        return {
            "API-KEY": self.api_key,
            "API-TIMESTAMP": timestamp,
            "API-SIGN": sign,
            "Content-Type": "application/json",
        }

    def _private_get(self, path: str, params: dict | None = None) -> dict:
        timestamp = str(int(time.time() * 1000))
        query = ""
        if params:
            query = "?" + "&".join(f"{k}={v}" for k, v in params.items())
        sign = self._sign(timestamp, "GET", path + query)
        resp = self.session.get(
            BASE_PRIVATE + path + query,
            headers=self._headers(timestamp, sign),
            timeout=10,
        )
        return resp.json()

    def _private_post(self, path: str, body: dict) -> dict:
        timestamp = str(int(time.time() * 1000))
        body_str = json.dumps(body)
        sign = self._sign(timestamp, "POST", path, body_str)
        resp = self.session.post(
            BASE_PRIVATE + path,
            headers=self._headers(timestamp, sign),
            data=body_str,
            timeout=10,
        )
        return resp.json()

    def _public_get(self, path: str, params: dict | None = None) -> dict:
        resp = self.session.get(
            BASE_PUBLIC + path, params=params, timeout=10
        )
        return resp.json()

    # ------------------------------------------------------------------
    # Public endpoints
    # ------------------------------------------------------------------

    def get_ticker(self, symbol: str) -> dict:
        """Get current ticker for a symbol."""
        result = self._public_get("/v1/ticker", {"symbol": symbol})
        if result.get("status") == 0:
            data = result.get("data", [])
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            return data
        raise Exception(f"Ticker error: {result}")

    def get_klines(self, symbol: str, interval: str = "4hour",
                   date: str = "") -> list[dict]:
        """Get OHLCV klines.

        interval: 1min, 5min, 15min, 30min, 1hour, 4hour, 8hour, 1day
        date: YYYYMMDD for <=1hour, YYYY for >=4hour
        """
        if not date:
            date = datetime.now(timezone.utc).strftime("%Y")
        result = self._public_get("/v1/klines", {
            "symbol": symbol, "interval": interval, "date": date,
        })
        if result.get("status") == 0:
            return result.get("data", [])
        raise Exception(f"Klines error: {result}")

    # ------------------------------------------------------------------
    # Account endpoints
    # ------------------------------------------------------------------

    def get_assets(self) -> list[dict]:
        """Get account asset balances."""
        result = self._private_get("/v1/account/assets")
        if result.get("status") == 0:
            return result.get("data", [])
        raise Exception(f"Assets error: {result}")

    def get_margin(self) -> dict:
        """Get margin account info."""
        result = self._private_get("/v1/account/margin")
        if result.get("status") == 0:
            return result.get("data", {})
        raise Exception(f"Margin error: {result}")

    # ------------------------------------------------------------------
    # Order endpoints
    # ------------------------------------------------------------------

    def place_order(self, symbol: str, side: str, size: str,
                    execution_type: str = "MARKET",
                    price: str = "", time_in_force: str = "") -> dict:
        """Place a new order.

        Args:
            symbol: e.g. "BTC_JPY"
            side: "BUY" or "SELL"
            size: Order size as string (e.g. "0.001")
            execution_type: "MARKET" or "LIMIT"
            price: Required for LIMIT orders
            time_in_force: "GTC", "IOC", "FOK" (for LIMIT)
        """
        body = {
            "symbol": symbol,
            "side": side,
            "executionType": execution_type,
            "size": size,
        }
        if execution_type == "LIMIT" and price:
            body["price"] = price
        if time_in_force:
            body["timeInForce"] = time_in_force

        result = self._private_post("/v1/order", body)
        if result.get("status") == 0:
            return result.get("data", {})
        raise Exception(f"Order error: {result}")

    def cancel_order(self, order_id: str) -> dict:
        """Cancel an open order."""
        result = self._private_post("/v1/cancelOrder", {"orderId": order_id})
        if result.get("status") == 0:
            return result
        raise Exception(f"Cancel error: {result}")

    def get_active_orders(self, symbol: str, page: int = 1) -> list[dict]:
        """Get active (open) orders."""
        result = self._private_get("/v1/activeOrders", {
            "symbol": symbol, "page": str(page),
        })
        if result.get("status") == 0:
            return result.get("data", {}).get("list", [])
        raise Exception(f"Active orders error: {result}")

    # ------------------------------------------------------------------
    # Margin position endpoints
    # ------------------------------------------------------------------

    def get_open_positions(self, symbol: str, page: int = 1) -> list[dict]:
        """Get open margin positions."""
        result = self._private_get("/v1/openPositions", {
            "symbol": symbol, "page": str(page),
        })
        if result.get("status") == 0:
            return result.get("data", {}).get("list", [])
        raise Exception(f"Open positions error: {result}")

    def close_order(self, symbol: str, side: str, size: str,
                    position_id: str, execution_type: str = "MARKET") -> dict:
        """Close a margin position."""
        body = {
            "symbol": symbol,
            "side": side,
            "executionType": execution_type,
            "settlePosition": [{"positionId": position_id, "size": size}],
        }
        result = self._private_post("/v1/closeOrder", body)
        if result.get("status") == 0:
            return result.get("data", {})
        raise Exception(f"Close order error: {result}")

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def get_price(self, symbol: str) -> float:
        """Get current last price for a symbol."""
        ticker = self.get_ticker(symbol)
        return float(ticker.get("last", 0))

    def get_jpy_balance(self) -> float:
        """Get available JPY balance."""
        assets = self.get_assets()
        for asset in assets:
            if asset.get("symbol") == "JPY":
                return float(asset.get("available", 0))
        return 0.0


if __name__ == "__main__":
    client = GMOClient()

    # Test public endpoints (no auth needed)
    print("=== Public API Test ===")
    try:
        ticker = client.get_ticker("BTC_JPY")
        print(f"BTC/JPY: ¥{float(ticker.get('last', 0)):,.0f}")
    except Exception as e:
        print(f"Ticker error: {e}")

    try:
        ticker_eth = client.get_ticker("ETH_JPY")
        print(f"ETH/JPY: ¥{float(ticker_eth.get('last', 0)):,.0f}")
    except Exception as e:
        print(f"ETH ticker error: {e}")

    # Test private endpoints (needs API key)
    if client.api_key:
        print("\n=== Private API Test ===")
        try:
            assets = client.get_assets()
            for a in assets:
                if float(a.get("available", 0)) > 0:
                    print(f"  {a['symbol']}: {a['available']}")
        except Exception as e:
            print(f"Assets error: {e}")
    else:
        print("\nNo GMO_API_KEY set — skipping private API tests")
