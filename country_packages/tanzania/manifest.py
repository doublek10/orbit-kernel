"""
Tanzania Country Package - Manifest

Fourth Country Package built out against the Country Packages
Engineering Specification, same structure as Kenya's, Ghana's and
Uganda's. Read by the Plugin Manager before anything else in this
package is touched.
"""

from country_packages.manifest_schema import CountryManifest

PACKAGE_VERSION = "1.0.0"
MIN_KERNEL_VERSION = "1.0.0"

MANIFEST = CountryManifest(
    country_name="Tanzania",
    iso_code="TZ",
    package_version=PACKAGE_VERSION,
    currency="TZS",
    timezone="Africa/Dar_es_Salaam",
    locale="en-TZ",
    min_kernel_version=MIN_KERNEL_VERSION,
    # Fourth fully built-out Country Package - Tanzania is now offered
    # alongside Kenya, Ghana and Uganda at signup. Nigeria is next and
    # last in the initial rollout.
    active=True,
    feature_flags={
        "mobile_money": True,
        "bank_transfers": True,
        "payment_gateways": True,
        "crypto": True,
        "regulatory_monitoring": True,
    },
    supported_providers=[
        "mpesa_tz",
        "tigo_pesa",
        "halopesa",
        "airtel_money_tz",
        "crdb_bank",
        "nmb_bank",
        "flutterwave",
        "binance_pay",
        "mock_mobile_money",
        "custom",
    ],
    supported_integrations=["quickbooks", "zoho_books", "custom_erp"],
)
