import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import History from './History'

vi.mock('../api/client', () => ({
  listContacts: vi.fn().mockResolvedValue([
    {
      id: 'msg1', name: 'Alice Smith', address: '123 Main St, DC',
      email_primary: 'alice@example.com', parse_status: 'parsed',
      received_at: '2026-04-20T10:00:00Z', email_form: null, raw_body: null,
      nearest_charger_id: 1, distance_miles: 2.4, geocache_hit: true, hubspot_status: null,
    },
    {
      id: 'msg2', name: 'Bob Jones', address: '456 Oak Ave, NYC',
      email_primary: 'bob@example.com', parse_status: 'parsed',
      received_at: '2026-04-19T08:00:00Z', email_form: null, raw_body: null,
      nearest_charger_id: 2, distance_miles: 5.1, geocache_hit: true, hubspot_status: null,
    },
  ]),
  previewImport: vi.fn().mockResolvedValue({
    import_id: 'imp-1',
    preview: { new_chargers: 3, new_contacts: 5, new_templates: 1 },
  }),
  confirmImport: vi.fn().mockResolvedValue({ ok: true }),
  deleteContact: vi.fn().mockResolvedValue({ ok: true }),
}))

test('shows all contacts in table after load', async () => {
  render(<History />)
  expect(await screen.findByText('Alice Smith')).toBeInTheDocument()
  expect(screen.getByText('Bob Jones')).toBeInTheDocument()
})

test('search by name filters out non-matching contacts', async () => {
  render(<History />)
  await screen.findByText('Alice Smith')
  await userEvent.type(screen.getByPlaceholderText(/search/i), 'Alice')
  expect(screen.getByText('Alice Smith')).toBeInTheDocument()
  expect(screen.queryByText('Bob Jones')).not.toBeInTheDocument()
})

test('search by email filters contacts', async () => {
  render(<History />)
  await screen.findByText('Alice Smith')
  await userEvent.type(screen.getByPlaceholderText(/search/i), 'alice@example')
  expect(screen.getByText('alice@example.com')).toBeInTheDocument()
  expect(screen.queryByText('bob@example.com')).not.toBeInTheDocument()
})

test('export links point to API endpoints', async () => {
  render(<History />)
  await screen.findByText('Alice Smith')
  expect(screen.getByRole('link', { name: /download json/i }))
    .toHaveAttribute('href', '/api/export/snapshot')
  expect(screen.getByRole('link', { name: /download csv/i }))
    .toHaveAttribute('href', '/api/export/csv')
})

test('file upload triggers preview and shows Confirm button', async () => {
  render(<History />)
  await screen.findByText('Alice Smith')

  const snapshot = JSON.stringify({
    contacts: [], outbound_emails: [], chargers: [], templates: [], geocache: [],
  })
  const file = new File([snapshot], 'snapshot.json', { type: 'application/json' })
  const input = screen.getByLabelText(/upload snapshot/i)
  await userEvent.upload(input, file)

  expect(await screen.findByRole('button', { name: /confirm import/i })).toBeInTheDocument()
})

test('clicking Confirm Import calls confirmImport and shows success', async () => {
  render(<History />)
  await screen.findByText('Alice Smith')

  const snapshot = JSON.stringify({
    contacts: [], outbound_emails: [], chargers: [], templates: [], geocache: [],
  })
  const file = new File([snapshot], 'snapshot.json', { type: 'application/json' })
  await userEvent.upload(screen.getByLabelText(/upload snapshot/i), file)
  await userEvent.click(await screen.findByRole('button', { name: /confirm import/i }))

  expect(await screen.findByText(/import complete/i)).toBeInTheDocument()
})
