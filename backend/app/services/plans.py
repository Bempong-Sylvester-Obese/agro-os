"""Plan catalog and pricing — single source of truth for all plan metadata."""

from datetime import datetime, timedelta

PLANS = {
    "starter": {
        "key": "starter",
        "track": "cooperative",
        "name": "Starter",
        "price": 0.0,
        "display_price": "Free",
        "currency": "GHS",
        "eyebrow": "For emerging cooperatives",
        "cadence": "No card required",
        "description": "Establish a reliable digital member register and start collecting dues.",
        "cta": "Create free workspace",
        "bands": None,
        "max_members": 10,
        "max_workers": 0,
        "sms_per_month": 100,
        "features": [
            "Up to 10 members",
            "MoMo payment collection",
            "Member and dues dashboard",
            "100 SMS messages per month",
            "Email support",
        ],
        "feature_keys": ["members", "payments", "dashboard"],
    },
    "solo": {
        "key": "solo",
        "track": "farmer",
        "name": "Solo Farm",
        "price": 99.0,
        "display_price": "GHS 99",
        "currency": "GHS",
        "eyebrow": "For independent farmers",
        "cadence": "per farm / month",
        "description": "Manage farm workers, track tasks and attendance, run payroll.",
        "cta": "Start Solo Farm onboarding",
        "bands": [
            {"key": "w20", "label": "Up to 20 workers", "capacity": 20, "price": 99.0},
            {"key": "w50", "label": "Up to 50 workers", "capacity": 50, "price": 199.0},
            {"key": "w100", "label": "Up to 100 workers", "capacity": 100, "price": 349.0},
            {"key": "custom", "label": "Custom worker count", "capacity": None, "price": None},
        ],
        "max_members": 0,
        "max_workers": 20,
        "sms_per_month": 200,
        "features": [
            "Worker management",
            "Task management",
            "Attendance tracking",
            "Wage payroll",
            "200 SMS messages per month",
            "Worker USSD access",
        ],
        "feature_keys": [
            "workers",
            "tasks",
            "attendance",
            "payroll",
            "farm_production",
            "ussd_worker",
        ],
    },
    "growth": {
        "key": "growth",
        "track": "cooperative",
        "name": "Growth",
        "price": 299.0,
        "display_price": "GHS 299",
        "currency": "GHS",
        "eyebrow": "For operating cooperatives",
        "cadence": "per organisation / month",
        "description": "Run payments, credit workflows, communication, and field operations at scale.",
        "cta": "Start Growth onboarding",
        "featured": True,
        "badge": "Most selected",
        "bands": [
            {"key": "base", "label": "Up to 50 members", "capacity": 50, "price": 299.0},
            {"key": "plus_50", "label": "Up to 100 members", "capacity": 100, "price": 449.0},
            {"key": "plus_100", "label": "Up to 200 members", "capacity": 200, "price": 599.0},
        ],
        "max_members": 500,
        "max_workers": 0,
        "sms_per_month": 1000,
        "features": [
            "AgroCredit Trust Scores",
            "USSD access",
            "Unlimited payment records",
            "1,000 SMS messages per month",
            "Priority support",
        ],
        "feature_keys": ["members", "payments", "loans", "scores", "commerce", "ussd", "sms"],
    },
    "enterprise": {
        "key": "enterprise",
        "track": "cooperative",
        "name": "Enterprise",
        "price": 0.0,  # custom pricing
        "display_price": "Custom",
        "currency": "GHS",
        "eyebrow": "For networks and institutions",
        "cadence": "Annual agreement",
        "description": "A governed rollout for unions, lenders, NGOs, and multi-cooperative programmes.",
        "cta": "Talk to enterprise sales",
        "bands": None,
        "max_members": 0,  # unlimited
        "max_workers": 0,  # unlimited
        "sms_per_month": 999999,
        "features": [
            "Unlimited members",
            "Multi-cooperative administration",
            "Custom USSD and API access",
            "Migration and implementation support",
            "Dedicated account manager",
            "Contracted SLA",
        ],
        "feature_keys": ["all"],
    },
}


def get_plan(plan_key: str) -> dict | None:
    return PLANS.get((plan_key or "").lower())


def get_plan_price(plan_key: str) -> float:
    plan = get_plan(plan_key) or {}
    return plan.get("price", 0.0)


def get_plan_limit(plan_key: str, limit: str) -> int:
    plan = get_plan(plan_key) or PLANS["starter"]
    return plan.get(limit, 0)


def get_plan_features(plan_key: str) -> list:
    plan = get_plan(plan_key) or {}
    return plan.get("feature_keys", [])


def has_feature(plan_key: str, feature: str) -> bool:
    features = get_plan_features(plan_key)
    return feature in features or "all" in features


def get_band(plan_key: str, band_key: str | None = None) -> dict | None:
    plan = get_plan(plan_key)
    bands = plan.get("bands") if plan else None
    if not bands:
        return None
    if band_key is None:
        return bands[0]
    return next((band for band in bands if band["key"] == band_key), None)


def resolve_amount(plan_key: str, band_key: str | None = None) -> float | None:
    band = get_band(plan_key, band_key)
    if not band:
        return None
    return band.get("price")


SUBSCRIPTION_STATUSES = ["trial", "active", "past_due", "expired", "cancelled"]


def activate_subscription(cooperative, plan_key: str, days: int = 30):
    cooperative.subscription_plan = plan_key
    cooperative.subscription_status = "active"
    if (
        cooperative.subscription_expires_at
        and cooperative.subscription_expires_at > datetime.utcnow()
    ):
        cooperative.subscription_expires_at += timedelta(days=days)
    else:
        cooperative.subscription_expires_at = datetime.utcnow() + timedelta(days=days)


def check_subscription_active(cooperative) -> bool:
    if (
        cooperative.subscription_status == "active"
        and cooperative.subscription_expires_at
    ):
        return datetime.utcnow() < cooperative.subscription_expires_at
    if cooperative.subscription_status == "trial":
        return True
    return False


def expire_if_needed(cooperative):
    if (
        cooperative.subscription_status == "active"
        and cooperative.subscription_expires_at
    ):
        if datetime.utcnow() > cooperative.subscription_expires_at:
            cooperative.subscription_status = "expired"
            return True
    return False
