"""Formal role model for staff accounts (#244).

Every ``require_roles(...)`` gate in ``app/routes`` uses one of these values, and
the invite / update schemas accept exactly this set, so the roles an operator
can grant are the roles the API actually enforces. The frontend mirrors this
catalogue in ``frontend/src/utils/roles.js``; keep the two in sync.

Roles are split by organisation track:

* ``COOP_ROLES`` — cooperative staff.
* ``SOLO_ROLES`` — solo-farm staff (owner / manager / supervisor).

``admin`` belongs to both: it is the account created at signup and the only
role that can manage team access, billing, and cooperative settings.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal


class Role(str, Enum):
    ADMIN = "admin"
    FINANCE_OFFICER = "finance_officer"
    FIELD_OFFICER = "field_officer"
    OPERATIONS_OFFICER = "operations_officer"
    SALES_OFFICER = "sales_officer"
    FARM_OWNER = "farm_owner"
    FARM_MANAGER = "farm_manager"
    SUPERVISOR = "supervisor"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


RoleLiteral = Literal[
    "admin",
    "finance_officer",
    "field_officer",
    "operations_officer",
    "sales_officer",
    "farm_owner",
    "farm_manager",
    "supervisor",
]

ALL_ROLES: frozenset[str] = frozenset(role.value for role in Role)

COOP_ROLES: frozenset[str] = frozenset(
    {
        Role.ADMIN.value,
        Role.FINANCE_OFFICER.value,
        Role.FIELD_OFFICER.value,
        Role.OPERATIONS_OFFICER.value,
        Role.SALES_OFFICER.value,
    }
)

SOLO_ROLES: frozenset[str] = frozenset(
    {
        Role.ADMIN.value,
        Role.FARM_OWNER.value,
        Role.FARM_MANAGER.value,
        Role.SUPERVISOR.value,
    }
)

ROLE_LABELS: dict[str, str] = {
    Role.ADMIN.value: "Administrator",
    Role.FINANCE_OFFICER.value: "Finance officer",
    Role.FIELD_OFFICER.value: "Field officer",
    Role.OPERATIONS_OFFICER.value: "Operations officer",
    Role.SALES_OFFICER.value: "Sales officer",
    Role.FARM_OWNER.value: "Farm owner",
    Role.FARM_MANAGER.value: "Farm manager",
    Role.SUPERVISOR.value: "Supervisor",
}

# Human-readable summary of what each role may mutate. Reads are open to every
# authenticated staff account within their cooperative; this describes the
# ``require_roles`` gates on write paths.
ROLE_CAPABILITIES: dict[str, str] = {
    Role.ADMIN.value: "Everything: team, billing, settings, members, finance, commerce, communications",
    Role.FINANCE_OFFICER.value: "Payments, loans, settlements, buyers/sales, SMS and announcements",
    Role.FIELD_OFFICER.value: "Produce intake and aggregation batches",
    Role.OPERATIONS_OFFICER.value: "Produce intake and aggregation batches",
    Role.SALES_OFFICER.value: "Buyers and buyer sales",
    Role.FARM_OWNER.value: "Workers, tasks, attendance, payroll and farm production",
    Role.FARM_MANAGER.value: "Workers, tasks, attendance, payroll runs and farm production",
    Role.SUPERVISOR.value: "Attendance only",
}


def roles_for_track(organization_type: str | None) -> frozenset[str]:
    """Roles that may be granted inside an organisation of the given type."""
    if organization_type == "solo_farm":
        return SOLO_ROLES
    return COOP_ROLES


def is_valid_role(value: str | None) -> bool:
    return (value or "").lower() in ALL_ROLES
