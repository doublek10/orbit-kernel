"""
Provider Manager (stub)

Standardised adapter layer for external integrations: banks, mobile money,
accounting platforms, ERPs, payroll, payment platforms. The Workflow
Engine requests provider operations through here - it never calls a
provider's SDK/API directly.

    class ProviderAdapter(Protocol):
        async def execute(self, operation: str, payload: dict) -> dict: ...

    class ProviderManager:
        def register(self, name: str, adapter: ProviderAdapter): ...
        async def call(self, name: str, operation: str, payload: dict) -> dict: ...
"""


class ProviderManager:
    def __init__(self):
        self._adapters: dict[str, object] = {}

    def register(self, name: str, adapter) -> None:
        self._adapters[name] = adapter

    def catalog(self) -> list[dict]:
        """What's available to connect - used by the providers.list workflow."""
        return [
            {
                "provider": name,
                "display_name": getattr(adapter, "display_name", name),
            }
            for name, adapter in self._adapters.items()
        ]

    async def call(self, name: str, operation: str, payload: dict) -> dict:
        if name not in self._adapters:
            raise NotImplementedError(f"Provider '{name}' is not registered yet")
        return await self._adapters[name].execute(operation, payload)


_manager: ProviderManager | None = None


def get_provider_manager() -> ProviderManager:
    """
    Process-wide Provider Manager, adapters registered once at first use.
    Each real integration (M-Pesa, a bank, an accounting platform) adds
    one line here - nothing else in the Kernel needs to change to pick
    it up, since callers only ever ask for it by name.
    """
    global _manager
    if _manager is None:
        _manager = ProviderManager()
        from providers.mock_mobile_money import MockMobileMoneyAdapter

        _manager.register("mock_mobile_money", MockMobileMoneyAdapter())
    return _manager
