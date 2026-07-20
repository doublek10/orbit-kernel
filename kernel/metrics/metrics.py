"""
Metrics (stub)

Placeholder for request counters / latency histograms. Wire up
prometheus-client (or OpenTelemetry) here when observability infra
lands.
"""


class Metrics:
    def increment(self, name: str, **tags) -> None:
        pass

    def observe(self, name: str, value: float, **tags) -> None:
        pass
