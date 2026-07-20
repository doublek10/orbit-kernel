"""
Service Registry (stub)

Tracks which business modules/services are available to the Request
Router at runtime - useful once the Kernel is split across multiple
deployable services rather than a single process.
"""


class ServiceRegistry:
    def __init__(self):
        self._services: dict[str, object] = {}

    def register(self, name: str, service) -> None:
        self._services[name] = service

    def get(self, name: str):
        if name not in self._services:
            raise KeyError(f"Service '{name}' is not registered")
        return self._services[name]
