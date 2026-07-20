"""
The ExecutionContext is the single structure that flows through every
module in the Kernel (Request Router -> Company Resolver -> Permission
Engine -> Rule Engine -> Workflow Engine -> ...). No module invents its own
notion of "who is asking and on behalf of what company" - they all read
and enrich this same object.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionContext:
    # Identity - who is making the request (resolved from the Supabase token)
    user_id: str
    email: str | None = None

    # Company - which tenant this request operates within
    company_id: str | None = None
    company_name: str | None = None
    country: str | None = None

    # Permissions - what this identity may do within this company
    role: str | None = None
    permissions: list[str] = field(default_factory=list)

    # Request metadata
    request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": {"user_id": self.user_id, "email": self.email},
            "company": {
                "id": self.company_id,
                "name": self.company_name,
                "country": self.country,
            },
            "permissions": {"role": self.role, "grants": self.permissions},
            "request_id": self.request_id,
            "metadata": self.metadata,
        }
