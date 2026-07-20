"""
Marketplace Catalog

First-party modules only, for now - there's no third-party developer
submission/review pipeline yet (that needs the Plugin Manager to
actually sandbox and permission-scope external code, which is still a
stub). This is an honest, working slice of the marketplace concept:
companies can install/uninstall real modules and the rest of the
platform can check `company_installed_apps` to change behavior
accordingly, wired the same way a submitted third-party app would be
once that pipeline exists.
"""

CATALOG = [
    {
        "app_key": "anomaly-alerts",
        "name": "Anomaly Alerts",
        "category": "intelligence",
        "description": "Surfaces unusual transactions from your ledger as they're flagged by the Rule Engine.",
    },
    {
        "app_key": "automation-pack",
        "name": "Automation Starter Pack",
        "category": "automation",
        "description": "A set of ready-made Workflow automations for common patterns (large payments, low balance).",
    },
    {
        "app_key": "csv-export",
        "name": "CSV Export",
        "category": "reporting",
        "description": "Export your Financial Graph timeline for spreadsheets and external accounting tools.",
    },
    {
        "app_key": "audit-trail-pro",
        "name": "Audit Trail Pro",
        "category": "compliance",
        "description": "Extended retention and search over your company's audit log, for compliance reviews.",
    },
]
