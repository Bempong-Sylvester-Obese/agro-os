-- Add a unified, unit-aware production model while retaining crop contracts.

ALTER TABLE cooperative_memberships
    ADD COLUMN IF NOT EXISTS production_focus VARCHAR DEFAULT 'crop',
    ADD COLUMN IF NOT EXISTS animal_type VARCHAR,
    ADD COLUMN IF NOT EXISTS animal_scale DOUBLE PRECISION;

UPDATE cooperative_memberships
SET production_focus = 'crop'
WHERE production_focus IS NULL;

ALTER TABLE cooperative_memberships
    ALTER COLUMN production_focus SET DEFAULT 'crop',
    ALTER COLUMN production_focus SET NOT NULL,
    ADD CONSTRAINT ck_membership_production_focus
        CHECK (production_focus IN ('crop', 'animal', 'mixed'));

CREATE INDEX IF NOT EXISTS ix_cooperative_memberships_production_focus
    ON cooperative_memberships(production_focus);

ALTER TABLE productions
    ADD COLUMN IF NOT EXISTS production_kind VARCHAR DEFAULT 'crop',
    ADD COLUMN IF NOT EXISTS product_name VARCHAR,
    ADD COLUMN IF NOT EXISTS activity VARCHAR,
    ADD COLUMN IF NOT EXISTS unit VARCHAR DEFAULT 'kg',
    ADD COLUMN IF NOT EXISTS expected_quantity DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS quantity DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS production_date TIMESTAMP;

UPDATE productions
SET production_kind = COALESCE(production_kind, 'crop'),
    product_name = COALESCE(product_name, crop_type),
    activity = COALESCE(
        activity,
        CASE
            WHEN harvest_date IS NOT NULL OR quantity_kg IS NOT NULL THEN 'harvest'
            WHEN planted_date IS NOT NULL THEN 'planting'
            ELSE NULL
        END
    ),
    unit = COALESCE(unit, 'kg'),
    expected_quantity = COALESCE(expected_quantity, expected_kg),
    quantity = COALESCE(quantity, quantity_kg),
    production_date = COALESCE(production_date, harvest_date, planted_date);

ALTER TABLE productions
    ALTER COLUMN production_kind SET DEFAULT 'crop',
    ALTER COLUMN production_kind SET NOT NULL,
    ALTER COLUMN unit SET DEFAULT 'kg',
    ALTER COLUMN unit SET NOT NULL,
    ALTER COLUMN crop_type DROP NOT NULL,
    ADD CONSTRAINT ck_production_kind
        CHECK (production_kind IN ('crop', 'animal'));

CREATE INDEX IF NOT EXISTS ix_productions_production_kind
    ON productions(production_kind);
