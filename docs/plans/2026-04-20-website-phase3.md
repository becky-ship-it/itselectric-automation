# Website Phase 3 — History, Export & Import Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a History page with a searchable contact log, one-click JSON/CSV export download links, and a JSON snapshot import flow (file → preview diff → confirm).

**Architecture:** Pure frontend addition — the backend APIs already exist in `server/routers/export.py`. The History page lives at `/history`, fetches all contacts via the existing `GET /api/contacts` endpoint, filters client-side by search query, provides `<a href>` download links for JSON and CSV, and implements a three-step import flow: file picker → `POST /api/import/snapshot` (returns preview) → `POST /api/import/snapshot/confirm/{import_id}` (applies changes). No backend changes needed.

**Tech Stack:** React 19, TypeScript 5 (`verbatimModuleSyntax` + `erasableSyntaxOnly` enforced), Tailwind CSS v4, Vitest 4 + jsdom + @testing-library/react + @testing-library/user-event. All work is in `web/`.

**Key TypeScript rules (enforced by tsconfig):**
- Type-only imports MUST use `import type { Foo }` — never `import { Foo }` for types
- No parameter properties in class constructors (`constructor(public x: string)` is banned)
- `vi.mock(...)` calls MUST be at module scope, not inside test bodies — Vitest hoists them

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `web/src/components/Sidebar.tsx` | Modify | Add "History" nav link |
| `web/src/App.tsx` | Modify | Add `/history` route |
| `web/src/App.test.tsx` | Modify | Add History nav smoke test; extend mock with new client fns |
| `web/src/api/client.ts` | Modify | Add `ImportPreview` interface, `previewImport`, `confirmImport` |
| `web/src/api/client.test.ts` | Modify | Tests for two new client functions |
| `web/src/pages/History.tsx` | Create | Full History page: contact table, search, export links, import flow |
| `web/src/pages/History.test.tsx` | Create | Unit tests for History page |

---

## Chunk 1: Route wiring and API client

### Task 1.1: History route and nav link

**Files:**
- Modify: `web/src/components/Sidebar.tsx`
- Modify: `web/src/App.tsx`
- Create: `web/src/pages/History.tsx` (placeholder)
- Modify: `web/src/App.test.tsx`

- [ ] **Step 1: Update `web/src/App.test.tsx` — extend mock and add nav test**

The existing `vi.mock('./api/client', ...)` at module scope needs two new mock entries (`previewImport`, `confirmImport`). Add a "History" nav test. Replace the entire file with:

```tsx
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
```

- [ ] **Step 2: Run tests — confirm FAIL**

```bash
cd web && npm test
```

Expected: FAIL — "History" not found in sidebar (we haven't added it yet).

- [ ] **Step 3: Create placeholder `web/src/pages/History.tsx`**

```tsx
export default function History() {
  return <h1 className="text-2xl font-semibold text-gray-900">History</h1>
}
```

- [ ] **Step 4: Add History link to `web/src/components/Sidebar.tsx`**

Replace the `links` array (the rest of the file stays unchanged):

```tsx
const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/inbox', label: 'Inbox' },
  { to: '/history', label: 'History' },
]
```

- [ ] **Step 5: Add `/history` route to `web/src/App.tsx`**

```tsx
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Inbox from './pages/Inbox'
import History from './pages/History'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout pipelineStatus="idle" lastRunAt={null} />}>
        <Route index element={<Dashboard />} />
        <Route path="inbox" element={<Inbox />} />
        <Route path="history" element={<History />} />
      </Route>
    </Routes>
  )
}
```

- [ ] **Step 6: Run tests — confirm PASS**

```bash
cd web && npm test
```

Expected:
```
Test Files: 3 passed (3)
Tests:      17 passed (17)
```

- [ ] **Step 7: Commit**

```bash
git add web/src/components/Sidebar.tsx web/src/App.tsx web/src/pages/History.tsx web/src/App.test.tsx
git commit -m "feat(web): add History route and sidebar nav link"
```

---

### Task 1.2: Import API client functions

**Files:**
- Modify: `web/src/api/client.ts`
- Modify: `web/src/api/client.test.ts`

The existing `request<T>` helper and `vi.stubGlobal('fetch', ...)` pattern in the test file handle all the boilerplate.

- [ ] **Step 1: Write failing tests**

Add to the end of `web/src/api/client.test.ts` (after the `skipContact` describe block):

```ts
import { previewImport, confirmImport } from './client'
```

Wait — the imports are already at the top of the file. Instead, add the two new functions to the existing import list at the top:

Change the existing import block from:
```ts
import {
  getPipelineStatus,
  runPipeline,
  listContacts,
  getContact,
  sendContact,
  skipContact,
} from './client'
```

To:
```ts
import {
  getPipelineStatus,
  runPipeline,
  listContacts,
  getContact,
  sendContact,
  skipContact,
  previewImport,
  confirmImport,
} from './client'
```

Then add at the end of the file:

```ts
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
```

- [ ] **Step 2: Run tests — confirm FAIL**

```bash
cd web && npm test
```

Expected: FAIL — `previewImport` and `confirmImport` not exported from `client.ts`.

- [ ] **Step 3: Add `ImportPreview` interface and two functions to `web/src/api/client.ts`**

Add after the `ContactDetail` interface:

```ts
export interface ImportPreview {
  import_id: string
  preview: {
    new_chargers: number
    new_contacts: number
    new_templates: number
  }
}
```

Add after `skipContact`:

```ts
export function previewImport(snapshot: unknown): Promise<ImportPreview> {
  return request('/api/import/snapshot', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(snapshot),
  })
}

export function confirmImport(importId: string): Promise<{ ok: boolean }> {
  return request(`/api/import/snapshot/confirm/${importId}`, { method: 'POST' })
}
```

- [ ] **Step 4: Run tests — confirm PASS**

```bash
cd web && npm test
```

Expected:
```
Test Files: 3 passed (3)
Tests:      19 passed (19)
```

- [ ] **Step 5: Commit**

```bash
git add web/src/api/client.ts web/src/api/client.test.ts
git commit -m "feat(web): add previewImport and confirmImport API client functions"
```

---

## Chunk 2: History page implementation

### Task 2.1: Contact table with search and export links

**Files:**
- Create: `web/src/pages/History.test.tsx`
- Modify: `web/src/pages/History.tsx`

The table shows every contact returned by `GET /api/contacts` (default limit 100, all statuses). Columns: Date, Name, Address, Email, Parse Status. Search filters client-side on name/address/email. Export links are plain `<a href>` anchors — the browser navigates to the endpoint and the `Content-Disposition` header or the `download` attribute triggers a file save. No JS fetch needed.

- [ ] **Step 1: Install `@testing-library/user-event`**

```bash
cd web && npm install -D @testing-library/user-event
```

This package provides `userEvent.type`, `userEvent.upload` etc. that simulate real browser interaction (as opposed to `fireEvent` which is lower-level).

- [ ] **Step 2: Write failing tests**

Create `web/src/pages/History.test.tsx`:

```tsx
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
      id: 'msg2', name: null, address: null,
      email_primary: null, parse_status: 'unparsed',
      received_at: null, email_form: 'bob@test.com', raw_body: null,
      nearest_charger_id: null, distance_miles: null, geocache_hit: false, hubspot_status: null,
    },
  ]),
  previewImport: vi.fn().mockResolvedValue({
    import_id: 'imp-1',
    preview: { new_chargers: 3, new_contacts: 5, new_templates: 1 },
  }),
  confirmImport: vi.fn().mockResolvedValue({ ok: true }),
}))

test('shows all contacts in table after load', async () => {
  render(<History />)
  expect(await screen.findByText('Alice Smith')).toBeInTheDocument()
  expect(screen.getByText('(unparsed)')).toBeInTheDocument()
})

test('search by name filters out non-matching contacts', async () => {
  render(<History />)
  await screen.findByText('Alice Smith')
  await userEvent.type(screen.getByPlaceholderText(/search/i), 'Alice')
  expect(screen.getByText('Alice Smith')).toBeInTheDocument()
  expect(screen.queryByText('(unparsed)')).not.toBeInTheDocument()
})

test('search by email filters contacts', async () => {
  render(<History />)
  await screen.findByText('Alice Smith')
  await userEvent.type(screen.getByPlaceholderText(/search/i), 'alice@example')
  expect(screen.getByText('alice@example.com')).toBeInTheDocument()
  expect(screen.queryByText('(unparsed)')).not.toBeInTheDocument()
})

test('export links point to API endpoints', async () => {
  render(<History />)
  await screen.findByText('Alice Smith')
  expect(screen.getByRole('link', { name: /download json/i }))
    .toHaveAttribute('href', '/api/export/snapshot')
  expect(screen.getByRole('link', { name: /download csv/i }))
    .toHaveAttribute('href', '/api/export/csv')
})
```

- [ ] **Step 3: Run tests — confirm FAIL**

```bash
cd web && npm test
```

Expected: FAIL — placeholder `History.tsx` does not render table, search, or export links.

- [ ] **Step 4: Implement `web/src/pages/History.tsx`** (table + search + export; import flow comes in Task 2.2)

```tsx
import { useState, useEffect } from 'react'
import { listContacts } from '../api/client'
import type { Contact } from '../api/client'

const STATUS_BADGE: Record<string, string> = {
  parsed: 'text-green-700 bg-green-50',
  unparsed: 'text-gray-600 bg-gray-100',
}

export default function History() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')

  useEffect(() => {
    listContacts().then(setContacts).finally(() => setLoading(false))
  }, [])

  const filtered = query
    ? contacts.filter((c) => {
        const q = query.toLowerCase()
        return (
          c.name?.toLowerCase().includes(q) ||
          c.address?.toLowerCase().includes(q) ||
          c.email_primary?.toLowerCase().includes(q)
        )
      })
    : contacts

  return (
    <div className="space-y-6">
      {/* Header + export buttons */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">History</h1>
        <div className="flex gap-2">
          <a
            href="/api/export/snapshot"
            download="itselectric_snapshot.json"
            className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300
                       rounded-lg hover:bg-gray-50 transition-colors"
          >
            Download JSON
          </a>
          <a
            href="/api/export/csv"
            download
            className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300
                       rounded-lg hover:bg-gray-50 transition-colors"
          >
            Download CSV
          </a>
        </div>
      </div>

      {/* Search */}
      <input
        type="search"
        placeholder="Search by name, address, or email…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full max-w-md px-3 py-2 text-sm border border-gray-300 rounded-lg
                   focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

      {/* Contact table */}
      {loading ? (
        <div className="text-sm text-gray-400">Loading…</div>
      ) : filtered.length === 0 ? (
        <div className="text-sm text-gray-400">No contacts found.</div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {['Date', 'Name', 'Address', 'Email', 'Status'].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {filtered.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {c.received_at ? new Date(c.received_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {c.name || '(unparsed)'}
                  </td>
                  <td className="px-4 py-3 text-gray-600 max-w-xs truncate">
                    {c.address || '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {c.email_primary || '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        STATUS_BADGE[c.parse_status] ?? 'text-gray-500 bg-gray-100'
                      }`}
                    >
                      {c.parse_status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Run tests — confirm PASS**

```bash
cd web && npm test
```

Expected:
```
Test Files: 4 passed (4)
Tests:      23 passed (23)
```

- [ ] **Step 6: Commit**

```bash
git add web/src/pages/History.tsx web/src/pages/History.test.tsx web/package.json web/package-lock.json
git commit -m "feat(web): History page with contact table, client-side search, export download links"
```

---

### Task 2.2: Import flow

**Files:**
- Modify: `web/src/pages/History.tsx` — add import section with state machine
- Modify: `web/src/pages/History.test.tsx` — add import flow tests

The import flow cycles through five states: `idle` (shows file picker) → `loading` (file read + API call) → `preview` (shows diff counts + Confirm button) → `confirming` (API call in flight) → `done` (success message). A `FileReader` reads the JSON file client-side, then passes it to `previewImport`.

- [ ] **Step 1: Write failing import flow tests**

Add to the end of `web/src/pages/History.test.tsx`:

```tsx
test('file upload triggers preview and shows Confirm button', async () => {
  render(<History />)
  await screen.findByText('Alice Smith') // wait for initial load

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
```

- [ ] **Step 2: Run tests — confirm FAIL**

```bash
cd web && npm test
```

Expected: FAIL — no file input with "upload snapshot" label exists yet.

- [ ] **Step 3: Add import state machine to `web/src/pages/History.tsx`**

Replace the existing two import lines at the top of `History.tsx`:

```tsx
// BEFORE (remove these two lines):
import { listContacts } from '../api/client'
import type { Contact } from '../api/client'

// AFTER (replace with these two lines):
import { listContacts, previewImport, confirmImport } from '../api/client'
import type { Contact, ImportPreview } from '../api/client'
```

Add state variables inside `History()`, after the existing `const [query, setQuery]` line:

```tsx
type ImportPhase = 'idle' | 'loading' | 'preview' | 'confirming' | 'done'
const [importPhase, setImportPhase] = useState<ImportPhase>('idle')
const [importData, setImportData] = useState<ImportPreview | null>(null)
const [importError, setImportError] = useState<string | null>(null)
```

Add handler functions inside `History()`, after the `filtered` declaration:

```tsx
function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
  const file = e.target.files?.[0]
  if (!file) return
  setImportPhase('loading')
  setImportError(null)
  const reader = new FileReader()
  reader.onload = (ev) => {
    void (async () => {
      try {
        const snapshot: unknown = JSON.parse(ev.target?.result as string)
        const result = await previewImport(snapshot)
        setImportData(result)
        setImportPhase('preview')
      } catch (err) {
        setImportError(String(err))
        setImportPhase('idle')
      }
    })()
  }
  reader.readAsText(file)
}

async function handleConfirmImport() {
  if (!importData) return
  setImportPhase('confirming')
  try {
    await confirmImport(importData.import_id)
    setImportPhase('done')
  } catch (err) {
    setImportError(String(err))
    setImportPhase('idle')
  }
}
```

Add the import section at the very end of the JSX `return`, after the table block (but still inside the outer `<div className="space-y-6">`):

```tsx
{/* Import section */}
<div className="border-t border-gray-200 pt-6">
  <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
    Import Snapshot
  </h2>

  {importPhase === 'done' ? (
    <div className="flex items-center gap-3">
      <span className="text-sm text-green-700">Import complete.</span>
      <button
        onClick={() => { setImportPhase('idle'); setImportData(null) }}
        className="text-sm text-blue-600 hover:underline"
      >
        Import another
      </button>
    </div>
  ) : importPhase === 'preview' && importData ? (
    <div className="space-y-3">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm max-w-xs">
        <dt className="text-gray-500">New contacts</dt>
        <dd className="font-medium text-gray-900">{importData.preview.new_contacts}</dd>
        <dt className="text-gray-500">New chargers</dt>
        <dd className="font-medium text-gray-900">{importData.preview.new_chargers}</dd>
        <dt className="text-gray-500">New templates</dt>
        <dd className="font-medium text-gray-900">{importData.preview.new_templates}</dd>
      </dl>
      <button
        onClick={() => void handleConfirmImport()}
        disabled={importPhase === 'confirming'}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium
                   hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        Confirm Import
      </button>
    </div>
  ) : (
    <label className="flex flex-col gap-1.5 cursor-pointer">
      <span className="text-sm text-gray-600">Upload snapshot (JSON)</span>
      <input
        aria-label="Upload snapshot"
        type="file"
        accept=".json,application/json"
        onChange={handleFileChange}
        disabled={importPhase === 'loading'}
        className="text-sm text-gray-600
                   file:mr-3 file:py-1.5 file:px-3 file:rounded-lg
                   file:border file:border-gray-300 file:cursor-pointer
                   file:text-sm file:font-medium file:text-gray-700
                   file:bg-white hover:file:bg-gray-50"
      />
      {importPhase === 'loading' && (
        <span className="text-xs text-gray-400">Reading file…</span>
      )}
    </label>
  )}

  {importError && (
    <p className="mt-2 text-sm text-red-600">{importError}</p>
  )}
</div>
```

> **Note on `void` keyword:** `handleFileChange` and `handleConfirmImport` are async, but the onClick handler expects `void`. Wrapping with `void` suppresses the unhandled-promise-rejection lint warning without adding extra boilerplate. The FileReader `onload` callback uses an immediately-invoked async IIFE (`void (async () => { ... })()`) for the same reason.

- [ ] **Step 4: Run tests — confirm PASS**

```bash
cd web && npm test
```

Expected:
```
Test Files: 4 passed (4)
Tests:      25 passed (25)
```

- [ ] **Step 5: Run production build — confirm clean**

```bash
cd web && npm run build
```

Expected: clean TypeScript compilation + Vite bundle, no errors.

- [ ] **Step 6: Run full test suite**

```bash
python3 -m pytest tests/ --ignore=tests/test_gui_pipeline.py -q
cd web && npm test
```

Expected:
```
217 passed in Xs     # Python (no backend changes; just confirming nothing regressed)
Tests: 25 passed     # Vitest
```

- [ ] **Step 7: Final commit**

```bash
git add web/src/pages/History.tsx web/src/pages/History.test.tsx
git commit -m "feat(web): History import flow — file picker, preview diff, confirm"
```

---

## Done

Phase 3 delivers:

- **Nav + route:** "History" sidebar link and `/history` route wired into the app shell
- **API client:** `previewImport` and `confirmImport` typed functions with 2 new unit tests
- **History table:** all contacts fetched via `GET /api/contacts`, rendered with Date/Name/Address/Email/Status columns, client-side search filtering by name, address, or email
- **Export links:** "Download JSON" and "Download CSV" anchor tags pointing at the existing backend endpoints — no JS required, browser handles the file save
- **Import flow:** file picker with `aria-label` → FileReader JSON parse → `POST /api/import/snapshot` → preview diff (new contacts/chargers/templates counts) → Confirm button → `POST /api/import/snapshot/confirm/{import_id}` → success state with "Import another" reset
- **Test suite:** 217 Python + 25 Vitest tests passing, clean production build
