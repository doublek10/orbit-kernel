"""
Nigeria Country Package - Manifest

Fifth and last Country Package in the initial rollout, built out
against the Country Packages Engineering Specification, same structure
as Kenya's, Ghana's, Uganda's and Tanzania's. Read by the Plugin
Manager before anything else in this package is touched.
"""

from country_packages.manifest_schema import CountryManifest

PACKAGE_VERSION = "1.0.0"
MIN_KERNEL_VERSION = "1.0.0"

MANIFEST = CountryManifest(
    country_name="Nigeria",
    iso_code="NG",
    package_version=PACKAGE_VERSION,
    currency="NGN",
    timezone="Africa/Lagos",
    locale="en-NG",
    min_kernel_version=MIN_KERNEL_VERSION,
    # Fifth and final Country Package of the initial rollout - Nigeria
    # is now offered alongside Kenya, Ghana, Uganda and Tanzania at
    # signup.
    active=True,
    feature_flags={
        "mobile_money": True,
        "bank_transfers": True,
        "payment_gateways": True,
        "crypto": True,
        "regulatory_monitoring": True,
    },
    supported_providers=[
        "opay",
        "palmpay",
        "paga",
        "gtbank",
        "access_bank",
        "zenith_bank",
        "paystack",
        "flutterwave",
        "binance_pay",
        "mock_mobile_money",
        "custom",
    ],
    supported_integrations=["quickbooks", "zoho_books", "custom_erp"],
)
