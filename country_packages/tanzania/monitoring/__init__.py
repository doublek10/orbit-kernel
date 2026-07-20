"""
Tanzania Country Package - Regulatory Intelligence / Monitoring

Per the spec, this service "never changes system behaviour directly...
instead it generates verified update proposals". check() stays honest
and returns no events until a real poller is attached - same contract
as Kenya's, Ghana's and Uganda's monitoring modules.
"""

from dataclasses import dataclass

TRUSTED_SOURCES = [
    {"name": "Bank of Tanzania", "type": "central_bank", "url": "https://www.bot.go.tz"},
    {"name": "Tanzania Revenue Authority", "type": "revenue_authority", "url": "https://www.tra.go.tz"},
    {"name": "Tanzania Gazette", "type": "government_gazette", "url": "https://www.gazettes.africa/archive/tz"},
    {"name": "Vodacom M-Pesa Developer Docs", "type": "provider_documentation", "url": "https://openapiportal.m-pesa.com"},
    {"name": "Tanzania Communications Regulatory Authority", "type": "financial_regulator", "url": "https://www.tcra.go.tz"},
]

MONITORED_CHANGE_TYPES = [
    "provider_api_change",
    "webhook_change",
    "authentication_update",
    "tax_update",
    "compliance_change",
    "bank_addition",
    "bank_removal",
    "currency_change",
    "provider_deprecation",
    "government_notice",
]


@dataclass(frozen=True)
class MonitoringEvent:
    change_type: str
    source: str
    summary: str
    detected_at: str


def check() -> list[MonitoringEvent]:
    """Placeholder for the live poller - returns no events until this
    package is wired to a real monitoring job."""
    return []
