# Website Phase 4 — Config Page: Decision Tree Editor + Template Management

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/config` page with a template editor (list + subject/HTML editor + sandboxed preview) and a decision tree YAML editor with a dry-run test button; also set the itselectric favicon.

**Architecture:** Single new `Config` page at `/config` with two stacked sections. Templates section: master/detail layout (name list + editor panel). Decision tree section: full-width YAML textarea + Save/Test buttons + results table. `js-yaml` converts between backend JSON and editable YAML in the browser; the iframe preview uses `srcdoc` + `sandbox` to render template HTML safely. Five new functions added to the existing `client.ts` with matching unit tests.

**Tech Stack:** React 19, TypeScript 5 (`verbatimModuleSyntax` + `erasableSyntaxOnly`), Tailwind CSS v4, `js-yaml` 4.x, Vitest 4 + jsdom + @testing-library/react + @testing-library/user-event.

**Key TypeScript rules (enforced by tsconfig):**
- Type-only imports MUST use `import type { Foo }` — never `import { Foo }` for types
- No parameter properties in class constructors (`constructor(public x: string)` is banned)
- `vi.mock(...)` calls MUST be at module scope, not inside test bodies

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `web/public/favicon.png` | Create | Itselectric favicon downloaded from CDN |
| `web/index.html` | Modify | Update `<link rel="icon">` to PNG |
| `web/src/components/Sidebar.tsx` | Modify | Add "Config" nav link |
| `web/src/App.tsx` | Modify | Add `/config` route + import Config |
| `web/src/App.test.tsx` | Modify | Add Config nav assertion + 5 new client mocks |
| `web/src/api/client.ts` | Modify | Add `Template`, decision tree interfaces, 5 new functions |
| `web/src/api/client.test.ts` | Modify | Tests for 5 new client functions |
| `web/src/pages/Config.tsx` | Create | Config page: Templates section + Decision Tree section |
| `web/src/pages/Config.test.tsx` | Create | Unit tests for Config page |

---

## Chunk 1: Favicon + routing scaffold

### Task 1.1: Favicon

**Files:**
- Create: `web/public/favicon.png`
- Modify: `web/index.html`

- [ ] **Step 1: Download favicon PNG**

```bash
curl -L "https://cdn.prod.website-files.com/6297984862f8ce031cbee04f/690b75fb67ccc9099287c620_itselectric%20favicon.png" \
  -o web/public/favicon.png
```

Expected: `web/public/favicon.png` exists (non-zero bytes).

- [ ] **Step 2: Update `web/index.html`**

Replace the existing `<link rel="icon" ...>` line with:

```html
<link rel="icon" type="image/png" href="/favicon.png" />
```

Full updated `web/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/png" href="/favicon.png" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>It's Electric</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

(Also update the `<title>` from "web" to "It's Electric" while here.)

- [ ] **Step 3: Commit**

```bash
git add web/public/favicon.png web/index.html
git commit -m "feat(web): add itselectric favicon and update page title"
```

---

### Task 1.2: Config route and nav link

**Files:**
- Modify: `web/src/App.test.tsx`
- Create: `web/src/pages/Config.tsx` (placeholder)
- Modify: `web/src/components/Sidebar.tsx`
- Modify: `web/src/App.tsx`

- [ ] **Step 1: Update `web/src/App.test.tsx` — add Config nav assertion and 5 new client mocks**

Replace the entire file:

```tsx
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import App from './App'

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
  listTemplates: vi.fn().mockResolvedValue([]),
  updateTemplate: vi.fn().mockResolvedValue({ name: 't', subject: 's', body_html: '', updated_at: null }),
  getDecisionTree: vi.fn().mockResolvedValue(null),
  updateDecisionTree: vi.fn().mockResolvedValue({}),
  testDecisionTree: vi.fn().mockResolvedValue({ results: [] }),
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
  expect(screen.getByText('Config')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run tests — confirm FAIL**

```bash
cd web && npm test
```

Expected: FAIL — "Config" not found in sidebar.

- [ ] **Step 3: Create placeholder `web/src/pages/Config.tsx`**

```tsx
export default function Config() {
  return <h1 className="text-2xl font-semibold text-gray-900">Config</h1>
}
```

- [ ] **Step 4: Add Config link to `web/src/components/Sidebar.tsx`**

Replace the `links` array:

```tsx
const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/inbox', label: 'Inbox' },
  { to: '/history', label: 'History' },
  { to: '/config', label: 'Config' },
]
```

- [ ] **Step 5: Add `/config` route to `web/src/App.tsx`**

```tsx
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Inbox from './pages/Inbox'
import History from './pages/History'
import Config from './pages/Config'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout pipelineStatus="idle" lastRunAt={null} />}>
        <Route index element={<Dashboard />} />
        <Route path="inbox" element={<Inbox />} />
        <Route path="history" element={<History />} />
        <Route path="config" element={<Config />} />
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
Test Files: 4 passed (4)
Tests:      28 passed (28)
```

- [ ] **Step 7: Commit**

```bash
git add web/src/components/Sidebar.tsx web/src/App.tsx web/src/pages/Config.tsx web/src/App.test.tsx
git commit -m "feat(web): add Config route and sidebar nav link"
```

---

## Chunk 2: API client extensions

### Task 2.1: Install js-yaml

**Files:**
- Modify: `web/package.json` (via npm)

- [ ] **Step 1: Install js-yaml**

```bash
cd web && npm install js-yaml && npm install -D @types/js-yaml
```

Expected: `js-yaml` in `dependencies`, `@types/js-yaml` in `devDependencies` in `package.json`.

- [ ] **Step 2: Commit**

```bash
git add web/package.json web/package-lock.json
git commit -m "feat(web): add js-yaml for YAML↔JSON conversion in decision tree editor"
```

---

### Task 2.2: Add Template and decision tree client functions

**Files:**
- Modify: `web/src/api/client.ts`
- Modify: `web/src/api/client.test.ts`

- [ ] **Step 1: Write failing tests**

Add to the import list at the top of `web/src/api/client.test.ts` (extend the existing named import):

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
  listTemplates,
  updateTemplate,
  getDecisionTree,
  updateDecisionTree,
  testDecisionTree,
} from './client'
```

Add at the end of `web/src/api/client.test.ts`:

```ts
describe('listTemplates', () => {
  it('GETs /api/templates and returns array', async () => {
    mockFetch([{ name: 'general_car_info', subject: 'Hi', body_html: '<p>Hi</p>', updated_at: null }])
    const result = await listTemplates()
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('general_car_info')
    expect(fetch).toHaveBeenCalledWith('/api/templates')
  })
})

describe('updateTemplate', () => {
  it('PUTs to /api/templates/{name} with subject and body_html', async () => {
    mockFetch({ name: 'general_car_info', subject: 'Updated', body_html: '<p>New</p>', updated_at: null })
    const result = await updateTemplate('general_car_info', { subject: 'Updated', body_html: '<p>New</p>' })
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
```

- [ ] **Step 2: Run tests — confirm FAIL**

```bash
cd web && npm test
```

Expected: FAIL — `listTemplates` and others not exported from `client.ts`.

- [ ] **Step 3: Add interfaces and functions to `web/src/api/client.ts`**

Add after the `ImportPreview` interface:

```ts
export interface Template {
  name: string
  subject: string | null
  body_html: string | null
  updated_at: string | null
}

export interface TemplateIn {
  subject: string
  body_html: string
}

export interface DecisionTreeTestResult {
  id: string
  name?: string | null
  address?: string | null
  parsed: boolean
  template: string | null
}

export interface DecisionTreeTestResponse {
  results: DecisionTreeTestResult[]
  error?: string
}
```

Add after `confirmImport`:

```ts
export function listTemplates(): Promise<Template[]> {
  return request('/api/templates')
}

export function updateTemplate(name: string, body: TemplateIn): Promise<Template> {
  return request(`/api/templates/${name}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function getDecisionTree(): Promise<unknown> {
  return request('/api/decision-tree')
}

export function updateDecisionTree(tree: unknown): Promise<unknown> {
  return request('/api/decision-tree', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(tree),
  })
}

export function testDecisionTree(): Promise<DecisionTreeTestResponse> {
  return request('/api/decision-tree/test', { method: 'POST' })
}
```

- [ ] **Step 4: Run tests — confirm PASS**

```bash
cd web && npm test
```

Expected:
```
Test Files: 4 passed (4)
Tests:      39 passed (39)
```

- [ ] **Step 5: Commit**

```bash
git add web/src/api/client.ts web/src/api/client.test.ts
git commit -m "feat(web): add Template and decision tree API client functions"
```

---

## Chunk 3: Config page implementation

### Task 3.1: Config page — Templates section

**Files:**
- Create: `web/src/pages/Config.test.tsx`
- Modify: `web/src/pages/Config.tsx`

- [ ] **Step 1: Write failing tests**

Create `web/src/pages/Config.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import Config from './Config'

vi.mock('../api/client', () => ({
  listTemplates: vi.fn().mockResolvedValue([
    { name: 'general_car_info', subject: 'Hello!', body_html: '<p>Hi there</p>', updated_at: '2026-04-20T10:00:00Z' },
    { name: 'waitlist', subject: 'Join the waitlist', body_html: '<p>Waitlist</p>', updated_at: '2026-04-20T10:00:00Z' },
  ]),
  updateTemplate: vi.fn().mockImplementation((name: string, body: { subject: string; body_html: string }) =>
    Promise.resolve({ name, subject: body.subject, body_html: body.body_html, updated_at: new Date().toISOString() })
  ),
  getDecisionTree: vi.fn().mockResolvedValue(null),
  updateDecisionTree: vi.fn().mockResolvedValue({}),
  testDecisionTree: vi.fn().mockResolvedValue({
    results: [
      { id: 'msg1', name: 'Alice Smith', address: '123 Main St DC', parsed: true, template: 'general_car_info' },
      { id: 'msg2', name: null, address: null, parsed: false, template: null },
    ],
  }),
}))

test('shows template names after load', async () => {
  render(<Config />)
  expect(await screen.findByRole('button', { name: 'general_car_info' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'waitlist' })).toBeInTheDocument()
})

test('clicking template shows subject and body in editor', async () => {
  render(<Config />)
  await screen.findByRole('button', { name: 'general_car_info' })
  await userEvent.click(screen.getByRole('button', { name: 'general_car_info' }))
  expect(screen.getByDisplayValue('Hello!')).toBeInTheDocument()
  expect(screen.getByDisplayValue('<p>Hi there</p>')).toBeInTheDocument()
})

test('saving template calls updateTemplate and shows Saved feedback', async () => {
  const { updateTemplate } = await import('../api/client')
  render(<Config />)
  await screen.findByRole('button', { name: 'general_car_info' })
  await userEvent.click(screen.getByRole('button', { name: 'general_car_info' }))
  const subjectInput = screen.getByDisplayValue('Hello!')
  await userEvent.clear(subjectInput)
  await userEvent.type(subjectInput, 'New Subject')
  await userEvent.click(screen.getByRole('button', { name: /save template/i }))
  expect(updateTemplate).toHaveBeenCalledWith(
    'general_car_info',
    expect.objectContaining({ subject: 'New Subject' })
  )
  expect(await screen.findByText('Saved.')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run tests — confirm FAIL**

```bash
cd web && npm test
```

Expected: FAIL — placeholder Config.tsx doesn't render templates.

- [ ] **Step 3: Implement `web/src/pages/Config.tsx` (Templates section; decision tree section added in Task 3.2)**

```tsx
import { useState, useEffect } from 'react'
import yaml from 'js-yaml'
import {
  listTemplates,
  updateTemplate,
  getDecisionTree,
  updateDecisionTree,
  testDecisionTree,
} from '../api/client'
import type { Template, DecisionTreeTestResult } from '../api/client'

export default function Config() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [selectedName, setSelectedName] = useState<string | null>(null)
  const [subject, setSubject] = useState('')
  const [bodyHtml, setBodyHtml] = useState('')
  const [tmplSaving, setTmplSaving] = useState(false)
  const [tmplSaved, setTmplSaved] = useState(false)
  const [tmplError, setTmplError] = useState<string | null>(null)

  const [treeYaml, setTreeYaml] = useState('')
  const [treeSaving, setTreeSaving] = useState(false)
  const [treeSaved, setTreeSaved] = useState(false)
  const [treeTesting, setTreeTesting] = useState(false)
  const [treeError, setTreeError] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<DecisionTreeTestResult[] | null>(null)

  useEffect(() => {
    listTemplates().then(setTemplates)
    getDecisionTree().then((tree) => {
      if (tree) setTreeYaml(yaml.dump(tree))
    })
  }, [])

  function selectTemplate(name: string) {
    const t = templates.find((t) => t.name === name)
    if (!t) return
    setSelectedName(name)
    setSubject(t.subject ?? '')
    setBodyHtml(t.body_html ?? '')
    setTmplSaved(false)
    setTmplError(null)
  }

  async function handleSaveTemplate() {
    if (!selectedName) return
    setTmplSaving(true)
    setTmplError(null)
    try {
      const updated = await updateTemplate(selectedName, { subject, body_html: bodyHtml })
      setTemplates((ts) => ts.map((t) => (t.name === selectedName ? updated : t)))
      setTmplSaved(true)
    } catch (err) {
      setTmplError(String(err))
    } finally {
      setTmplSaving(false)
    }
  }

  async function handleSaveTree() {
    setTreeSaving(true)
    setTreeError(null)
    try {
      const tree = yaml.load(treeYaml)
      await updateDecisionTree(tree as Record<string, unknown>)
      setTreeSaved(true)
    } catch (err) {
      setTreeError(String(err))
    } finally {
      setTreeSaving(false)
    }
  }

  async function handleTestTree() {
    setTreeTesting(true)
    setTreeError(null)
    setTestResults(null)
    try {
      const res = await testDecisionTree()
      setTestResults(res.results)
    } catch (err) {
      setTreeError(String(err))
    } finally {
      setTreeTesting(false)
    }
  }

  return (
    <div className="space-y-10">
      <h1 className="text-2xl font-semibold text-gray-900">Config</h1>

      <section>
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">Templates</h2>
        <div className="flex border border-gray-200 rounded-lg overflow-hidden min-h-64">
          <div className="w-52 shrink-0 border-r border-gray-200 overflow-y-auto">
            {templates.length === 0 ? (
              <div className="p-3 text-sm text-gray-400">No templates.</div>
            ) : (
              templates.map((t) => (
                <button
                  key={t.name}
                  onClick={() => selectTemplate(t.name)}
                  className={`w-full text-left px-3 py-2.5 text-sm border-b border-gray-100 truncate transition-colors ${
                    selectedName === t.name
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {t.name}
                </button>
              ))
            )}
          </div>

          <div className="flex-1 p-4 space-y-3">
            {!selectedName ? (
              <p className="text-sm text-gray-400">Select a template to edit.</p>
            ) : (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Subject</label>
                  <input
                    type="text"
                    value={subject}
                    onChange={(e) => { setSubject(e.target.value); setTmplSaved(false) }}
                    className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg
                               focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Body HTML</label>
                  <textarea
                    value={bodyHtml}
                    onChange={(e) => { setBodyHtml(e.target.value); setTmplSaved(false) }}
                    rows={8}
                    className="w-full px-3 py-1.5 text-sm font-mono border border-gray-300 rounded-lg
                               focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Preview</label>
                  <iframe
                    srcDoc={bodyHtml}
                    sandbox=""
                    title="Template preview"
                    className="w-full h-48 border border-gray-200 rounded-lg bg-white"
                  />
                </div>
                <div className="flex items-center gap-3">
                  <button
                    aria-label="Save template"
                    onClick={() => void handleSaveTemplate()}
                    disabled={tmplSaving}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium
                               hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    {tmplSaving ? 'Saving…' : 'Save'}
                  </button>
                  {tmplSaved && <span className="text-sm text-green-700">Saved.</span>}
                  {tmplError && <span className="text-sm text-red-600">{tmplError}</span>}
                </div>
              </>
            )}
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">Decision Tree</h2>
        <div className="space-y-3">
          <textarea
            aria-label="Decision tree YAML"
            value={treeYaml}
            onChange={(e) => { setTreeYaml(e.target.value); setTreeSaved(false) }}
            rows={18}
            className="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-lg
                       focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
          />
          <div className="flex items-center gap-3">
            <button
              aria-label="Save decision tree"
              onClick={() => void handleSaveTree()}
              disabled={treeSaving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium
                         hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {treeSaving ? 'Saving…' : 'Save'}
            </button>
            <button
              onClick={() => void handleTestTree()}
              disabled={treeTesting}
              className="px-4 py-2 bg-gray-100 text-gray-700 border border-gray-300 rounded-lg text-sm font-medium
                         hover:bg-gray-200 disabled:opacity-50 transition-colors"
            >
              {treeTesting ? 'Testing…' : 'Test'}
            </button>
            {treeSaved && <span className="text-sm text-green-700">Saved.</span>}
            {treeError && <span className="text-sm text-red-600">{treeError}</span>}
          </div>

          {testResults !== null && (
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {['Name', 'Address', 'Template'].map((h) => (
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
                  {testResults.map((r, i) => (
                    <tr key={i}>
                      <td className="px-4 py-3 text-gray-900">{r.name ?? '(unparsed)'}</td>
                      <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{r.address ?? '—'}</td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-700">{r.template ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
```

> **Note on `aria-label` on buttons:** The template Save and decision tree Save buttons have distinct `aria-label`s ("Save template" vs "Save decision tree") so tests can target them unambiguously via `getByRole('button', { name: /save template/i })`.

- [ ] **Step 4: Run tests — confirm PASS (Templates section)**

```bash
cd web && npm test
```

Expected:
```
Test Files: 5 passed (5)
Tests:      42 passed (42)
```

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/Config.tsx web/src/pages/Config.test.tsx
git commit -m "feat(web): Config page with template list and editor"
```

---

### Task 3.2: Config page — Decision tree tests

**Files:**
- Modify: `web/src/pages/Config.test.tsx`

The decision tree section is already implemented in `Config.tsx` from Task 3.1. This task adds tests for it.

- [ ] **Step 1: Write decision tree tests**

Add to the end of `web/src/pages/Config.test.tsx`:

```tsx
test('decision tree YAML textarea is empty when no tree saved', async () => {
  render(<Config />)
  const textarea = await screen.findByRole('textbox', { name: /decision tree yaml/i })
  expect(textarea).toHaveValue('')
})

test('clicking Save decision tree calls updateDecisionTree', async () => {
  const { updateDecisionTree } = await import('../api/client')
  render(<Config />)
  const textarea = await screen.findByRole('textbox', { name: /decision tree yaml/i })
  await userEvent.type(textarea, 'template: general_car_info')
  await userEvent.click(screen.getByRole('button', { name: /save decision tree/i }))
  expect(updateDecisionTree).toHaveBeenCalled()
  expect(await screen.findByText('Saved.')).toBeInTheDocument()
})

test('clicking Test calls testDecisionTree and shows results table', async () => {
  render(<Config />)
  await screen.findByRole('button', { name: 'general_car_info' })
  await userEvent.click(screen.getByRole('button', { name: /test/i }))
  expect(await screen.findByText('Alice Smith')).toBeInTheDocument()
  expect(screen.getAllByText('general_car_info').length).toBeGreaterThan(0)
})
```

- [ ] **Step 2: Run tests — confirm PASS**

```bash
cd web && npm test
```

Expected:
```
Test Files: 5 passed (5)
Tests:      45 passed (45)
```

- [ ] **Step 3: Run production build — confirm clean**

```bash
cd web && npm run build
```

Expected: clean TypeScript compilation + Vite bundle, no errors or warnings.

- [ ] **Step 4: Final commit**

```bash
git add web/src/pages/Config.test.tsx
git commit -m "feat(web): decision tree YAML editor with save and dry-run test"
```

---

## Done

Phase 4 delivers:

- **Favicon:** itselectric PNG favicon; page title updated to "It's Electric"
- **Nav + route:** "Config" sidebar link and `/config` route wired into the app shell
- **API client:** `listTemplates`, `updateTemplate`, `getDecisionTree`, `updateDecisionTree`, `testDecisionTree` with matching unit tests
- **Templates section:** scrollable name list; click to open editor with subject input, body_html textarea, and sandboxed iframe preview; Save calls `PUT /api/templates/{name}` and shows "Saved." feedback
- **Decision tree section:** YAML textarea loaded via `GET /api/decision-tree` → `js-yaml.dump`; Save parses YAML → `PUT /api/decision-tree`; Test button → `POST /api/decision-tree/test` → results table (Name / Address / Template)
- **Test suite:** 45 Vitest tests passing, clean production build
