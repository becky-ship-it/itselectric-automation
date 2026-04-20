import { Contact } from '../api/client'

interface Props {
  contact: Contact
  selected: boolean
  onClick: () => void
}

const STATUS_BADGE: Record<string, string> = {
  parsed: 'text-green-700 bg-green-50',
  unparsed: 'text-gray-600 bg-gray-100',
}

export default function ContactRow({ contact, selected, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-3 border-b border-gray-100 hover:bg-gray-50 transition-colors ${
        selected ? 'bg-blue-50 border-l-2 border-l-blue-500' : ''
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-900 truncate">
          {contact.name || '(unparsed)'}
        </span>
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            STATUS_BADGE[contact.parse_status] ?? 'text-gray-500 bg-gray-100'
          }`}
        >
          {contact.parse_status}
        </span>
      </div>
      <div className="text-xs text-gray-500 mt-0.5 truncate">{contact.address || '—'}</div>
      <div className="text-xs text-gray-400 mt-0.5">
        {contact.received_at ? new Date(contact.received_at).toLocaleDateString() : ''}
      </div>
    </button>
  )
}
