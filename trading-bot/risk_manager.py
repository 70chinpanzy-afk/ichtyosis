"""Professional Risk Management — position sizing, correlation, drawdown control.

Key principles:
  - Risk 1-2% of capital per trade (fixed fractional)
  - Reduce position size when correlated assets are already open
  - Gradually reduce exposure as drawdown increases
  - Hard stop at max drawdown (complements kill_switch.py)

Usage:
    from risk_manager import RiskManager
    rm = RiskManager()
    size = rm.calculate_position_size(capital, entry, sl, symbol, positions)
"""


# Crypto correlation with BTC (approximate, stable enough for sizing)
# 1.0 = perfectly correlated, 0.0 = uncorrelated
BTC_CORRELATION = {
    "BTC/USDT": 1.00,
    "ETH/USDT": 0.85,
    "SOL/USDT": 0.80,
    "BNB/USDT": 0.75,
    "XRP/USDT": 0.70,
}


class RiskManager:
    """Portfolio-level risk management."""

    def __init__(self,
                 risk_per_trade_pct: float = 0.02,
                 max_portfolio_heat_pct: float = 0.10,
                 max_correlation_exposure: float = 0.06,
                 drawdown_reduction_start: float = 0.05,
                 drawdown_halt_pct: float = 0.15):
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_portfolio_heat_pct = max_portfolio_heat_pct
        self.max_correlation_exposure = max_correlation_exposure
        self.drawdown_reduction_start = drawdown_reduction_start
        self.drawdown_halt_pct = drawdown_halt_pct
        self.peak_capital = 0.0

    def update_peak(self, capital: float):
        """Track peak capital for drawdown calculation."""
        if capital > self.peak_capital:
            self.peak_capital = capital

    def get_drawdown(self, capital: float) -> float:
        """Current drawdown as a positive fraction (0.05 = 5% drawdown)."""
        if self.peak_capital <= 0:
            return 0.0
        return max(0.0, (self.peak_capital - capital) / self.peak_capital)

    def get_drawdown_factor(self, capital: float) -> float:
        """Position size multiplier based on drawdown. 1.0 = full size, 0.0 = halt."""
        dd = self.get_drawdown(capital)
        if dd >= self.drawdown_halt_pct:
            return 0.0
        if dd <= self.drawdown_reduction_start:
            return 1.0
        # Linear reduction between start and halt
        range_pct = self.drawdown_halt_pct - self.drawdown_reduction_start
        reduction = (dd - self.drawdown_reduction_start) / range_pct
        return max(0.0, 1.0 - reduction)

    def get_portfolio_heat(self, capital: float, positions: dict) -> float:
        """Total portfolio risk as fraction of capital."""
        if not positions or capital <= 0:
            return 0.0

        total_risk = 0.0
        for sym, pos in positions.items():
            entry = pos.get("entry_price", 0)
            sl = pos.get("stop_loss", 0)
            size_value = pos.get("size", 0)
            if entry > 0:
                risk_pct = abs(entry - sl) / entry
                total_risk += risk_pct * size_value / capital

        return total_risk

    def get_correlation_exposure(self, symbol: str, positions: dict) -> float:
        """How much correlated exposure already exists."""
        if not positions:
            return 0.0

        my_corr = BTC_CORRELATION.get(symbol, 0.5)
        exposure = 0.0
        for sym in positions:
            other_corr = BTC_CORRELATION.get(sym, 0.5)
            # Correlation between two alts ≈ product of their BTC correlations
            pair_corr = my_corr * other_corr
            exposure += pair_corr

        return exposure

    def can_trade(self, capital: float, positions: dict) -> tuple[bool, str]:
        """Pre-trade gate: check all risk limits."""
        # Drawdown check
        dd_factor = self.get_drawdown_factor(capital)
        if dd_factor <= 0:
            dd = self.get_drawdown(capital)
            return False, f"Drawdown halt: {dd:.1%} >= {self.drawdown_halt_pct:.0%}"

        # Portfolio heat check
        heat = self.get_portfolio_heat(capital, positions)
        if heat >= self.max_portfolio_heat_pct:
            return False, f"Portfolio heat: {heat:.1%} >= {self.max_portfolio_heat_pct:.0%}"

        return True, "OK"

    def calculate_position_size(self, capital: float, entry_price: float,
                                stop_loss: float, symbol: str,
                                positions: dict) -> float:
        """Calculate position size with all risk adjustments.

        Returns position size in quote currency (USD/JPY).
        """
        if entry_price <= 0 or stop_loss <= 0 or capital <= 0:
            return 0.0

        # Base: fixed fractional
        risk_per_unit = abs(entry_price - stop_loss)
        if risk_per_unit <= 0:
            return 0.0

        risk_amount = capital * self.risk_per_trade_pct
        base_size = risk_amount / risk_per_unit * entry_price

        # Adjustment 1: Drawdown reduction
        dd_factor = self.get_drawdown_factor(capital)
        adjusted_size = base_size * dd_factor

        # Adjustment 2: Correlation reduction
        corr_exposure = self.get_correlation_exposure(symbol, positions)
        if corr_exposure > 0:
            # Reduce size proportionally to existing correlated exposure
            corr_factor = max(0.3, 1.0 - corr_exposure * 0.5)
            adjusted_size *= corr_factor

        # Adjustment 3: Portfolio heat cap
        heat = self.get_portfolio_heat(capital, positions)
        remaining_heat = max(0, self.max_portfolio_heat_pct - heat)
        max_size_by_heat = remaining_heat * capital / (risk_per_unit / entry_price) if risk_per_unit > 0 else adjusted_size
        adjusted_size = min(adjusted_size, max_size_by_heat)

        # Never exceed 20% of capital
        max_size = capital * 0.20
        adjusted_size = min(adjusted_size, max_size)

        return max(0.0, adjusted_size)


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    rm = RiskManager()
    rm.update_peak(10000)

    # Scenario 1: Fresh portfolio
    size = rm.calculate_position_size(
        capital=10000, entry_price=80000, stop_loss=78000,
        symbol="BTC/USDT", positions={})
    print(f"BTC fresh: ${size:,.0f} position")

    # Scenario 2: With existing BTC position
    positions = {
        "BTC/USDT": {"entry_price": 80000, "stop_loss": 78000, "size": 8000},
    }
    size = rm.calculate_position_size(
        capital=10000, entry_price=2000, stop_loss=1950,
        symbol="ETH/USDT", positions=positions)
    print(f"ETH with BTC open: ${size:,.0f} position")

    # Scenario 3: 10% drawdown
    rm.update_peak(10000)
    size = rm.calculate_position_size(
        capital=9000, entry_price=80000, stop_loss=78000,
        symbol="BTC/USDT", positions={})
    dd_factor = rm.get_drawdown_factor(9000)
    print(f"BTC at 10% DD: ${size:,.0f} position (dd_factor={dd_factor:.2f})")

    # Can trade check
    ok, reason = rm.can_trade(8400, {})
    print(f"Can trade at 16% DD: {ok} — {reason}")
