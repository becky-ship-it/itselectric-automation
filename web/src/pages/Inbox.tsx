import { useState, useEffect } from 'react'
import { listContacts, Contact } from '../api/client'
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

  function reload() {
    setLoading(true)
    listContacts(filter ? { status: filter } : undefined)
      .then(setContacts)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    reload()
  }, [filter])

  return (
    <div className="flex h-full gap-0 -m-6">
      <div className="w-80 shrink-0 border-r border-gray-200 flex flex-col h-full">
        <div className="flex border-b border-gray-200">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => {
                setFilter(tab.key)
                setSelected(null)
              }}
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

        <div className="overflow-y-auto flex-1">
          {loading ? (
            <div className="p-4 text-sm text-gray-400">Loading…</div>
          ) : contacts.length === 0 ? (
            <div className="p-4 text-sm text-gray-400">No contacts.</div>
          ) : (
            contacts.map((c) => (
              <ContactRow
                key={c.id}
                contact={c}
                selected={c.id === selected}
                onClick={() => setSelected(c.id)}
              />
            ))
          )}
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {selected ? (
          <InboxDetail id={selected} onAction={reload} />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            Select a contact to preview
          </div>
        )}
      </div>
    </div>
  )
}
