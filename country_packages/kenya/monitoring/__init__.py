"""
Kenya Country Package - Regulatory Intelligence / Monitoring

Per the spec, this service "never changes system behaviour directly...
instead it generates verified update proposals". This module defines
the trusted sources this package would watch and the shape of a
Monitoring Event; it deliberately does not poll the network itself yet
(that's a live-integration concern for the Update Engine to wire up) -
check() always returns an empty list until a real poller is attached,
which is honest rather than fabricating "no changes found".
"""

from dataclasses import dataclass, field

TRUSTED_SOURCES = [
    {"name": "Central Bank of Kenya", "type": "central_bank", "url": "https://www.centralbank.go.ke"},
    {"name": "Kenya Revenue Authority", "type": "revenue_authority", "url": "https://www.kra.go.ke"},
    {"name": "Kenya Gazette", "type": "government_gazette", "url": "http://kenyalaw.org/kenya_gazette/"},
    {"name": "Safaricom Daraja Docs", "type": "provider_documentation", "url": "https://developer.safaricom.co.ke"},
    {"name": "Communications Authority of Kenya", "type": "financial_regulator", "url": "https://ca.go.ke"},
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
    """Placeholder for the live poller. Returns no events until this
    package is wired to a real monitoring job - never fabricates a
    "nothing changed" result from data it hasn't actually checked."""
    return []
