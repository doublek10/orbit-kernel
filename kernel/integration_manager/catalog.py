"""
Business Systems Catalog

Static reference data for the Business Systems Connection Manager - the
spec's second connection surface, distinct from Financial Connections
(kernel/provider_manager/catalog.py). Financial Connections is "where a
company's money moves"; Business Systems is "the other software a
company already runs its operations on" - payroll, accounting,
inventory, CRM, ERP, warehouse, POS, HR.

Same honesty contract as the Financial Connections catalog: nothing here
has a real adapter (`live` is always False for now), so connecting one
stores the company's own encrypted credentials and Test Connection only
checks the declared credential fields are present. No fabricated sync,
no fabricated "verified".
"""

from dataclasses import dataclass, field

SYSTEM_TYPES = [
    "payroll",
    "accounting",
    "inventory",
    "crm",
    "erp",
    "warehouse",
    "pos",
    "hr",
    "custom",
]


@dataclass(frozen=True)
class IntegrationCatalogEntry:
    provider: str
    display_name: str
    system_type: str
    auth_method: str  # api_key | oauth
    credential_fields: list[str] = field(default_factory=list)
    live: bool = False


INTEGRATION_CATALOG: list[IntegrationCatalogEntry] = [
    IntegrationCatalogEntry(
        provider="workpay",
        display_name="Workpay",
        system_type="payroll",
        auth_method="api_key",
        credential_fields=["api_key"],
    ),
    IntegrationCatalogEntry(
        provider="payspace",
        display_name="PaySpace",
        system_type="payroll",
        auth_method="api_key",
        credential_fields=["api_key", "company_code"],
    ),
    IntegrationCatalogEntry(
        provider="quickbooks",
        display_name="QuickBooks",
        system_type="accounting",
        auth_method="oauth",
        credential_fields=["client_id", "client_secret"],
    ),
    IntegrationCatalogEntry(
        provider="xero",
        display_name="Xero",
        system_type="accounting",
        auth_method="oauth",
        credential_fields=["client_id", "client_secret"],
    ),
    IntegrationCatalogEntry(
        provider="zoho_books",
        display_name="Zoho Books",
        system_type="accounting",
        auth_method="api_key",
        credential_fields=["api_key", "organization_id"],
    ),
    IntegrationCatalogEntry(
        provider="zoho_inventory",
        display_name="Zoho Inventory",
        system_type="inventory",
        auth_method="api_key",
        credential_fields=["api_key", "organization_id"],
    ),
    IntegrationCatalogEntry(
        provider="cin7",
        display_name="Cin7",
        system_type="inventory",
        auth_method="api_key",
        credential_fields=["api_key"],
    ),
    IntegrationCatalogEntry(
        provider="hubspot",
        display_name="HubSpot",
        system_type="crm",
        auth_method="api_key",
        credential_fields=["api_key"],
    ),
    IntegrationCatalogEntry(
        provider="salesforce",
        display_name="Salesforce",
        system_type="crm",
        auth_method="oauth",
        credential_fields=["client_id", "client_secret"],
    ),
    IntegrationCatalogEntry(
        provider="zoho_crm",
        display_name="Zoho CRM",
        system_type="crm",
        auth_method="api_key",
        credential_fields=["api_key", "organization_id"],
    ),
    IntegrationCatalogEntry(
        provider="odoo",
        display_name="Odoo",
        system_type="erp",
        auth_method="api_key",
        credential_fields=["api_key", "database"],
    ),
    IntegrationCatalogEntry(
        provider="sap_business_one",
        display_name="SAP Business One",
        system_type="erp",
        auth_method="api_key",
        credential_fields=["api_key", "company_db"],
    ),
    IntegrationCatalogEntry(
        provider="cin7_warehouse",
        display_name="Cin7 Warehouse",
        system_type="warehouse",
        auth_method="api_key",
        credential_fields=["api_key"],
    ),
    IntegrationCatalogEntry(
        provider="square",
        display_name="Square POS",
        system_type="pos",
        auth_method="oauth",
        credential_fields=["client_id", "client_secret"],
    ),
    IntegrationCatalogEntry(
        provider="lightspeed",
        display_name="Lightspeed",
        system_type="pos",
        auth_method="api_key",
        credential_fields=["api_key"],
    ),
    IntegrationCatalogEntry(
        provider="bamboohr",
        display_name="BambooHR",
        system_type="hr",
        auth_method="api_key",
        credential_fields=["api_key", "subdomain"],
    ),
    IntegrationCatalogEntry(
        provider="workday",
        display_name="Workday",
        system_type="hr",
        auth_method="oauth",
        credential_fields=["client_id", "client_secret"],
    ),
    IntegrationCatalogEntry(
        provider="custom_system",
        display_name="Custom Business System",
        system_type="custom",
        auth_method="api_key",
        credential_fields=["api_key"],
    ),
]

_BY_PROVIDER = {entry.provider: entry for entry in INTEGRATION_CATALOG}


def get_catalog_entry(provider: str) -> IntegrationCatalogEntry | None:
    return _BY_PROVIDER.get(provider)


def catalog_for_type(system_type: str | None) -> list[IntegrationCatalogEntry]:
    if not system_type:
        return list(INTEGRATION_CATALOG)
    return [e for e in INTEGRATION_CATALOG if e.system_type == system_type]
