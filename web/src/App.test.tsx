import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import App from './App'

// Must be at module scope — Vitest hoists vi.mock calls
vi.mock('./api/client', () => ({
  getPipelineStatus: vi.fn().mockResolvedValue({ status: 'idle', last_run_at: null, run_id: null }),
  runPipeline: vi.fn().mockResolvedValue({ run_id: 'test-run' }),
  listContacts: vi.fn().mockResolvedValue([
    {
      id: 'msg1', name: 'Alice', address: '1 Main St',
      parse_status: 'parsed', received_at: null,
      email_primary: null, email_form: null, raw_body: null,
      nearest_charger_id: null, distance_miles: null,
      geocache_hit: false, hubspot_status: null,
    },
  ]),
  getContact: vi.fn().mockResolvedValue({ contact: {}, outbound_emails: [] }),
  sendContact: vi.fn().mockResolvedValue({ ok: true, status: 'sent' }),
  skipContact: vi.fn().mockResolvedValue({ ok: true }),
}))

test('inbox route shows contact name', async () => {
  render(
    <MemoryRouter initialEntries={['/inbox']}>
      <App />
    </MemoryRouter>
  )
  expect(await screen.findByText('Alice')).toBeInTheDocument()
})

test('renders sidebar nav links', () => {
  render(
    <MemoryRouter initialEntries={['/']}>
      <App />
    </MemoryRouter>
  )
  expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0)
  expect(screen.getByText('Inbox')).toBeInTheDocument()
})
