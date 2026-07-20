from fastapi import APIRouter, Form, Depends, Request, Response
from sqlalchemy.orm import Session
import logging

from app.database.db import get_db
from app.models.models import Farmer, CooperativeMembership, Cooperative, Loan, LoanStatus
from app.services.membership_service import resolve_phone_membership
from app.routes.transactions import _run_dues_collect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ussd", tags=["ussd"])

@router.post("/callback")
async def ussd_callback(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(""),
    db: Session = Depends(get_db)
):
    """
    Native USSD Gateway Router using Africa's Talking format.
    State is managed by the `text` string which contains inputs separated by '*'.
    """
    inputs = text.split("*") if text else []
    
    # 1. Resolve phone membership
    farmer, memberships = resolve_phone_membership(phoneNumber, db)
    
    if not farmer:
        # User is not registered yet. Enter Hybrid Onboarding flow.
        if len(inputs) == 0:
            return Response(content="CON Welcome to AgroOS.\nEnter your 4-digit Cooperative Code:", media_type="text/plain")
        elif len(inputs) == 1:
            return Response(content="CON Enter your 6-digit Farmer ID:", media_type="text/plain")
        elif len(inputs) == 2:
            coop_code = inputs[0]
            farmer_code = inputs[1]
            
            # Find the cooperative
            coop = db.query(Cooperative).filter(Cooperative.ussd_code == coop_code).first()
            if not coop:
                return Response(content="END Invalid Cooperative Code. Please try again.", media_type="text/plain")
                
            # Find the membership
            membership = db.query(CooperativeMembership).filter(
                CooperativeMembership.cooperative_id == coop.id,
                CooperativeMembership.farmer_code == farmer_code
            ).first()
            
            if not membership:
                return Response(content="END Invalid Farmer ID. Please try again.", media_type="text/plain")
                
            # Valid codes! Link the phone number
            farmer_obj = db.query(Farmer).filter(Farmer.id == membership.farmer_id).first()
            if farmer_obj:
                # Replace phone number with the new one securely
                farmer_obj.phone = phoneNumber
                db.commit()
                return Response(content="END Phone linked successfully!\nPlease dial the code again to access your account.", media_type="text/plain")
            else:
                return Response(content="END System error. Farmer not found.", media_type="text/plain")
        else:
            return Response(content="END Invalid input.", media_type="text/plain")

    # 2. Main Menu Logic (Farmer is recognized)
    if len(inputs) == 0:
        return Response(content=f"CON Welcome {farmer.name}!\n1. Pay Dues\n2. Request Loan\n3. Repay Loan\n4. Check Balance", media_type="text/plain")
        
    menu_selection = inputs[0]
    
    if menu_selection == "1":
        # Pay Dues
        if len(inputs) == 1:
            return Response(content="CON Enter amount to pay (GHS):", media_type="text/plain")
        elif len(inputs) == 2:
            amount_raw = inputs[1]
            try:
                amount = float(amount_raw)
            except ValueError:
                return Response(content="END Invalid amount.", media_type="text/plain")
                
            import uuid
            external_ref = str(uuid.uuid4())
            
            # Use existing logic
            result = await _run_dues_collect(
                farmer=farmer,
                amount=amount,
                channel="13", # Moolre generic mobile money channel
                description="Cooperative dues (USSD)",
                external_ref=external_ref,
                otp_code=None,
                db=db,
                initiation_channel="ussd_native",
            )
            
            return Response(content="END Please approve the Moolre payment prompt on your phone to complete your dues payment.", media_type="text/plain")
            
    elif menu_selection == "2":
        # Request Loan
        if len(inputs) == 1:
            return Response(content="CON Enter loan amount to request (GHS):", media_type="text/plain")
        elif len(inputs) == 2:
            amount_raw = inputs[1]
            try:
                amount = float(amount_raw)
            except ValueError:
                return Response(content="END Invalid amount.", media_type="text/plain")
                
            from app.services.loan_request_service import create_farmer_loan_request, PendingLoanRequestError
            try:
                membership = memberships[0] # Simplification
                create_farmer_loan_request(farmer.id, membership.cooperative_id, amount, db)
                return Response(content=f"END Loan request for GHS {amount} submitted successfully for review.", media_type="text/plain")
            except PendingLoanRequestError:
                return Response(content="END You already have a pending loan request.", media_type="text/plain")
            except Exception as e:
                return Response(content=f"END Failed to request loan: {str(e)}", media_type="text/plain")
                
    elif menu_selection == "3":
        # Repay Loan
        if len(inputs) == 1:
            return Response(content="CON Enter amount to repay (GHS):", media_type="text/plain")
        elif len(inputs) == 2:
            amount_raw = inputs[1]
            try:
                amount = float(amount_raw)
            except ValueError:
                return Response(content="END Invalid amount.", media_type="text/plain")
                
            from app.routes.loans import start_farmer_loan_repayment
            from app.schemas.schemas import LoanRepaymentInit
            import uuid
            try:
                await start_farmer_loan_repayment(
                    LoanRepaymentInit(amount=amount),
                    db=db,
                    current_user=None, # System action via USSD
                    x_ussd_msisdn=phoneNumber,
                    x_ussd_membership_id=str(memberships[0].id)
                )
                return Response(content="END Please approve the Moolre payment prompt on your phone to complete your loan repayment.", media_type="text/plain")
            except Exception as e:
                return Response(content=f"END Failed to process repayment: {str(e)}", media_type="text/plain")
                
    elif menu_selection == "4":
        # Check Balance
        active_loans = db.query(Loan).filter(Loan.farmer_id == farmer.id, Loan.status == LoanStatus.disbursed).all()
        total_balance = sum(ln.amount for ln in active_loans)
        return Response(content=f"END Your total active loan balance is GHS {total_balance}.", media_type="text/plain")
        
    return Response(content="END Invalid selection.", media_type="text/plain")
