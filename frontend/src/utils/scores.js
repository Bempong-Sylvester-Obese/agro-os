export function scoreTier(score) {
  const value = Number(score)
  if (Number.isNaN(value)) return 'sl'
  if (value >= 82) return 'sh'
  if (value >= 60) return 'sm'
  return 'sl'
}

export function formatTrustScore(score) {
  const value = Number(score)
  if (Number.isNaN(value)) return '—'
  return value.toFixed(1)
}

export function averageTrustScore(farmers) {
  if (!farmers?.length) return '—'
  const total = farmers.reduce((sum, farmer) => sum + Number(farmer.trust_score || 0), 0)
  return (total / farmers.length).toFixed(1)
}

export function findFarmerByName(farmers, name) {
  if (!name || !farmers?.length) return null
  const normalized = name.trim().toLowerCase()
  return farmers.find((farmer) => farmer.name.trim().toLowerCase() === normalized) || null
}
