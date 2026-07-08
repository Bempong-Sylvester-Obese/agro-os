import { PAYMENTS } from '../data/payments'
import { authHeaders } from './auth'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const FETCH_TIMEOUT_MS = 10000

export function formatFarmerId(farmerId) {
  return `GH-${String(farmerId).padStart(4, '0')}`
}

export function channelToMethod(channel) {
  if (!channel) return '—'
  const code = String(channel)
  if (code === '13') return 'MoMo'
  if (code === '6' || code === '7') return 'USSD'
  return 'Mobile'
}

export function statusToDisplay(status) {
  switch (status) {
    case 'completed':
      return { label: 'Paid', cls: 'bdg-green' }
    case 'pending':
      return { label: 'Pending', cls: 'bdg-amber' }
    case 'failed':
      return { label: 'Failed', cls: 'bdg-red' }
    default:
      return { label: status || 'Unknown', cls: 'bdg-amber' }
  }
}

export function formatAmount(amount, currency = 'GHS') {
  const value = Number(amount)
  if (Number.isNaN(value)) return `${currency} —`
  return `${currency} ${value.toLocaleString('en-GH', { maximumFractionDigits: 2 })}`
}

export function formatTransactionDate(isoDate) {
  if (!isoDate) return '—'
  const date = new Date(isoDate)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
}

export function buildFarmerLookup(farmers = []) {
  return farmers.reduce((lookup, farmer) => {
    lookup[farmer.id] = farmer
    return lookup
  }, {})
}

export function mapTransactionToRow(tx, farmerLookup = {}) {
  const farmer = farmerLookup[tx.farmer_id]
  const { label, cls } = statusToDisplay(tx.status)

  return {
    key: String(tx.id),
    name: farmer?.name || `Member ${formatFarmerId(tx.farmer_id)}`,
    memberId: formatFarmerId(tx.farmer_id),
    amount: formatAmount(tx.amount, tx.currency),
    method: channelToMethod(tx.channel),
    date: formatTransactionDate(tx.created_at),
    status: label,
    statusClass: cls,
    rawAmount: Number(tx.amount) || 0,
    rawStatus: tx.status,
    rawChannel: tx.channel,
  }
}

export function mapTransactionsToRows(transactions = [], farmers = []) {
  const farmerLookup = buildFarmerLookup(farmers)
  return transactions.map((tx) => mapTransactionToRow(tx, farmerLookup))
}

export function computePaymentStats(rows = []) {
  const completed = rows.filter((row) => row.rawStatus === 'completed')
  const totalCollected = completed.reduce((sum, row) => sum + row.rawAmount, 0)
  const momoTotal = completed
    .filter((row) => row.rawChannel === '13')
    .reduce((sum, row) => sum + row.rawAmount, 0)
  const ussdTotal = completed
    .filter((row) => row.rawChannel === '6' || row.rawChannel === '7')
    .reduce((sum, row) => sum + row.rawAmount, 0)

  const monthLabel = new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
  const momoPct = totalCollected > 0 ? Math.round((momoTotal / totalCollected) * 100) : 0
  const ussdPct = totalCollected > 0 ? Math.round((ussdTotal / totalCollected) * 100) : 0

  return [
    ['Total collected', formatAmount(totalCollected), monthLabel],
    ['Via MoMo', formatAmount(momoTotal), totalCollected > 0 ? `${momoPct}% of total` : 'No completed payments'],
    ['Via USSD', formatAmount(ussdTotal), totalCollected > 0 ? `${ussdPct}% of total` : 'No completed payments'],
  ]
}

function demoFallback() {
  const rows = PAYMENTS.map(([name, id, amt, method, date, status, cls], index) => ({
    key: `demo-${index}`,
    name,
    memberId: id,
    amount: amt,
    method,
    date,
    status,
    statusClass: cls,
    rawAmount: parseFloat(String(amt).replace(/[^\d.]/g, '')) || 0,
    rawStatus: status === 'Paid' ? 'completed' : status === 'Failed' ? 'failed' : 'pending',
    rawChannel: method === 'MoMo' ? '13' : method === 'USSD' ? '6' : null,
  }))

  return {
    transactions: [],
    farmers: [],
    walletBalance: null,
    rows,
    stats: [
      ['Total collected', 'GHS 29,760', 'June 2026'],
      ['Via MoMo', 'GHS 18,240', '61% of total'],
      ['Via USSD', 'GHS 7,800', '26% of total'],
    ],
    source: 'demo',
  }
}

export async function collectDues({ farmer_id, amount, channel = '13', description = 'Cooperative dues payment' }) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}/transactions/dues/collect`, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
      },
      body: JSON.stringify({ farmer_id, amount, channel, description }),
    })

    if (!response.ok) {
      const detail = await response.text()
      throw new Error(detail || 'Could not initiate dues collection')
    }

    return response.json()
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function fetchPaymentsDashboard() {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)
  const fetchOptions = { signal: controller.signal }

  try {
    const [transactionsResponse, farmersResponse] = await Promise.all([
      fetch(`${API_URL}/transactions/`, fetchOptions),
      fetch(`${API_URL}/farmers/`, fetchOptions),
    ])

    if (!transactionsResponse.ok) {
      throw new Error('transactions API unavailable')
    }

    const transactions = await transactionsResponse.json()
    const farmers = farmersResponse.ok ? await farmersResponse.json() : []

    let walletBalance = null
    try {
      const walletResponse = await fetch(`${API_URL}/transactions/moolre/wallet-balance`, fetchOptions)
      if (walletResponse.ok) {
        walletBalance = await walletResponse.json()
      }
    } catch {
      // Wallet balance is optional for the dashboard.
    }

    const rows = mapTransactionsToRows(transactions, farmers)

    return {
      transactions,
      farmers,
      walletBalance,
      rows,
      stats: computePaymentStats(rows),
      source: 'api',
    }
  } catch {
    return demoFallback()
  } finally {
    clearTimeout(timeoutId)
  }
}
