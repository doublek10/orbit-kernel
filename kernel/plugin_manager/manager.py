"""
Plugin Manager

Loads marketplace applications and Country Packages dynamically. Plugins
talk to the Kernel exclusively through the Kernel API and never receive
direct database access - permissions are enforced by the Permission
Engine, same as any other caller.

Country Package loading follows the spec's "Plugin Manager" startup
sequence exactly:

    Startup -> Scan country_packages/ -> Read manifest.py
    -> Validate Compatibility -> Register Package
    -> Start Monitoring Services -> Ready

and, per request:

    Resolve Company -> Read company.country -> Load Country Package
    -> Merge With Blueprint -> Build Execution Context -> Execute Workflow

The actual scanning/importing lives in country_packages/loader.py - this
class is the thing other Kernel modules ask ("give me Kenya's package"),
never a country name itself.
"""

from country_packages.loader import LoadedCountryPackage, load_all_packages
from country_packages.registry import DEFAULT


class PluginManager:
    def __init__(self):
        self._plugins: dict[str, object] = {}
        self._country_packages: dict[str, LoadedCountryPackage] = {}
        self._ready = False

    # --- Marketplace / generic plugins ---

    def load(self, name: str, plugin) -> None:
        self._plugins[name] = plugin

    def get(self, name: str):
        return self._plugins.get(name)

    # --- Country Packages ---

    def start(self) -> None:
        """Startup -> Scan -> Validate -> Register -> Ready. Never
        hardcodes a country: whatever's discoverable under
        country_packages/ is what gets registered."""
        self._country_packages = load_all_packages()
        self._ready = True

    def get_country_package(self, country_code: str | None) -> LoadedCountryPackage | None:
        if not country_code:
            country_code = DEFAULT.code
        return self._country_packages.get(country_code.upper())

    def list_country_packages(self) -> list[LoadedCountryPackage]:
        return list(self._country_packages.values())

    def is_ready(self) -> bool:
        return self._ready


plugin_manager = PluginManager()
