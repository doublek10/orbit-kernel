"""
Nigeria Country Package - Regulatory Intelligence / Monitoring

Per the spec, this service "never changes system behaviour directly...
instead it generates verified update proposals". check() stays honest
and returns no events until a real poller is attached - same contract
as every other Country Package's monitoring module.
"""

from dataclasses import dataclass

TRUSTED_SOURCES = [
    {"name": "Central Bank of Nigeria", "type": "central_bank", "url": "https://www.cbn.gov.ng"},
    {"name": "Federal Inland Revenue Service", "type": "revenue_authority", "url": "https://www.firs.gov.ng"},
    {"name": "Federal Government of Nigeria Gazette", "type": "government_gazette", "url": "https://gazettes.africa/archive/ng"},
    {"name": "NIBSS", "type": "financial_regulator", "url": "https://nibss-plc.com.ng"},
    {"name": "Corporate Affairs Commission", "type": "financial_regulator", "url": "https://www.cac.gov.ng"},
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
