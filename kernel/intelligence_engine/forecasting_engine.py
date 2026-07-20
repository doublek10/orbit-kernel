"""
Intelligence Engine - Forecasting Engine

A deterministic, explainable projection: hold the current 30-day average
net cash flow constant and project it forward. No randomness, no hidden
state - the same balance and the same 30-day window always produce the
same forecast (spec's Deterministic Intelligence requirement). This is
intentionally simple; it's the same method ai/insights.py already used
for its "forecast-30d" insight, generalized to multiple horizons and
wired into the Reasoning Engine instead of computed standalone.
"""

from kernel.intelligence_engine.models import Finding

_HORIZONS_DAYS = (30, 90)


class ForecastingEngine:
    def project(self, summary: dict) -> dict:
        daily_net = summary["net_30d"] / 30 if summary["net_30d"] else 0
        projections = {
            f"{days}d": round(summary["balance"] + daily_net * days, 2) for days in _HORIZONS_DAYS
        }
        return {
            "daily_net_avg": round(daily_net, 2),
            "projected_balance": projections,
            "method": "30-day average net cash flow held constant",
        }

    def finding(self, forecast: dict) -> Finding:
        projected_30d = forecast["projected_balance"]["30d"]
        severity = "critical" if projected_30d < 0 else "info"
        return Finding(
            id="forecast-30d",
            kind="forecast",
            severity=severity,
            title=f"Projected balance in 30 days: {projected_30d}",
            message="Based on your current 30-day average net cash flow, held constant. "
            + ("This goes negative - review upcoming spend." if projected_30d < 0 else "Trajectory looks stable."),
            data=forecast,
        )
