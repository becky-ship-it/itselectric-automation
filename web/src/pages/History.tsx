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
    </div>
  )
}
