import { useState, useEffect } from 'react'
import { getContact, sendContact, skipContact, deleteContact, fixContact } from '../api/client'
import type { ContactDetail } from '../api/client'

interface Props {
  id: string
  onAction: () => void
  onDelete?: () => void
}

export function InboxDetail({ id, onAction, onDelete }: Props) {
  const [detail, setDetail] = useState<ContactDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editEmail, setEditEmail] = useState('')
  const [editAddress, setEditAddress] = useState('')
  const [fixing, setFixing] = useState(false)

  useEffect(() => {
    setLoading(true)
    setDetail(null)
    setError(null)
    getContact(id)
      .then((d) => {
        setDetail(d)
        setEditName(d.contact.name ?? '')
        setEditEmail(d.contact.email_primary ?? '')
        setEditAddress(d.contact.address ?? '')
      })
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

  async function handleFix() {
    setFixing(true)
    setError(null)
    try {
      await fixContact(id, { name: editName, email: editEmail, address: editAddress })
      onAction()
      const fresh = await getContact(id)
      setDetail(fresh)
    } catch (e) {
      setError(String(e))
    } finally {
      setFixing(false)
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

  async function handleDelete() {
    if (!window.confirm('Delete this contact? This cannot be undone.')) return
    await deleteContact(id)
    onDelete?.()
  }

  const { contact, outbound_emails } = detail
  const outbound = outbound_emails[0] ?? null
  const isUnparsed = contact.parse_status === 'unparsed'

  const fieldCls = "w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <div className="flex items-start justify-between">
        <h2 className="text-xl font-semibold text-gray-900">{contact.name || '(no name)'}</h2>
        <button
          onClick={() => void handleDelete()}
          className="text-xs text-gray-400 hover:text-red-600 transition-colors px-2 py-1 rounded"
          aria-label="Delete contact"
        >
          Delete
        </button>
      </div>

      {isUnparsed && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
          <strong>Could not parse this email.</strong> Fill in the fields below and click <strong>Save &amp; Route</strong> to process it.
        </div>
      )}

      {isUnparsed && contact.raw_body && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Raw email body</p>
          <pre className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-xs text-gray-700 whitespace-pre-wrap max-h-40 overflow-y-auto">
            {contact.raw_body}
          </pre>
        </div>
      )}

      <div className="space-y-3">
        <div className="grid grid-cols-[120px_1fr] items-center gap-x-4 gap-y-2 text-sm">
          <label className="text-gray-500">Name</label>
          <input className={fieldCls} value={editName} onChange={(e) => setEditName(e.target.value)} />
          <label className="text-gray-500">Email</label>
          <input className={fieldCls} value={editEmail} onChange={(e) => setEditEmail(e.target.value)} />
          <label className="text-gray-500">Address</label>
          <input className={fieldCls} value={editAddress} onChange={(e) => setEditAddress(e.target.value)} />
          <label className="text-gray-500">Distance</label>
          <span className="text-gray-900">
            {contact.distance_miles != null ? `${contact.distance_miles.toFixed(1)} mi` : '—'}
          </span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => void handleFix()}
            disabled={fixing || !editName || !editEmail || !editAddress}
            className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium
                       hover:bg-blue-700 disabled:opacity-40 transition-colors"
          >
            {fixing ? 'Saving…' : 'Save & Route'}
          </button>
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
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
                sandbox="allow-same-origin"
                onLoad={(e) => {
                  const el = e.currentTarget
                  const h = el.contentDocument?.body?.scrollHeight
                  if (h) el.style.height = h + 32 + 'px'
                }}
                className="w-full border-0 min-h-[480px]"
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
