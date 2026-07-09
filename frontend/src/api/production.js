import { API_URL, apiResult, fetchJson, withDemoFallback } from './config'

const DEMO_PRODUCTION = [
  {
    id: 1,
    farmer_id: 1,
    farmer_name: 'Abena Mensah',
    crop_type: 'Maize',
    season: '2026A',
    expected_kg: 1800,
    quantity_kg: 920,
    quality_grade: 'B',
  },
  {
    id: 2,
    farmer_id: 2,
    farmer_name: 'Kofi Darko',
    crop_type: 'Cocoa',
    season: '2026A',
    expected_kg: 2400,
    quantity_kg: 2100,
    quality_grade: 'A',
  },
]

function enrichRecords(records, farmers) {
  const lookup = farmers.reduce((acc, farmer) => {
    acc[farmer.id] = farmer.name
    return acc
  }, {})

  return records.map((record) => ({
    ...record,
    farmer_name: lookup[record.farmer_id] || `Member GH-${String(record.farmer_id).padStart(4, '0')}`,
  }))
}

function demoProductionDashboard() {
  return apiResult('demo', {
    records: DEMO_PRODUCTION,
    stats: [
      ['Active crop cycles', String(DEMO_PRODUCTION.length), 'Demo data'],
      ['Expected yield', '4,200 kg', 'Current season'],
      ['Actual harvest', '3,020 kg', '72% of expected'],
    ],
  })
}

export function fetchProductionDashboard() {
  return withDemoFallback(
    async () => {
      const [records, farmers] = await Promise.all([
        fetchJson(`${API_URL}/production/`),
        fetchJson(`${API_URL}/farmers/`),
      ])

      const enriched = enrichRecords(records, farmers)
      const totalExpected = enriched.reduce((sum, row) => sum + (Number(row.expected_kg) || 0), 0)
      const totalActual = enriched.reduce((sum, row) => sum + (Number(row.quantity_kg) || 0), 0)
      const yieldPct = totalExpected > 0 ? Math.round((totalActual / totalExpected) * 100) : 0

      return apiResult('api', {
        records: enriched,
        stats: [
          ['Active crop cycles', String(enriched.length), 'All farmers'],
          ['Expected yield', `${totalExpected.toLocaleString()} kg`, 'Current season'],
          ['Actual harvest', `${totalActual.toLocaleString()} kg`, `${yieldPct}% of expected`],
        ],
      })
    },
    () => demoProductionDashboard(),
  )
}
