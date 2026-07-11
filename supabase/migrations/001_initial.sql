-- Initial schema aligned with backend/app/models/models.py (SQLAlchemy create_all mirror).
-- Use for Supabase CLI review; runtime tables are created by the FastAPI app on startup.

CREATE TABLE IF NOT EXISTS cooperatives (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    location VARCHAR,
    currency VARCHAR DEFAULT 'GHS',
    moolre_account_number VARCHAR,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS farmers (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    phone VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE,
    location VARCHAR,
    crop_type VARCHAR,
    acreage DOUBLE PRECISION,
    membership_status VARCHAR DEFAULT 'active',
    cooperative_id INTEGER NOT NULL REFERENCES cooperatives(id),
    trust_score DOUBLE PRECISION DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    farmer_id INTEGER NOT NULL REFERENCES farmers(id),
    transaction_type VARCHAR NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    currency VARCHAR DEFAULT 'GHS',
    status VARCHAR DEFAULT 'pending',
    moolre_reference VARCHAR UNIQUE,
    moolre_transfer_ref VARCHAR UNIQUE,
    payer_phone VARCHAR,
    payee_phone VARCHAR,
    channel VARCHAR,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS loans (
    id SERIAL PRIMARY KEY,
    farmer_id INTEGER NOT NULL REFERENCES farmers(id),
    amount DOUBLE PRECISION NOT NULL,
    currency VARCHAR DEFAULT 'GHS',
    purpose TEXT,
    status VARCHAR DEFAULT 'requested',
    approved_by VARCHAR,
    approved_at TIMESTAMP,
    moolre_transfer_ref VARCHAR,
    disbursed_at TIMESTAMP,
    repaid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS productions (
    id SERIAL PRIMARY KEY,
    farmer_id INTEGER NOT NULL REFERENCES farmers(id),
    crop_type VARCHAR NOT NULL,
    season VARCHAR,
    expected_kg DOUBLE PRECISION,
    planted_date TIMESTAMP,
    harvest_date TIMESTAMP,
    quantity_kg DOUBLE PRECISION,
    quality_grade VARCHAR,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trust_scores (
    id SERIAL PRIMARY KEY,
    farmer_id INTEGER NOT NULL REFERENCES farmers(id),
    score DOUBLE PRECISION NOT NULL,
    payment_compliance DOUBLE PRECISION DEFAULT 0,
    production_history DOUBLE PRECISION DEFAULT 0,
    loan_repayment DOUBLE PRECISION DEFAULT 0,
    attendance DOUBLE PRECISION DEFAULT 0,
    calculated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cooperative_attendances (
    id SERIAL PRIMARY KEY,
    farmer_id INTEGER NOT NULL REFERENCES farmers(id),
    event_name VARCHAR NOT NULL,
    event_date TIMESTAMP NOT NULL,
    attended BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS communication_logs (
    id SERIAL PRIMARY KEY,
    message_type VARCHAR DEFAULT 'sms',
    cooperative_id INTEGER REFERENCES cooperatives(id),
    recipients_count INTEGER DEFAULT 0,
    body TEXT NOT NULL,
    moolre_ref VARCHAR,
    sent_by VARCHAR,
    status VARCHAR DEFAULT 'sent',
    sent_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payment_webhook_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR DEFAULT 'payment',
    moolre_reference VARCHAR,
    transaction_id INTEGER REFERENCES transactions(id),
    signature_valid BOOLEAN DEFAULT TRUE,
    payload TEXT NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    message VARCHAR,
    received_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ussd_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR,
    phone VARCHAR NOT NULL,
    input_path VARCHAR,
    response_text TEXT,
    farmer_id INTEGER REFERENCES farmers(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agro_ai_prediction_logs (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR UNIQUE NOT NULL,
    farmer_id VARCHAR,
    cooperative_id VARCHAR,
    actor_id VARCHAR,
    model_version VARCHAR NOT NULL,
    feature_schema_version VARCHAR NOT NULL,
    requested_credit_amount INTEGER DEFAULT 0,
    features TEXT NOT NULL,
    prediction TEXT NOT NULL,
    context TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    role VARCHAR DEFAULT 'admin',
    cooperative_id INTEGER REFERENCES cooperatives(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
