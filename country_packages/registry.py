"""
Country Packages - Registry

The runtime lookup every other Kernel module uses ("Load Country
Package" in the spec's Login/Request Execution flows). Backed by
`country_packages/loader.py`, which actually scans `country_packages/`
and imports each package's `manifest.py` + submodules.

Kept as a *thin, stable facade* on purpose: `get_country_package()`'s
signature and the fields on `CountryPackage` (`.currency`,
`.default_provider`) are unchanged from before this package build-out,
so kernel/workflow_engine/engine.py and everything else that was
already calling this keeps working untouched, whether or not a given
country's full package has been built yet.

Only Kenya is a fully-built, `active = True` package today. Uganda,
Tanzania, Ghana and Nigeria are discovered (so `list_countries()` can
tell the Frontend they exist) but stay `active = False` - and therefore
unavailable at signup - until each is built out the same way Kenya was.
"""

from dataclasses import dataclass

from country_packages.loader import LoadedCountryPackage, load_all_packages

_LOADED: dict[str, LoadedCountryPackage] = load_all_packages()


@dataclass(frozen=True)
class CountryPackage:
    code: str
    name: str
    currency: str
    default_provider: str
    active: bool = True


def _default_provider(pkg: LoadedCountryPackage) -> str:
    if pkg.defaults is not None:
        provider = getattr(pkg.defaults, "DEFAULT_PROVIDER", None)
        if provider:
            return provider
    return "mock_mobile_money"


# Every discovered package (built-out or stub) gets an entry here, so
# `.currency` keeps resolving for companies already registered under a
# country whose full package isn't built yet - only `active` gates
# whether *new* signups may choose it.
REGISTRY: dict[str, CountryPackage] = {
    code: CountryPackage(
        code=code,
        name=pkg.manifest.country_name,
        currency=pkg.manifest.currency,
        default_provider=_default_provider(pkg),
        active=pkg.manifest.active,
    )
    for code, pkg in _LOADED.items()
}

DEFAULT = REGISTRY["KE"]


def get_country_package(country_code: str | None) -> CountryPackage:
    if not country_code:
        return DEFAULT
    return REGISTRY.get(country_code.upper(), DEFAULT)


def get_loaded_package(country_code: str | None) -> LoadedCountryPackage | None:
    """The full package (providers/taxes/compliance/defaults/...), for
    callers that need more than currency + default provider - e.g. the
    signup flow generating an initial Blueprint from
    `defaults.DEFAULT_BLUEPRINT`."""
    if not country_code:
        country_code = DEFAULT.code
    return _LOADED.get(country_code.upper())


def is_active(country_code: str | None) -> bool:
    pkg = REGISTRY.get((country_code or "").upper())
    return bool(pkg and pkg.active)


def list_countries() -> list[CountryPackage]:
    return sorted(REGISTRY.values(), key=lambda p: p.name)
