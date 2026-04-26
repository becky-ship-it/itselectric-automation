import type { Contact } from '../api/client'

interface Props {
  contact: Contact
  selected: boolean
  onClick: () => void
  onDelete?: () => void
}

const STATUS_BADGE: Record<string, string> = {
  sent:     'text-green-700 bg-green-50',
  pending:  'text-orange-700 bg-orange-50',
  skipped:  'text-gray-500 bg-gray-100',
  failed:   'text-red-700 bg-red-50',
  unparsed: 'text-gray-500 bg-gray-100',
  parsed:   'text-blue-700 bg-blue-50',
}

export default function ContactRow({ contact, selected, onClick, onDelete }: Props) {
  return (
    <div className={`relative group border-b border-gray-100 ${selected ? 'border-l-2 border-l-blue-500' : ''}`}>
      <button
        onClick={onClick}
        className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors pr-8 ${
          selected ? 'bg-blue-50' : ''
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-900 truncate">
            {contact.name || '(no name)'}
          </span>
          {(() => {
            const label = contact.outbound_status ?? contact.parse_status
            return (
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_BADGE[label] ?? 'text-gray-500 bg-gray-100'}`}>
                {label}
              </span>
            )
          })()}
        </div>
        <div className="text-xs text-gray-500 mt-0.5 truncate">{contact.address || '—'}</div>
        {contact.raw_body && (
          <div className="text-xs text-gray-400 mt-1 line-clamp-2 whitespace-pre-line leading-relaxed">
            {contact.raw_body.trim()}
          </div>
        )}
        <div className="text-xs text-gray-400 mt-0.5">
          {contact.received_at ? new Date(contact.received_at).toLocaleDateString() : ''}
        </div>
      </button>
      {onDelete && (
        <button
          aria-label="Delete contact"
          onClick={(e) => { e.stopPropagation(); onDelete() }}
          className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100
                     text-gray-400 hover:text-red-600 transition-all p-1 rounded"
        >
          ×
        </button>
      )}
    </div>
  )
}
