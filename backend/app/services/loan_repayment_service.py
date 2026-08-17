"""Loan repayment domain service — thin re-export from routes/loans.py.

This module exists so that consumers (webhooks, USSD gateways) can
import shared loan-repayment logic from a service module instead of
directly from a route module, breaking cross-route import chains.
"""
from app.routes.loans import (
    resume_loan_repayment_customer_action,
    start_farmer_loan_repayment,
)

__all__ = [
    "resume_loan_repayment_customer_action",
    "start_farmer_loan_repayment",
]
