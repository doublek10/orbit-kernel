"""
Provider Catalog (Financial Connections)

The "Provider" picker in the Financial Connections UI - now sourced
from each active Country Package's `providers/` module instead of a
separate hand-maintained list. This is what makes a Country Package's
providers actually show up where a company connects one: before this,
`country_packages/{country}/providers/` fed the Kernel's internal
knowledge of a country but the Financial Connections catalog never
read it, so a Ghanaian company would see none of MTN MoMo, Vodafone
Cash, GCB Bank etc. Building a Country Package now automatically
extends this catalog - no change here is required when the next
country is built.

This is deliberately NOT the same thing as
kernel/provider_manager/manager.py's adapter registry: the catalog is
"providers a company can tell Orbit it uses", the adapter registry is
"providers Orbit can actually talk to on their behalf".

Only `mock_mobile_money` has a real adapter (`live: True`) - connecting
it runs an actual connect+sync against that adapter, the same working
path that existed before Financial Connections. Every other catalog
entry is `live: False`: connecting one stores the company's own
encrypted credentials for Orbit to use once a real adapter for it is
built, and Test Connection only checks the credential fields are
structurally complete - it does not fabricate a "connected" result for
an integration that doesn't exist yet. Honest about what's real, same
as the rest of this Kernel.
"""

from dataclasses import dataclass, field

from country_packages.loader import load_all_packages

CATEGORIES = ["bank", "mobile_money", "payment_gateway", "crypto", "custom"]


@dataclass(frozen=True)
class CatalogEntry:
    provider: str
    display_name: str
    category: str
    countries: list[str]
    auth_method: str  # api_key | oauth | none
    credential_fields: list[str] = field(default_factory=list)
    live: bool = False


def _build_catalog() -> list[CatalogEntry]:
    """Every active Country Package's providers/, merged by provider id
    so a provider shared across countries (Flutterwave, Binance Pay,
    the sandbox) ends up as one entry with every country it's available
    in, rather than one duplicate entry per country."""
    packages = load_all_packages()
    merged: dict[str, CatalogEntry] = {}

    for pkg in packages.values():
        if not pkg.active or pkg.providers is None:
            continue
        for p in pkg.providers.PROVIDERS:
            existing = merged.get(p.provider)
            if existing is None:
                merged[p.provider] = CatalogEntry(
                    provider=p.provider,
                    display_name=p.display_name,
                    category=p.category,
                    countries=[pkg.code],
                    auth_method=p.auth_method,
                    credential_fields=list(p.credential_fields),
                    live=p.live,
                )
            elif pkg.code not in existing.countries:
                merged[p.provider] = CatalogEntry(
                    provider=existing.provider,
                    display_name=existing.display_name,
                    category=existing.category,
                    countries=[*existing.countries, pkg.code],
                    auth_method=existing.auth_method,
                    credential_fields=existing.credential_fields,
                    live=existing.live,
                )

    # "custom" isn't a real financial provider any Country Package
    # defines - it's the escape hatch for a company using something
    # Orbit doesn't know about yet, so it's added once, for every
    # country every loaded package covers.
    all_countries = sorted(pkg.code for pkg in packages.values() if pkg.active)
    merged["custom"] = CatalogEntry(
        provider="custom",
        display_name="Custom Financial Provider",
        category="custom",
        countries=all_countries,
        auth_method="api_key",
        credential_fields=["api_key"],
    )

    return sorted(merged.values(), key=lambda e: (e.category, e.provider))


PROVIDER_CATALOG: list[CatalogEntry] = _build_catalog()

_BY_PROVIDER = {entry.provider: entry for entry in PROVIDER_CATALOG}


def get_catalog_entry(provider: str) -> CatalogEntry | None:
    return _BY_PROVIDER.get(provider)


def catalog_for_country(country_code: str | None) -> list[CatalogEntry]:
    if not country_code:
        return list(PROVIDER_CATALOG)
    return [e for e in PROVIDER_CATALOG if country_code.upper() in e.countries]
