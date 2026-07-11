-- Golden Path demo seed for `supabase db reset` (see backend/app/database/seed.py)

INSERT INTO cooperatives (name, description, location, currency, moolre_account_number)
VALUES (
    'Kuapa Kokoo Demo Cooperative',
    'Hackathon demo cooperative for the Golden Path pitch',
    'Kumasi, Ashanti Region',
    'GHS',
    'DEMO-WALLET-001'
)
ON CONFLICT DO NOTHING;

INSERT INTO farmers (name, phone, location, crop_type, acreage, cooperative_id, trust_score)
SELECT 'Abena Mensah', '+233552341234', 'Ashanti', 'Maize', 4.1, c.id, 58.0
FROM cooperatives c
WHERE c.name = 'Kuapa Kokoo Demo Cooperative'
ON CONFLICT DO NOTHING;
