export const PRODUCTION_FOCUS_OPTIONS = [
  { value: 'crop', label: 'Crop' },
  { value: 'animal', label: 'Animal' },
  { value: 'mixed', label: 'Mixed' },
]

export const PRODUCTION_KIND_OPTIONS = PRODUCTION_FOCUS_OPTIONS.slice(0, 2)

export const PRODUCTION_ACTIVITIES = {
  crop: ['Harvest', 'Planting', 'Processing', 'Sale'],
  animal: ['Livestock count', 'Milk collection', 'Egg collection', 'Breeding', 'Sale'],
}

export const PRODUCTION_UNITS = [
  { value: 'kg', label: 'kg' },
  { value: 'tonnes', label: 'tonnes' },
  { value: 'litres', label: 'litres' },
  { value: 'bags', label: 'bags' },
  { value: 'crates', label: 'crates' },
  { value: 'dozen', label: 'dozen' },
  { value: 'heads', label: 'heads' },
]

export function productionFocus(member) {
  return member?.production_focus || 'crop'
}

export function productionFocusLabel(value) {
  return PRODUCTION_FOCUS_OPTIONS.find(option => option.value === value)?.label || 'Crop'
}

export function memberProductionDescription(member) {
  const focus = productionFocus(member)
  const crop = member?.crop_type || 'Unspecified crop'
  const animal = member?.animal_type || 'Unspecified animal'

  if (focus === 'animal') {
    return `${animal}${member?.animal_scale ? ` · ${member.animal_scale} animals` : ''}`
  }
  if (focus === 'mixed') return `${crop} + ${animal}`
  return `${crop}${member?.acreage ? ` · ${member.acreage} acres` : ''}`
}

export function productionKind(record) {
  return record?.production_kind || 'crop'
}

export function productionProduct(record) {
  return record?.product_name || record?.crop_type || '—'
}

export function productionActivity(record) {
  return record?.activity || (record?.harvest_date ? 'Harvest' : 'Production')
}

export function productionUnit(record) {
  return record?.unit || 'kg'
}

export function productionExpected(record) {
  const value = record?.expected_quantity ?? record?.expected_kg
  return value == null || Number.isNaN(Number(value)) ? null : Number(value)
}

export function productionQuantity(record) {
  const value = record?.quantity ?? record?.quantity_kg ?? record?.yield_amount
  return value == null || Number.isNaN(Number(value)) ? null : Number(value)
}

export function productionDate(record) {
  return record?.production_date || record?.harvest_date || null
}

export function formatProductionQuantity(value, unit) {
  if (value == null) return '—'
  return `${Number(value).toLocaleString()} ${unit || 'kg'}`
}

export function totalsByUnit(records, valueForRecord) {
  return records.reduce((totals, record) => {
    const value = valueForRecord(record)
    if (value == null) return totals
    const unit = productionUnit(record)
    totals[unit] = (totals[unit] || 0) + value
    return totals
  }, {})
}

export function formatUnitTotals(totals) {
  const entries = Object.entries(totals)
  if (entries.length === 0) return '—'
  return entries
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([unit, value]) => formatProductionQuantity(value, unit))
    .join(' · ')
}
