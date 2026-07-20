"""
Kenya Country Package - Automatic Update Engine

Turns a detected monitoring change into a versioned Update Proposal.
Applying/rolling back a proposal is deliberately out of scope here
(that belongs to the Kernel's Package Version Manager, which is
country-agnostic) - this module only knows how to *shape* a Kenya-package
change into the proposal format the Kernel expects.
"""

from dataclasses import dataclass, field

NOTIFICATION_MODES = ["notify_only", "approve_before_applying", "automatic_low_risk", "mandatory_regulatory"]


@dataclass(frozen=True)
class UpdateProposal:
    current_version: str
    proposed_version: str
    affected_modules: list[str]
    migration_notes: str
    risk_assessment: str  # low | medium | high
    rollback_plan: str
    breaking_changes: list[str] = field(default_factory=list)
    upgrade_instructions: str = ""


def build_proposal(
    *,
    current_version: str,
    proposed_version: str,
    affected_modules: list[str],
    migration_notes: str,
    risk_assessment: str,
    breaking_changes: list[str] | None = None,
) -> UpdateProposal:
    return UpdateProposal(
        current_version=current_version,
        proposed_version=proposed_version,
        affected_modules=affected_modules,
        migration_notes=migration_notes,
        risk_assessment=risk_assessment,
        rollback_plan=f"Restore country_packages/kenya at version {current_version}.",
        breaking_changes=breaking_changes or [],
        upgrade_instructions=f"Review {', '.join(affected_modules)} before approving.",
    )
