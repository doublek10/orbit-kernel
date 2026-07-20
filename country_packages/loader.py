"""
Country Package Loader

The concrete implementation of the spec's "Country Package Loader" step:

    Plugin Manager -> Scan country_packages/ -> Read manifest.py
    -> Validate Compatibility -> Register Package

This module only *discovers and validates* packages - it never decides
who gets to use one (that's the Company Resolver reading
`company.country`) and it never executes business logic (that's the
Rule/Workflow Engines, fed by whatever this loader hands back).

A package is only ever "loaded" (usable end-to-end - providers, taxes,
compliance, defaults, etc, per Design Principle #6) when its manifest
sets `active = True`. Every folder under `country_packages/` is still
*discovered* and appears in `list_manifests()` regardless of `active`,
so the Frontend can show "coming soon" countries without the Kernel
ever treating them as usable.
"""

import importlib
import pkgutil
from dataclasses import dataclass, field
from types import ModuleType

import country_packages
from country_packages.manifest_schema import CountryManifest

KERNEL_VERSION = "1.0.0"


class PackageLoadError(ValueError):
    """Raised when a Country Package's manifest is missing, malformed,
    or incompatible with the running Kernel version."""


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.split("."))


@dataclass(frozen=True)
class LoadedCountryPackage:
    """Everything the Kernel needs from one Country Package, aggregated
    behind a single object - this is what the Plugin Manager hands to
    the Provider Manager, Rule Engine, Event Engine and Mapping Engine
    once a company's country has been resolved."""

    manifest: CountryManifest
    module_path: str
    providers: ModuleType | None = None
    banking: ModuleType | None = None
    mobile_money: ModuleType | None = None
    payment_gateways: ModuleType | None = None
    crypto: ModuleType | None = None
    taxes: ModuleType | None = None
    compliance: ModuleType | None = None
    currencies: ModuleType | None = None
    validation: ModuleType | None = None
    workflows: ModuleType | None = None
    mappings: ModuleType | None = None
    events: ModuleType | None = None
    defaults: ModuleType | None = None
    localization: ModuleType | None = None
    monitoring: ModuleType | None = None
    updater: ModuleType | None = None
    health: ModuleType | None = None

    @property
    def code(self) -> str:
        return self.manifest.iso_code

    @property
    def active(self) -> bool:
        return self.manifest.active


_SUBMODULES = (
    "providers", "banking", "mobile_money", "payment_gateways", "crypto",
    "taxes", "compliance", "currencies", "validation", "workflows",
    "mappings", "events", "defaults", "localization", "monitoring",
    "updater", "health",
)


def _discover_package_dirs() -> list[str]:
    return sorted(
        name for _, name, is_pkg in pkgutil.iter_modules(country_packages.__path__)
        if is_pkg
    )


def _validate_manifest(manifest: CountryManifest, dir_name: str) -> None:
    required = ["country_name", "iso_code", "package_version", "currency", "min_kernel_version"]
    for field_name in required:
        if not getattr(manifest, field_name, None):
            raise PackageLoadError(f"{dir_name}: manifest is missing required field '{field_name}'")

    if _version_tuple(manifest.min_kernel_version) > _version_tuple(KERNEL_VERSION):
        raise PackageLoadError(
            f"{dir_name}: requires Kernel >= {manifest.min_kernel_version}, running {KERNEL_VERSION}"
        )


def load_package(dir_name: str) -> LoadedCountryPackage:
    """Reads manifest.py, validates compatibility, imports every
    standard submodule the package has (a not-yet-built package like
    uganda/ simply won't have most of them - that's fine, those fields
    stay None rather than erroring the whole load)."""
    module_path = f"country_packages.{dir_name}"
    try:
        manifest_mod = importlib.import_module(f"{module_path}.manifest")
    except ModuleNotFoundError as exc:
        raise PackageLoadError(f"{dir_name}: no manifest.py found") from exc

    manifest = getattr(manifest_mod, "MANIFEST", None)
    if manifest is None:
        raise PackageLoadError(f"{dir_name}: manifest.py does not define MANIFEST")

    _validate_manifest(manifest, dir_name)

    submodules: dict[str, ModuleType | None] = {}
    for name in _SUBMODULES:
        try:
            submodules[name] = importlib.import_module(f"{module_path}.{name}")
        except ModuleNotFoundError:
            submodules[name] = None

    return LoadedCountryPackage(manifest=manifest, module_path=module_path, **submodules)


def load_all_packages() -> dict[str, LoadedCountryPackage]:
    """Scans every folder under country_packages/, loads what it can,
    and never lets one broken/unfinished package take the others down
    with it - a load failure is logged onto the package's own entry
    instead of raised, so `uganda/` being a stub never breaks `kenya/`."""
    packages: dict[str, LoadedCountryPackage] = {}
    for dir_name in _discover_package_dirs():
        try:
            pkg = load_package(dir_name)
        except PackageLoadError:
            continue
        packages[pkg.code] = pkg
    return packages
