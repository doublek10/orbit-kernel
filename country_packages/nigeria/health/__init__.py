"""
Nigeria Country Package - Health

Package-level integrity check, same contract as every other Country
Package's health module.
"""

from dataclasses import dataclass

from country_packages.nigeria import manifest as _manifest
from country_packages.nigeria.providers import PROVIDERS


@dataclass(frozen=True)
class PackageHealth:
    healthy: bool
    package_version: str
    provider_count: int
    issues: list[str]


def check_package_health() -> PackageHealth:
    issues: list[str] = []
    if not _manifest.MANIFEST.active:
        issues.append("package is marked inactive in its manifest")
    if not PROVIDERS:
        issues.append("no providers defined")

    return PackageHealth(
        healthy=len(issues) == 0,
        package_version=_manifest.MANIFEST.package_version,
        provider_count=len(PROVIDERS),
        issues=issues,
    )
