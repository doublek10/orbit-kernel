"""
Ghana Country Package - Regulatory Intelligence / Monitoring

Per the spec, this service "never changes system behaviour directly...
instead it generates verified update proposals". check() stays honest
and returns no events until a real poller is attached - same contract
as Kenya's monitoring module.
"""

from dataclasses import dataclass

TRUSTED_SOURCES = [
    {"name": "Bank of Ghana", "type": "central_bank", "url": "https://www.bog.gov.gh"},
    {"name": "Ghana Revenue Authority", "type": "revenue_authority", "url": "https://gra.gov.gh"},
    {"name": "Ghana Gazette", "type": "government_gazette", "url": "https://www.ghanagazette.com.gh"},
    {"name": "MTN MoMo Developer Docs", "type": "provider_documentation", "url": "https://momodeveloper.mtn.com"},
    {"name": "National Communications Authority", "type": "financial_regulator", "url": "https://nca.org.gh"},
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
