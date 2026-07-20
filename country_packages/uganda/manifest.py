"""
Uganda Country Package - Manifest

Third Country Package built out against the Country Packages
Engineering Specification, same structure as Kenya's and Ghana's. Read
by the Plugin Manager before anything else in this package is touched.
"""

from country_packages.manifest_schema import CountryManifest

PACKAGE_VERSION = "1.0.0"
MIN_KERNEL_VERSION = "1.0.0"

MANIFEST = CountryManifest(
    country_name="Uganda",
    iso_code="UG",
    package_version=PACKAGE_VERSION,
    currency="UGX",
    timezone="Africa/Kampala",
    locale="en-UG",
    min_kernel_version=MIN_KERNEL_VERSION,
    # Third fully built-out Country Package - Uganda is now offered
    # alongside Kenya and Ghana at signup. Next up: Tanzania, then
    # Nigeria.
    active=True,
    feature_flags={
        "mobile_money": True,
        "bank_transfers": True,
        "payment_gateways": True,
        "crypto": True,
        "regulatory_monitoring": True,
    },
    supported_providers=[
        "mtn_momo_ug",
        "airtel_money_ug",
        "stanbic_bank_ug",
        "centenary_bank",
        "flutterwave",
        "binance_pay",
        "mock_mobile_money",
        "custom",
    ],
    supported_integrations=["quickbooks", "zoho_books", "custom_erp"],
)
