"""Plan catalog and pricing — single source of truth for all plan metadata."""

from datetime import datetime, timedelta

PLANS = {
    "starter": {
        "name": "Starter",
        "price": 0.0,
        "currency": "GHS",
        "max_members": 10,
        "max_workers": 0,
        "sms_per_month": 100,
        "features": ["members", "payments", "dashboard"],
    },
    "solo": {
        "name": "Solo Farm",
        "price": 99.0,
        "currency": "GHS",
        "max_members": 0,
        "max_workers": 20,
        "sms_per_month": 200,
        "features": [
            "workers",
            "tasks",
            "attendance",
            "payroll",
            "farm_production",
            "ussd_worker",
        ],
    },
    "growth": {
        "name": "Growth",
        "price": 299.0,
        "currency": "GHS",
        "max_members": 500,
        "max_workers": 0,
        "sms_per_month": 1000,
        "features": [
            "members",
            "payments",
            "loans",
            "scores",
            "commerce",
            "ussd",
            "sms",
        ],
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 0.0,  # custom pricing
        "currency": "GHS",
        "max_members": 0,  # unlimited
        "max_workers": 0,  # unlimited
        "sms_per_month": 999999,
        "features": ["all"],
    },
}


def get_plan(plan_key: str) -> dict | None:
    return PLANS.get((plan_key or "").lower())


def get_plan_price(plan_key: str) -> float:
    plan = PLANS.get(plan_key, {})
    return plan.get("price", 0.0)


def get_plan_limit(plan_key: str, limit: str) -> int:
    plan = get_plan(plan_key) or PLANS["starter"]
    return plan.get(limit, 0)


def get_plan_features(plan_key: str) -> list:
    plan = PLANS.get(plan_key, {})
    return plan.get("features", [])


def has_feature(plan_key: str, feature: str) -> bool:
    features = get_plan_features(plan_key)
    return feature in features or "all" in features


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
