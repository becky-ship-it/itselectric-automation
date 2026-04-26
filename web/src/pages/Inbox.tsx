import { useState, useEffect } from 'react'
import { listContacts, deleteContact } from '../api/client'
import type { Contact } from '../api/client'
import ContactRow from '../components/ContactRow'
import InboxDetail from './InboxDetail'

const TABS = [
  { key: '', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'unparsed', label: 'Unparsed' },
]

export default function Inbox() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [filter, setFilter] = useState('')
  const [selected, setSelected] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [checked, setChecked] = useState<Set<string>>(new Set())
  const [deleting, setDeleting] = useState(false)

  function reload() {
    setLoading(true)
    listContacts(filter ? { status: filter } : undefined)
      .then((cs) => { setContacts(cs); setChecked(new Set()) })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    reload()
  }, [filter])

  function toggleCheck(id: string) {
    setChecked((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function toggleAll() {
    setChecked((prev) =>
      prev.size === contacts.length ? new Set() : new Set(contacts.map((c) => c.id))
    )
  }

  async function handleDelete(id: string) {
    if (!window.confirm('Delete this contact? This cannot be undone.')) return
    await deleteContact(id)
    if (selected === id) setSelected(null)
    reload()
  }

  async function handleBulkDelete() {
    const ids = [...checked]
    if (ids.length === 0) return
    if (!window.confirm(`Delete ${ids.length} contact(s)? This cannot be undone.`)) return
    setDeleting(true)
    try {
      await Promise.all(ids.map(deleteContact))
      if (selected && ids.includes(selected)) setSelected(null)
      reload()
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="flex h-full gap-0 -m-6">
      <div className="w-80 shrink-0 border-r border-gray-200 flex flex-col h-full">
        <div className="flex border-b border-gray-200">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => { setFilter(tab.key); setSelected(null) }}
              className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
                filter === tab.key
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {checked.size > 0 && (
          <div className="flex items-center justify-between px-3 py-2 bg-red-50 border-b border-red-100">
            <span className="text-xs text-red-700">{checked.size} selected</span>
            <button
              onClick={() => void handleBulkDelete()}
              disabled={deleting}
              className="text-xs font-medium text-red-700 hover:text-red-900 disabled:opacity-50"
            >
              {deleting ? 'Deleting…' : 'Delete selected'}
            </button>
          </div>
        )}

        <div className="flex items-center gap-2 px-3 py-1.5 border-b border-gray-100">
          <input
            type="checkbox"
            checked={contacts.length > 0 && checked.size === contacts.length}
            onChange={toggleAll}
            className="h-3.5 w-3.5 rounded border-gray-300"
          />
          <span className="text-xs text-gray-400">{contacts.length} contacts</span>
        </div>

        <div className="overflow-y-auto flex-1">
          {loading ? (
            <div className="p-4 text-sm text-gray-400">Loading…</div>
          ) : contacts.length === 0 ? (
            <div className="p-4 text-sm text-gray-400">No contacts.</div>
          ) : (
            contacts.map((c) => (
              <div key={c.id} className="flex items-stretch">
                <div className="flex items-center pl-3 pr-1 border-b border-gray-100">
                  <input
                    type="checkbox"
                    checked={checked.has(c.id)}
                    onChange={() => toggleCheck(c.id)}
                    className="h-3.5 w-3.5 rounded border-gray-300"
                    onClick={(e) => e.stopPropagation()}
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <ContactRow
                    contact={c}
                    selected={c.id === selected}
                    onClick={() => setSelected(c.id)}
                    onDelete={() => void handleDelete(c.id)}
                  />
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {selected ? (
          <InboxDetail id={selected} onAction={reload} onDelete={() => { setSelected(null); reload() }} />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            Select a contact to preview
          </div>
        )}
      </div>
    </div>
  )
}
