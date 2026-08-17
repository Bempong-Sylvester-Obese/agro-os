-- M4 cooperative completeness: auth lifecycle, SMS consent, announcements.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS reset_token VARCHAR,
    ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS invite_token VARCHAR,
    ADD COLUMN IF NOT EXISTS invite_token_expires_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE NOT NULL;

ALTER TABLE cooperative_memberships
    ADD COLUMN IF NOT EXISTS sms_consent BOOLEAN DEFAULT TRUE NOT NULL;

CREATE TABLE IF NOT EXISTS announcements (
    id SERIAL PRIMARY KEY,
    cooperative_id INTEGER NOT NULL REFERENCES cooperatives(id),
    title VARCHAR NOT NULL,
    body TEXT NOT NULL,
    send_sms BOOLEAN DEFAULT FALSE NOT NULL,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    deleted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_announcements_cooperative_id
    ON announcements(cooperative_id);

ALTER TABLE announcements ENABLE ROW LEVEL SECURITY;

CREATE POLICY announcements_service_role ON announcements
    FOR ALL TO service_role USING (true) WITH CHECK (true);
