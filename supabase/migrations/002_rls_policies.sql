-- Row-level security policies (service role bypasses RLS; anon/authenticated scoped)

ALTER TABLE cooperatives ENABLE ROW LEVEL SECURITY;
ALTER TABLE farmers ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY cooperatives_service_role ON cooperatives
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY farmers_service_role ON farmers
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY transactions_service_role ON transactions
    FOR ALL TO service_role USING (true) WITH CHECK (true);
