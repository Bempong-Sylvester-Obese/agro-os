-- Persist expected loan repayment date from dashboard loan requests
ALTER TABLE loans
    ADD COLUMN IF NOT EXISTS expected_repayment_date DATE;
