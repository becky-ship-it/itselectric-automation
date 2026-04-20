import { useState, useEffect } from 'react'
import { listContacts, previewImport, confirmImport } from '../api/client'
import type { Contact, ImportPreview } from '../api/client'

const STATUS_BADGE: Record<string, string> = {
  parsed: 'text-green-700 bg-green-50',
  unparsed: 'text-gray-600 bg-gray-100',
}

export default function History() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')

  type ImportPhase = 'idle' | 'loading' | 'preview' | 'confirming' | 'done'
  const [importPhase, setImportPhase] = useState<ImportPhase>('idle')
  const [importData, setImportData] = useState<ImportPreview | null>(null)
  const [importError, setImportError] = useState<string | null>(null)

  useEffect(() => {
    listContacts().then(setContacts).finally(() => setLoading(false))
  }, [])

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

      <input
        type="search"
        placeholder="Search by name, address, or email…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full max-w-md px-3 py-2 text-sm border border-gray-300 rounded-lg
                   focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

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
        ) : (importPhase === 'preview' || importPhase === 'confirming') && importData ? (
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
    </div>
  )
}
