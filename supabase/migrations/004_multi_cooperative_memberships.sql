-- Split global farmer identity from cooperative-specific membership.
-- This migration deliberately fails on normalized phone collisions so records
-- can be reviewed instead of being merged implicitly.

DO $$
BEGIN
    IF EXISTS (
        SELECT normalized_phone
        FROM (
            SELECT
                CASE
                    WHEN regexp_replace(phone, '\D', '', 'g') ~ '^233[0-9]{9}$'
                        THEN '0' || substring(regexp_replace(phone, '\D', '', 'g') FROM 4 FOR 9)
                    WHEN regexp_replace(phone, '\D', '', 'g') ~ '^0[0-9]{9}$'
                        THEN regexp_replace(phone, '\D', '', 'g')
                    WHEN regexp_replace(phone, '\D', '', 'g') ~ '^[0-9]{9}$'
                        THEN '0' || regexp_replace(phone, '\D', '', 'g')
                    ELSE btrim(phone)
                END AS normalized_phone
            FROM farmers
        ) normalized
        GROUP BY normalized_phone
        HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Normalized farmer phone collision detected; resolve duplicate identities before migration';
    END IF;
END $$;

UPDATE farmers
SET phone = CASE
    WHEN regexp_replace(phone, '\D', '', 'g') ~ '^233[0-9]{9}$'
        THEN '0' || substring(regexp_replace(phone, '\D', '', 'g') FROM 4 FOR 9)
    WHEN regexp_replace(phone, '\D', '', 'g') ~ '^0[0-9]{9}$'
        THEN regexp_replace(phone, '\D', '', 'g')
    WHEN regexp_replace(phone, '\D', '', 'g') ~ '^[0-9]{9}$'
        THEN '0' || regexp_replace(phone, '\D', '', 'g')
    ELSE btrim(phone)
END;

CREATE TABLE cooperative_memberships (
    id SERIAL PRIMARY KEY,
    farmer_id INTEGER NOT NULL REFERENCES farmers(id),
    cooperative_id INTEGER NOT NULL REFERENCES cooperatives(id),
    crop_type VARCHAR,
    acreage DOUBLE PRECISION,
    membership_status VARCHAR DEFAULT 'active' NOT NULL,
    trust_score DOUBLE PRECISION DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_farmer_cooperative UNIQUE (farmer_id, cooperative_id)
);

CREATE INDEX ix_cooperative_memberships_farmer_id
    ON cooperative_memberships(farmer_id);
CREATE INDEX ix_cooperative_memberships_cooperative_id
    ON cooperative_memberships(cooperative_id);

INSERT INTO cooperative_memberships (
    farmer_id,
    cooperative_id,
    crop_type,
    acreage,
    membership_status,
    trust_score,
    created_at,
    updated_at
)
SELECT
    id,
    cooperative_id,
    crop_type,
    acreage,
    membership_status,
    trust_score,
    created_at,
    updated_at
FROM farmers;

ALTER TABLE transactions DROP CONSTRAINT transactions_farmer_id_fkey;
ALTER TABLE transactions RENAME COLUMN farmer_id TO membership_id;
UPDATE transactions child
SET membership_id = membership.id
FROM cooperative_memberships membership
WHERE membership.farmer_id = child.membership_id;
ALTER TABLE transactions
    ADD CONSTRAINT transactions_membership_id_fkey
    FOREIGN KEY (membership_id) REFERENCES cooperative_memberships(id);

ALTER TABLE loans DROP CONSTRAINT loans_farmer_id_fkey;
ALTER TABLE loans RENAME COLUMN farmer_id TO membership_id;
UPDATE loans child
SET membership_id = membership.id
FROM cooperative_memberships membership
WHERE membership.farmer_id = child.membership_id;
ALTER TABLE loans
    ADD CONSTRAINT loans_membership_id_fkey
    FOREIGN KEY (membership_id) REFERENCES cooperative_memberships(id);

ALTER TABLE productions DROP CONSTRAINT productions_farmer_id_fkey;
ALTER TABLE productions RENAME COLUMN farmer_id TO membership_id;
UPDATE productions child
SET membership_id = membership.id
FROM cooperative_memberships membership
WHERE membership.farmer_id = child.membership_id;
ALTER TABLE productions
    ADD CONSTRAINT productions_membership_id_fkey
    FOREIGN KEY (membership_id) REFERENCES cooperative_memberships(id);

ALTER TABLE trust_scores DROP CONSTRAINT trust_scores_farmer_id_fkey;
ALTER TABLE trust_scores RENAME COLUMN farmer_id TO membership_id;
UPDATE trust_scores child
SET membership_id = membership.id
FROM cooperative_memberships membership
WHERE membership.farmer_id = child.membership_id;
ALTER TABLE trust_scores
    ADD CONSTRAINT trust_scores_membership_id_fkey
    FOREIGN KEY (membership_id) REFERENCES cooperative_memberships(id);

ALTER TABLE cooperative_attendances
    DROP CONSTRAINT cooperative_attendances_farmer_id_fkey;
ALTER TABLE cooperative_attendances RENAME COLUMN farmer_id TO membership_id;
UPDATE cooperative_attendances child
SET membership_id = membership.id
FROM cooperative_memberships membership
WHERE membership.farmer_id = child.membership_id;
ALTER TABLE cooperative_attendances
    ADD CONSTRAINT cooperative_attendances_membership_id_fkey
    FOREIGN KEY (membership_id) REFERENCES cooperative_memberships(id);

ALTER TABLE ussd_sessions DROP CONSTRAINT ussd_sessions_farmer_id_fkey;
ALTER TABLE ussd_sessions RENAME COLUMN farmer_id TO membership_id;
UPDATE ussd_sessions child
SET membership_id = membership.id
FROM cooperative_memberships membership
WHERE membership.farmer_id = child.membership_id;
ALTER TABLE ussd_sessions
    ADD CONSTRAINT ussd_sessions_membership_id_fkey
    FOREIGN KEY (membership_id) REFERENCES cooperative_memberships(id);

ALTER TABLE farmers
    DROP COLUMN cooperative_id,
    DROP COLUMN crop_type,
    DROP COLUMN acreage,
    DROP COLUMN membership_status,
    DROP COLUMN trust_score;

ALTER TABLE cooperative_memberships ENABLE ROW LEVEL SECURITY;
CREATE POLICY cooperative_memberships_service_role ON cooperative_memberships
    FOR ALL TO service_role USING (true) WITH CHECK (true);
