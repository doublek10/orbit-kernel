"""
Shared Country Manifest shape.

Every `country_packages/{country}/manifest.py` builds one `MANIFEST`
instance of this dataclass. Defined once here (rather than duplicated
per package) so `country_packages/loader.py` validates every package
against the exact same required fields, and adding a field only means
touching this one file plus each manifest's literal values - never the
Loader or Plugin Manager.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CountryManifest:
    country_name: str
    iso_code: str  # ISO 3166-1 alpha-2
    package_version: str
    currency: str  # ISO 4217
    timezone: str
    locale: str
    min_kernel_version: str
    active: bool
    feature_flags: dict[str, bool] = field(default_factory=dict)
    supported_providers: list[str] = field(default_factory=list)
    supported_integrations: list[str] = field(default_factory=list)
