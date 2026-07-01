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
