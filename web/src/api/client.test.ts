import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  getPipelineStatus,
  runPipeline,
  listContacts,
  getContact,
  sendContact,
  skipContact,
  previewImport,
  confirmImport,
  listTemplates,
  updateTemplate,
  getDecisionTree,
  updateDecisionTree,
  testDecisionTree,
} from './client'

function mockFetch(data: unknown, status = 200) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  } as Response))
}

beforeEach(() => vi.restoreAllMocks())

describe('getPipelineStatus', () => {
  it('returns status object', async () => {
    mockFetch({ status: 'idle', last_run_at: null, run_id: null })
    const result = await getPipelineStatus()
    expect(result.status).toBe('idle')
    expect(fetch).toHaveBeenCalledWith('/api/pipeline/status')
  })
})

describe('runPipeline', () => {
  it('POSTs to /api/pipeline/run and returns run_id', async () => {
    mockFetch({ run_id: 'abc123' })
    const result = await runPipeline()
    expect(result.run_id).toBe('abc123')
    expect(fetch).toHaveBeenCalledWith(
      '/api/pipeline/run',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('passes fixture=true when requested', async () => {
    mockFetch({ run_id: 'xyz' })
    await runPipeline({ fixture: true })
    expect(fetch).toHaveBeenCalledWith(
      '/api/pipeline/run?fixture=true',
      expect.any(Object)
    )
  })
})

describe('listContacts', () => {
  it('fetches /api/contacts and returns array', async () => {
    mockFetch([{ id: '1', name: 'Alice', parse_status: 'parsed' }])
    const result = await listContacts()
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('Alice')
  })

  it('passes status filter as query param', async () => {
    mockFetch([])
    await listContacts({ status: 'pending' })
    expect(fetch).toHaveBeenCalledWith('/api/contacts?status=pending')
  })
})

describe('getContact', () => {
  it('fetches contact detail by id', async () => {
    mockFetch({ contact: { id: 'msg1' }, outbound_emails: [] })
    const result = await getContact('msg1')
    expect(result.contact.id).toBe('msg1')
  })
})

describe('sendContact', () => {
  it('POSTs to send endpoint', async () => {
    mockFetch({ ok: true, status: 'sent' })
    const result = await sendContact('msg1')
    expect(result.ok).toBe(true)
    expect(fetch).toHaveBeenCalledWith(
      '/api/contacts/msg1/send',
      expect.objectContaining({ method: 'POST' })
    )
  })
})

describe('skipContact', () => {
  it('POSTs to skip endpoint', async () => {
    mockFetch({ ok: true })
    await skipContact('msg1')
    expect(fetch).toHaveBeenCalledWith(
      '/api/contacts/msg1/skip',
      expect.objectContaining({ method: 'POST' })
    )
  })
})

describe('previewImport', () => {
  it('POSTs snapshot JSON and returns import_id + preview counts', async () => {
    mockFetch({
      import_id: 'abc',
      preview: { new_chargers: 2, new_contacts: 0, new_templates: 1 },
    })
    const snapshot = { contacts: [], outbound_emails: [], chargers: [], templates: [], geocache: [] }
    const result = await previewImport(snapshot)
    expect(result.import_id).toBe('abc')
    expect(result.preview.new_chargers).toBe(2)
    expect(fetch).toHaveBeenCalledWith(
      '/api/import/snapshot',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      })
    )
  })
})

describe('confirmImport', () => {
  it('POSTs to confirm endpoint and returns ok', async () => {
    mockFetch({ ok: true })
    const result = await confirmImport('abc')
    expect(result.ok).toBe(true)
    expect(fetch).toHaveBeenCalledWith(
      '/api/import/snapshot/confirm/abc',
      expect.objectContaining({ method: 'POST' })
    )
  })
})

describe('listTemplates', () => {
  it('GETs /api/templates and returns array', async () => {
    mockFetch([{ name: 'general_car_info', subject: 'Hi', body_md: '<p>Hi</p>', updated_at: null }])
    const result = await listTemplates()
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('general_car_info')
    expect(fetch).toHaveBeenCalledWith('/api/templates')
  })
})

describe('updateTemplate', () => {
  it('PUTs to /api/templates/{name} with subject and body_md', async () => {
    mockFetch({ name: 'general_car_info', subject: 'Updated', body_md: '<p>New</p>', updated_at: null })
    const result = await updateTemplate('general_car_info', { subject: 'Updated', body_md: '<p>New</p>' })
    expect(result.name).toBe('general_car_info')
    expect(result.subject).toBe('Updated')
    expect(fetch).toHaveBeenCalledWith(
      '/api/templates/general_car_info',
      expect.objectContaining({
        method: 'PUT',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      })
    )
  })
})

describe('getDecisionTree', () => {
  it('GETs /api/decision-tree', async () => {
    mockFetch({ condition: { field: 'distance_miles', op: 'lte', value: 5 }, then: { template: 'close' }, else: { template: 'far' } })
    const result = await getDecisionTree()
    expect(result).not.toBeNull()
    expect(fetch).toHaveBeenCalledWith('/api/decision-tree')
  })

  it('returns null when tree not set', async () => {
    mockFetch(null)
    const result = await getDecisionTree()
    expect(result).toBeNull()
  })
})

describe('updateDecisionTree', () => {
  it('PUTs to /api/decision-tree with JSON body', async () => {
    const tree = { condition: { field: 'distance_miles', op: 'lte', value: 5 }, then: { template: 'close' }, else: { template: 'far' } }
    mockFetch(tree)
    await updateDecisionTree(tree)
    expect(fetch).toHaveBeenCalledWith(
      '/api/decision-tree',
      expect.objectContaining({
        method: 'PUT',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      })
    )
  })
})

describe('testDecisionTree', () => {
  it('POSTs to /api/decision-tree/test and returns results', async () => {
    mockFetch({ results: [{ id: 'msg1', name: 'Alice', address: '123 Main', parsed: true, template: 'general_car_info' }] })
    const result = await testDecisionTree()
    expect(result.results).toHaveLength(1)
    expect(result.results[0].template).toBe('general_car_info')
    expect(fetch).toHaveBeenCalledWith(
      '/api/decision-tree/test',
      expect.objectContaining({ method: 'POST' })
    )
  })
})
