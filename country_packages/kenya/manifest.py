"""
Kenya Country Package - Manifest

Read by the Plugin Manager before anything else in this package is
touched (Plugin Manager -> "Read manifest.py" -> "Validate Compatibility"
-> "Register Package"). If MIN_KERNEL_VERSION is newer than the running
Kernel, or the manifest is missing a required field, the package is
rejected and the Kernel falls back to treating the country as
unavailable - it never partially loads a package.
"""

from country_packages.manifest_schema import CountryManifest

# Bump this on any change to providers/taxes/compliance/validation/etc in
# this package. Independent of every other Country Package's version
# (Design Principle #6 - every package follows the same structure, but
# each is versioned on its own timeline).
PACKAGE_VERSION = "1.0.0"

# The lowest orbit-kernel release this package is known to work against.
# The Plugin Manager refuses to load the package below this version.
MIN_KERNEL_VERSION = "1.0.0"

MANIFEST = CountryManifest(
    country_name="Kenya",
    iso_code="KE",
    package_version=PACKAGE_VERSION,
    currency="KES",
    timezone="Africa/Nairobi",
    locale="en-KE",
    min_kernel_version=MIN_KERNEL_VERSION,
    # First fully built-out Country Package - this is the only one the
    # Frontend should offer at signup until the next package (Uganda) is
    # built the same way.
    active=True,
    feature_flags={
        "mobile_money": True,
        "bank_transfers": True,
        "payment_gateways": True,
        "crypto": True,
        "regulatory_monitoring": True,
    },
    supported_providers=[
        "mpesa",
        "airtel_money",
        "kcb_bank",
        "equity_bank",
        "flutterwave",
        "binance_pay",
        "mock_mobile_money",
        "custom",
    ],
    supported_integrations=["quickbooks", "zoho_books", "custom_erp"],
)
