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

/** Parse CRM integer id or Agro-AI member code (e.g. GH-0042) to a numeric db id. */
export function parseMemberDbId(id) {
  if (id == null || id === '') return null
  if (typeof id === 'number' && Number.isFinite(id)) return id
  const text = String(id).trim()
  if (/^\d+$/.test(text)) return Number(text)
  const match = text.match(/^GH-(\d+)$/i)
  return match ? Number(match[1]) : null
}

function agroAiDbId(farmer) {
  if (!farmer) return null
  return farmer.db_id != null ? farmer.db_id : parseMemberDbId(farmer.farmer_id)
}

export function findAgroAiByDbId(agroAiFarmers, dbId) {
  const target = parseMemberDbId(dbId)
  if (target == null || !agroAiFarmers?.length) return null
  return agroAiFarmers.find((farmer) => agroAiDbId(farmer) === target) || null
}

export function findCrmFarmerByDbId(crmFarmers, dbId) {
  const target = parseMemberDbId(dbId)
  if (target == null || !crmFarmers?.length) return null
  return crmFarmers.find((farmer) => farmer.id === target) || null
}

export function findAgroAiForCrmFarmer(agroAiFarmers, crmFarmer) {
  if (!crmFarmer) return null
  return findAgroAiByDbId(agroAiFarmers, crmFarmer.id)
}

export function findCrmFarmerForAgroAi(crmFarmers, agroAiFarmer) {
  if (!agroAiFarmer) return null
  return findCrmFarmerByDbId(crmFarmers, agroAiDbId(agroAiFarmer))
}

/** @deprecated Prefer findAgroAiForCrmFarmer / findCrmFarmerForAgroAi for cross-source joins. */
export function findFarmerByName(farmers, name) {
  if (!name || !farmers?.length) return null
  const normalized = name.trim().toLowerCase()
  return farmers.find((farmer) => farmer.name.trim().toLowerCase() === normalized) || null
}
