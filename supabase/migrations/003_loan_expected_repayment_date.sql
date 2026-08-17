-- ⚠️ REFERENCE ONLY — actual schema is managed by Alembic (backend/alembic/versions/).
-- Do NOT apply this SQL directly. Use `alembic upgrade head` instead.
--
-- Persist expected loan repayment date from dashboard loan requests
ALTER TABLE loans
    ADD COLUMN IF NOT EXISTS expected_repayment_date DATE;
