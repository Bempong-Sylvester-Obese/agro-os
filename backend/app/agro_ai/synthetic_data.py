"""Synthetic farmer data for the Agro-AI hackathon model."""

from __future__ import annotations

import random
from typing import Any

FEATURE_NAMES = [
    "dues_payment_rate",
    "on_time_payment_rate",
    "yield_performance",
    "attendance_rate",
    "acreage",
    "cooperative_tenure_months",
    "prior_loans_repaid",
    "outstanding_balance_ratio",
    "savings_rate",
]


DEMO_FARMERS: list[dict[str, Any]] = [
    {
        "farmer_id": "GH-0103",
        "name": "Kofi Darko",
        "phone": "020 773 xxxx",
        "region": "Brong-Ahafo",
        "crop": "Cocoa",
        "dues_status": "Paid",
        "requested_credit_amount": 4200,
        "previous_score": 88,
        "features": {
            "dues_payment_rate": 0.98,
            "on_time_payment_rate": 0.94,
            "yield_performance": 0.91,
            "attendance_rate": 0.88,
            "acreage": 5.4,
            "cooperative_tenure_months": 64,
            "prior_loans_repaid": 4,
            "outstanding_balance_ratio": 0.08,
            "savings_rate": 0.72,
        },
    },
    {
        "farmer_id": "GH-0042",
        "name": "Abena Mensah",
        "phone": "055 234 xxxx",
        "region": "Ashanti",
        "crop": "Maize",
        "dues_status": "Paid",
        "requested_credit_amount": 3500,
        "previous_score": 72,
        "features": {
            "dues_payment_rate": 0.93,
            "on_time_payment_rate": 0.88,
            "yield_performance": 0.86,
            "attendance_rate": 0.84,
            "acreage": 4.1,
            "cooperative_tenure_months": 38,
            "prior_loans_repaid": 2,
            "outstanding_balance_ratio": 0.18,
            "savings_rate": 0.62,
        },
    },
    {
        "farmer_id": "GH-0128",
        "name": "Yaw Frimpong",
        "phone": "050 362 xxxx",
        "region": "Volta",
        "crop": "Chickens",
        "production_focus": "animal",
        "animal_type": "Chickens",
        "animal_scale": 180,
        "dues_status": "Paid",
        "requested_credit_amount": 2800,
        "previous_score": 76,
        "features": {
            "dues_payment_rate": 0.82,
            "on_time_payment_rate": 0.76,
            "yield_performance": 0.79,
            "attendance_rate": 0.74,
            "acreage": 3.2,
            "cooperative_tenure_months": 29,
            "prior_loans_repaid": 1,
            "outstanding_balance_ratio": 0.22,
            "savings_rate": 0.48,
        },
    },
    {
        "farmer_id": "GH-0081",
        "name": "Kwame Asante",
        "phone": "024 891 xxxx",
        "region": "Northern",
        "crop": "Sorghum",
        "dues_status": "Paid",
        "requested_credit_amount": 3000,
        "previous_score": 71,
        "features": {
            "dues_payment_rate": 0.78,
            "on_time_payment_rate": 0.7,
            "yield_performance": 0.74,
            "attendance_rate": 0.68,
            "acreage": 3.8,
            "cooperative_tenure_months": 24,
            "prior_loans_repaid": 1,
            "outstanding_balance_ratio": 0.3,
            "savings_rate": 0.42,
        },
    },
    {
        "farmer_id": "GH-0017",
        "name": "Ama Osei",
        "phone": "059 441 xxxx",
        "region": "Greater Accra",
        "crop": "Vegetables + Goats",
        "production_focus": "mixed",
        "animal_type": "Goats",
        "animal_scale": 14,
        "dues_status": "Pending",
        "requested_credit_amount": 2400,
        "previous_score": 63,
        "features": {
            "dues_payment_rate": 0.64,
            "on_time_payment_rate": 0.58,
            "yield_performance": 0.67,
            "attendance_rate": 0.62,
            "acreage": 2.1,
            "cooperative_tenure_months": 14,
            "prior_loans_repaid": 0,
            "outstanding_balance_ratio": 0.36,
            "savings_rate": 0.29,
        },
    },
    {
        "farmer_id": "GH-0056",
        "name": "Akosua Boateng",
        "phone": "026 558 xxxx",
        "region": "Eastern",
        "crop": "Cassava",
        "dues_status": "Overdue",
        "requested_credit_amount": 2200,
        "previous_score": 45,
        "features": {
            "dues_payment_rate": 0.42,
            "on_time_payment_rate": 0.36,
            "yield_performance": 0.51,
            "attendance_rate": 0.44,
            "acreage": 1.7,
            "cooperative_tenure_months": 9,
            "prior_loans_repaid": 0,
            "outstanding_balance_ratio": 0.68,
            "savings_rate": 0.18,
        },
    },
]


def generate_training_rows(count: int = 360) -> list[dict[str, Any]]:
    """Generate deterministic agritech-like rows for model training."""

    rng = random.Random(42)
    rows: list[dict[str, Any]] = []

    for index in range(count):
        tenure = rng.randint(3, 84)
        acreage = round(rng.uniform(0.8, 7.5), 1)
        dues_rate = rng.betavariate(4.5, 1.8)
        on_time_rate = max(0, min(1, dues_rate - rng.uniform(-0.1, 0.2)))
        yield_performance = rng.betavariate(4.0, 2.2)
        attendance_rate = rng.betavariate(3.4, 2.2)
        prior_loans_repaid = rng.randint(0, 5)
        outstanding_balance_ratio = rng.betavariate(1.7, 4.8)
        savings_rate = rng.betavariate(3.2, 2.8)

        row = {
            "farmer_id": f"SYN-{index + 1:04d}",
            "features": {
                "dues_payment_rate": round(dues_rate, 3),
                "on_time_payment_rate": round(on_time_rate, 3),
                "yield_performance": round(yield_performance, 3),
                "attendance_rate": round(attendance_rate, 3),
                "acreage": acreage,
                "cooperative_tenure_months": tenure,
                "prior_loans_repaid": prior_loans_repaid,
                "outstanding_balance_ratio": round(outstanding_balance_ratio, 3),
                "savings_rate": round(savings_rate, 3),
            },
        }
        row["eligible"] = _label_from_features(row["features"], rng)
        rows.append(row)

    return rows


def _label_from_features(features: dict[str, float], rng: random.Random) -> int:
    score = (
        features["dues_payment_rate"] * 24
        + features["on_time_payment_rate"] * 20
        + features["yield_performance"] * 18
        + features["attendance_rate"] * 12
        + min(features["cooperative_tenure_months"] / 60, 1) * 8
        + min(features["prior_loans_repaid"] / 4, 1) * 7
        + features["savings_rate"] * 6
        - features["outstanding_balance_ratio"] * 15
        + min(features["acreage"] / 6, 1) * 5
    )
    score += rng.uniform(-4, 4)
    return int(score >= 62)
