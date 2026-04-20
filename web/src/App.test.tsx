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
  getContact: vi.fn().mockResolvedValue({
    contact: {
      id: 'msg1', name: 'Bob', address: '123 Main St',
      email_primary: 'bob@example.com', parse_status: 'parsed',
      received_at: null, email_form: null, raw_body: null,
      nearest_charger_id: null, distance_miles: null,
      geocache_hit: false, hubspot_status: null,
    },
    outbound_emails: [{
      id: 'out1', contact_id: 'msg1', template_name: 'tell_me_more_dc',
      routed_template: 'tell_me_more_dc', subject: 'Hi Bob',
      body_html: '<p>Hello</p>', sent_at: null, status: 'pending',
      sent_by: 'auto', error_message: null,
    }],
  }),
  sendContact: vi.fn().mockResolvedValue({ ok: true, status: 'sent' }),
  skipContact: vi.fn().mockResolvedValue({ ok: true }),
  previewImport: vi.fn().mockResolvedValue({
    import_id: 'imp-1',
    preview: { new_chargers: 1, new_contacts: 2, new_templates: 0 },
  }),
  confirmImport: vi.fn().mockResolvedValue({ ok: true }),
}))

test('InboxDetail shows Send button for pending contact', async () => {
  const { InboxDetail } = await import('./pages/InboxDetail')
  render(<InboxDetail id="msg1" onAction={() => {}} />)
  expect(await screen.findByText('Send')).toBeInTheDocument()
})

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
  expect(screen.getByText('History')).toBeInTheDocument()
})
