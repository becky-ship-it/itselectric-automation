import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  getPipelineStatus,
  runPipeline,
  listContacts,
  getContact,
  sendContact,
  skipContact,
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
