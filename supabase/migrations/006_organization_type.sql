-- ⚠️ REFERENCE ONLY — actual schema is managed by Alembic (backend/alembic/versions/).
-- Do NOT apply this SQL directly. Use `alembic upgrade head` instead.
--
-- Add organization type, subscription, and role columns to cooperatives and users
-- to match backend/app/models/models.py (Cooperative and User SQLAlchemy models)

ALTER TABLE cooperatives
    ADD COLUMN IF NOT EXISTS organization_type VARCHAR NOT NULL DEFAULT 'cooperative',
    ADD COLUMN IF NOT EXISTS subscription_plan VARCHAR DEFAULT 'starter',
    ADD COLUMN IF NOT EXISTS subscription_status VARCHAR DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS ussd_code VARCHAR(4);

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS onboarding_role VARCHAR,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
