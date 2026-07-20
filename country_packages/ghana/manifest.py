"""
Ghana Country Package - Manifest

Second Country Package built out against the Country Packages
Engineering Specification, same structure as Kenya's. Read by the
Plugin Manager before anything else in this package is touched.
"""

from country_packages.manifest_schema import CountryManifest

PACKAGE_VERSION = "1.0.0"
MIN_KERNEL_VERSION = "1.0.0"

MANIFEST = CountryManifest(
    country_name="Ghana",
    iso_code="GH",
    package_version=PACKAGE_VERSION,
    currency="GHS",
    timezone="Africa/Accra",
    locale="en-GH",
    min_kernel_version=MIN_KERNEL_VERSION,
    # Second fully built-out Country Package - Ghana is now offered
    # alongside Kenya at signup. Next up: Uganda, then Tanzania, then
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
        "mtn_momo_gh",
        "vodafone_cash",
        "airteltigo_money",
        "gcb_bank",
        "ecobank_gh",
        "paystack",
        "flutterwave",
        "binance_pay",
        "mock_mobile_money",
        "custom",
    ],
    supported_integrations=["quickbooks", "zoho_books", "custom_erp"],
)
