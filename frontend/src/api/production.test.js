import { afterEach, describe, expect, it, vi } from 'vitest'
import { buildProductionPayload, logProduction } from './production'

describe('production API', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('builds a generic, typed production payload', () => {
    expect(buildProductionPayload({
      farmerId: '12',
      productionKind: 'animal',
      productName: '  Milk ',
      activity: 'Milk collection',
      unit: 'litres',
      expectedQuantity: '80.5',
      quantity: '72',
      productionDate: '2026-07-17',
    })).toEqual({
      farmer_id: 12,
      production_kind: 'animal',
      product_name: 'Milk',
      activity: 'Milk collection',
      unit: 'litres',
      expected_quantity: 80.5,
      quantity: 72,
      production_date: '2026-07-17',
    })
  })

  it('posts the production date in one adaptive request', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: vi.fn().mockResolvedValue({ id: 9 }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const values = {
      farmerId: '3',
      productionKind: 'crop',
      productName: 'Rice',
      activity: 'Harvest',
      unit: 'kg',
      expectedQuantity: '500',
      quantity: '450',
      productionDate: '2026-07-10',
    }

    await logProduction(values)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(buildProductionPayload(values))
  })
})
