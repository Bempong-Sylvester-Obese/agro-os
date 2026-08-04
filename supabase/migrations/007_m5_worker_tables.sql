-- M5 Solo Farm / Worker Platform tables
-- Mirrors Alembic migrations 007_organization_type.py and 007_phase1.py

CREATE TABLE IF NOT EXISTS workers (
    id SERIAL PRIMARY KEY,
    cooperative_id INTEGER NOT NULL REFERENCES cooperatives(id),
    name VARCHAR NOT NULL,
    phone VARCHAR NOT NULL,
    wage_rate DOUBLE PRECISION DEFAULT 0.0,
    role VARCHAR DEFAULT 'worker',
    status VARCHAR DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_worker_phone_per_coop UNIQUE (cooperative_id, phone)
);

CREATE TABLE IF NOT EXISTS work_tasks (
    id SERIAL PRIMARY KEY,
    cooperative_id INTEGER NOT NULL REFERENCES cooperatives(id),
    title VARCHAR NOT NULL,
    description TEXT,
    task_type VARCHAR NOT NULL DEFAULT 'general',
    location VARCHAR,
    scheduled_date DATE NOT NULL,
    assigned_by INTEGER REFERENCES users(id),
    status VARCHAR DEFAULT 'open',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS worker_assignments (
    id SERIAL PRIMARY KEY,
    work_task_id INTEGER NOT NULL REFERENCES work_tasks(id) ON DELETE CASCADE,
    worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS worker_attendance (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER NOT NULL REFERENCES workers(id),
    work_task_id INTEGER REFERENCES work_tasks(id),
    cooperative_id INTEGER NOT NULL REFERENCES cooperatives(id),
    date DATE NOT NULL,
    hours_worked DOUBLE PRECISION,
    shift VARCHAR NOT NULL DEFAULT 'full_day',
    logged_by INTEGER REFERENCES users(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS wage_payouts (
    id SERIAL PRIMARY KEY,
    cooperative_id INTEGER NOT NULL REFERENCES cooperatives(id),
    worker_id INTEGER NOT NULL REFERENCES workers(id),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_hours DOUBLE PRECISION DEFAULT 0,
    total_shifts INTEGER DEFAULT 0,
    wage_rate DOUBLE PRECISION DEFAULT 0,
    gross_amount DOUBLE PRECISION DEFAULT 0,
    status VARCHAR DEFAULT 'pending',
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP,
    paid_at TIMESTAMP,
    moolre_reference VARCHAR,
    failure_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS farm_productions (
    id SERIAL PRIMARY KEY,
    cooperative_id INTEGER NOT NULL REFERENCES cooperatives(id),
    crop_type VARCHAR NOT NULL,
    season VARCHAR NOT NULL,
    location VARCHAR,
    planted_date DATE NOT NULL,
    expected_harvest_date DATE,
    actual_harvest_date DATE,
    expected_quantity_kg DOUBLE PRECISION NOT NULL,
    actual_quantity_kg DOUBLE PRECISION,
    quality_grade VARCHAR,
    notes TEXT,
    logged_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);
