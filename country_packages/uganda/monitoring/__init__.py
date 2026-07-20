"""
Uganda Country Package - Regulatory Intelligence / Monitoring

Per the spec, this service "never changes system behaviour directly...
instead it generates verified update proposals". check() stays honest
and returns no events until a real poller is attached - same contract
as Kenya's and Ghana's monitoring modules.
"""

from dataclasses import dataclass

TRUSTED_SOURCES = [
    {"name": "Bank of Uganda", "type": "central_bank", "url": "https://www.bou.or.ug"},
    {"name": "Uganda Revenue Authority", "type": "revenue_authority", "url": "https://www.ura.go.ug"},
    {"name": "Uganda Gazette", "type": "government_gazette", "url": "https://ulii.org"},
    {"name": "MTN MoMo Developer Docs", "type": "provider_documentation", "url": "https://momodeveloper.mtn.com"},
    {"name": "Uganda Communications Commission", "type": "financial_regulator", "url": "https://www.ucc.co.ug"},
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
