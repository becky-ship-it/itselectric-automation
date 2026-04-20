import { useState, useEffect } from 'react'
import { getContact, sendContact, skipContact, ContactDetail } from '../api/client'

interface Props {
  id: string
  onAction: () => void
}

export function InboxDetail({ id, onAction }: Props) {
  const [detail, setDetail] = useState<ContactDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setDetail(null)
    setError(null)
    getContact(id)
      .then(setDetail)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [id])

  async function handleSend() {
    setSending(true)
    setError(null)
    try {
      await sendContact(id)
      onAction()
      const fresh = await getContact(id)
      setDetail(fresh)
    } catch (e) {
      setError(String(e))
    } finally {
      setSending(false)
    }
  }

  async function handleSkip() {
    setSending(true)
    try {
      await skipContact(id)
      onAction()
      const fresh = await getContact(id)
      setDetail(fresh)
    } catch (e) {
      setError(String(e))
    } finally {
      setSending(false)
    }
  }

  if (loading) return <div className="p-6 text-sm text-gray-400">Loading…</div>
  if (error) return <div className="p-6 text-sm text-red-600">{error}</div>
  if (!detail) return null

  const { contact, outbound_emails } = detail
  const outbound = outbound_emails[0] ?? null

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">{contact.name || '(no name)'}</h2>
        <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
          <dt className="text-gray-500">Address</dt>
          <dd className="text-gray-900">{contact.address || '—'}</dd>
          <dt className="text-gray-500">Email</dt>
          <dd className="text-gray-900">{contact.email_primary || '—'}</dd>
          <dt className="text-gray-500">Distance</dt>
          <dd className="text-gray-900">
            {contact.distance_miles != null
              ? `${contact.distance_miles.toFixed(1)} mi`
              : '—'}
          </dd>
          <dt className="text-gray-500">Status</dt>
          <dd className="text-gray-900">{contact.parse_status}</dd>
        </dl>
      </div>

      {outbound ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Email preview
            </h3>
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                outbound.status === 'sent'
                  ? 'bg-green-100 text-green-700'
                  : outbound.status === 'pending'
                  ? 'bg-yellow-100 text-yellow-700'
                  : outbound.status === 'skipped'
                  ? 'bg-gray-100 text-gray-600'
                  : 'bg-red-100 text-red-700'
              }`}
            >
              {outbound.status}
            </span>
          </div>

          <div className="rounded-lg border border-gray-200 overflow-hidden">
            <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 text-sm">
              <span className="font-medium text-gray-700">Subject: </span>
              <span className="text-gray-900">{outbound.subject || '(no subject)'}</span>
            </div>
            <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 text-xs text-gray-500">
              Template: {outbound.template_name || '—'}
              {outbound.routed_template &&
                outbound.routed_template !== outbound.template_name && (
                  <span className="ml-2 text-blue-600">
                    (routed: {outbound.routed_template})
                  </span>
                )}
            </div>
            {outbound.body_html ? (
              <iframe
                srcDoc={outbound.body_html}
                sandbox=""
                className="w-full h-80 border-0"
                title="Email preview"
              />
            ) : (
              <div className="p-4 text-sm text-gray-400">No body.</div>
            )}
          </div>

          {outbound.status === 'pending' && (
            <div className="flex gap-3">
              <button
                onClick={handleSend}
                disabled={sending}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium
                           hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {sending ? 'Sending…' : 'Send'}
              </button>
              <button
                onClick={handleSkip}
                disabled={sending}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm font-medium
                           hover:bg-gray-300 disabled:opacity-50 transition-colors"
              >
                Skip
              </button>
            </div>
          )}

          {outbound.error_message && (
            <div className="text-sm text-red-600 bg-red-50 rounded p-3">
              Error: {outbound.error_message}
            </div>
          )}
        </div>
      ) : (
        <div className="text-sm text-gray-400">No outbound email queued.</div>
      )}
    </div>
  )
}

export default InboxDetail
