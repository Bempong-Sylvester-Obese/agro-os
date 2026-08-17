-- ⚠️ REFERENCE ONLY — actual schema is managed by Alembic (backend/alembic/versions/).
-- Do NOT apply this SQL directly. Use `alembic upgrade head` instead.
--
-- Tenant-scoped RLS policies for core cooperative tables
-- Primary isolation is API-layer (enforce_cooperative_scope); RLS is defense-in-depth.

ALTER TABLE farmers ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE loans ENABLE ROW LEVEL SECURITY;
ALTER TABLE productions ENABLE ROW LEVEL SECURITY;
ALTER TABLE trust_scores ENABLE ROW LEVEL SECURITY;

-- Farmers: a global farmer is visible through a membership in the current cooperative.
CREATE POLICY farmers_cooperative_scope ON farmers
    FOR SELECT USING (
        EXISTS (
            SELECT 1
            FROM cooperative_memberships
            WHERE cooperative_memberships.farmer_id = farmers.id
              AND cooperative_memberships.cooperative_id =
                  NULLIF(current_setting('app.current_cooperative_id', true), '')::int
        )
    );

-- Finance tables store cooperative membership IDs in membership_id.
CREATE POLICY transactions_cooperative_scope ON transactions
    FOR SELECT USING (
        membership_id IN (
            SELECT id
            FROM cooperative_memberships
            WHERE cooperative_id =
                NULLIF(current_setting('app.current_cooperative_id', true), '')::int
        )
    );

CREATE POLICY loans_cooperative_scope ON loans
    FOR SELECT USING (
        membership_id IN (
            SELECT id
            FROM cooperative_memberships
            WHERE cooperative_id =
                NULLIF(current_setting('app.current_cooperative_id', true), '')::int
        )
    );

-- Productions: scope by farmer's cooperative
CREATE POLICY productions_cooperative_scope ON productions
    FOR SELECT USING (
        membership_id IN (
            SELECT id
            FROM cooperative_memberships
            WHERE cooperative_id =
                NULLIF(current_setting('app.current_cooperative_id', true), '')::int
        )
    );

-- Trust scores: scope by farmer's cooperative
CREATE POLICY trust_scores_cooperative_scope ON trust_scores
    FOR SELECT USING (
        membership_id IN (
            SELECT id
            FROM cooperative_memberships
            WHERE cooperative_id =
                NULLIF(current_setting('app.current_cooperative_id', true), '')::int
        )
    );
