-- ⚠️ REFERENCE ONLY — actual schema is managed by Alembic (backend/alembic/versions/).
-- Do NOT apply this SQL directly. Use `alembic upgrade head` instead.
--
-- RLS policies for M5 Solo Farm / Worker Platform tables
-- Mirrors the pattern in 002_rls_policies.sql

ALTER TABLE workers ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE worker_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE worker_attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE wage_payouts ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_productions ENABLE ROW LEVEL SECURITY;

CREATE POLICY workers_service_role ON workers
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY work_tasks_service_role ON work_tasks
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY worker_assignments_service_role ON worker_assignments
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY worker_attendance_service_role ON worker_attendance
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY wage_payouts_service_role ON wage_payouts
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY farm_productions_service_role ON farm_productions
    FOR ALL TO service_role USING (true) WITH CHECK (true);
