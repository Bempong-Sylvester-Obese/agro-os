"""Single source of truth for subscription plans, bands, and pricing."""

SUBSCRIPTION_DAYS = 30

PLANS = {
    "starter": {
        "key": "starter",
        "track": "cooperative",
        "name": "Starter",
        "eyebrow": "For emerging cooperatives",
        "price": "Free",
        "cadence": "No card required",
        "description": "Establish a reliable digital member register and start collecting dues.",
        "features": [
            "Up to 10 members",
            "MoMo payment collection",
            "Member and dues dashboard",
            "100 SMS messages per month",
            "Email support",
        ],
        "cta": "Create free workspace",
        "bands": None,
    },
    "growth": {
        "key": "growth",
        "track": "cooperative",
        "name": "Growth",
        "eyebrow": "For operating cooperatives",
        "price": "GHS 299",
        "cadence": "per organisation / month",
        "description": "Run payments, credit workflows, communication, and field operations at scale.",
        "features": [
            "AgroCredit Trust Scores",
            "USSD access",
            "Unlimited payment records",
            "1,000 SMS messages per month",
            "Priority support",
        ],
        "cta": "Start Growth onboarding",
        "featured": True,
        "badge": "Most selected",
        "bands": [
            {"key": "base", "label": "Up to 50 members", "capacity": 50, "price": 299.0},
            {"key": "plus_50", "label": "Up to 100 members", "capacity": 100, "price": 449.0},
            {"key": "plus_100", "label": "Up to 200 members", "capacity": 200, "price": 599.0},
        ],
    },
    "enterprise": {
        "key": "enterprise",
        "track": "cooperative",
        "name": "Enterprise",
        "eyebrow": "For networks and institutions",
        "price": "Custom",
        "cadence": "Annual agreement",
        "description": "A governed rollout for unions, lenders, NGOs, and multi-cooperative programmes.",
        "features": [
            "Unlimited members",
            "Multi-cooperative administration",
            "Custom USSD and API access",
            "Migration and implementation support",
            "Dedicated account manager",
            "Contracted SLA",
        ],
        "cta": "Talk to enterprise sales",
        "bands": None,
    },
    "solo": {
        "key": "solo",
        "track": "farmer",
        "name": "Solo Farm",
        "eyebrow": "For independent farmers",
        "price": "GHS 99",
        "cadence": "per farm / month",
        "description": "Manage farm workers, track tasks and attendance, run payroll.",
        "features": [
            "Worker management",
            "Task management",
            "Attendance tracking",
            "Wage payroll",
            "200 SMS messages per month",
            "Worker USSD access",
        ],
        "cta": "Start Solo Farm onboarding",
        "bands": [
            {"key": "w20", "label": "Up to 20 workers", "capacity": 20, "price": 99.0},
            {"key": "w50", "label": "Up to 50 workers", "capacity": 50, "price": 199.0},
            {"key": "w100", "label": "Up to 100 workers", "capacity": 100, "price": 349.0},
            {"key": "custom", "label": "Custom worker count", "capacity": None, "price": None},
        ],
    },
}


def get_plan(plan_key: str) -> dict | None:
    """Return a plan definition by key (case-insensitive), or None."""
    return PLANS.get((plan_key or "").lower())


def get_band(plan_key: str, band_key: str | None = None) -> dict | None:
    """Return the selected band, defaulting only when no band was supplied."""
    plan = get_plan(plan_key)
    bands = plan.get("bands") if plan else None
    if not bands:
        return None
    if band_key is None:
        return bands[0]
    return next((band for band in bands if band["key"] == band_key), None)


def resolve_amount(plan_key: str, band_key: str | None = None) -> float | None:
    """Resolve a checkout amount for a plan + optional band.

    Returns None when the plan is not self-serve (free Starter, custom
    Enterprise, or the Solo Farm custom band).
    """
    band = get_band(plan_key, band_key)
    if not band:
        return None
    return band.get("price")
