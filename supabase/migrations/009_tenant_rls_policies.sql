-- ⚠️ REFERENCE ONLY — actual schema is managed by Alembic (backend/alembic/versions/).
-- Do NOT apply this SQL directly. Use `alembic upgrade head` instead.
--
-- Tenant-scoped RLS policies for core cooperative tables
-- Primary isolation is API-layer (enforce_cooperative_scope); RLS is defense-in-depth.

-- Farmers: scope by cooperative_id
CREATE POLICY farmers_cooperative_scope ON farmers
    FOR SELECT USING (cooperative_id = current_setting('app.current_cooperative_id')::int);

-- Transactions: scope by farmer's cooperative
CREATE POLICY transactions_cooperative_scope ON transactions
    FOR SELECT USING (
        farmer_id IN (SELECT id FROM farmers WHERE cooperative_id = current_setting('app.current_cooperative_id')::int)
    );

-- Loans: scope by farmer's cooperative  
CREATE POLICY loans_cooperative_scope ON loans
    FOR SELECT USING (
        farmer_id IN (SELECT id FROM farmers WHERE cooperative_id = current_setting('app.current_cooperative_id')::int)
    );

-- Productions: scope by farmer's cooperative
CREATE POLICY productions_cooperative_scope ON productions
    FOR SELECT USING (
        farmer_id IN (SELECT id FROM cooperative_memberships WHERE cooperative_id = current_setting('app.current_cooperative_id')::int)
    );

-- Trust scores: scope by farmer's cooperative
CREATE POLICY trust_scores_cooperative_scope ON trust_scores
    FOR SELECT USING (
        farmer_id IN (SELECT id FROM cooperative_memberships WHERE cooperative_id = current_setting('app.current_cooperative_id')::int)
    );
