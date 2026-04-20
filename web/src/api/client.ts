export interface PipelineStatus {
  status: 'idle' | 'running'
  last_run_at: string | null
  run_id: string | null
}

export interface Contact {
  id: string
  received_at: string | null
  name: string | null
  address: string | null
  email_primary: string | null
  email_form: string | null
  raw_body: string | null
  parse_status: string
  nearest_charger_id: number | null
  distance_miles: number | null
  geocache_hit: boolean
  hubspot_status: string | null
}

export interface OutboundEmail {
  id: string
  contact_id: string
  template_name: string | null
  routed_template: string | null
  subject: string | null
  body_html: string | null
  sent_at: string | null
  status: string
  sent_by: string
  error_message: string | null
}

export interface ContactDetail {
  contact: Contact
  outbound_emails: OutboundEmail[]
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = init ? await fetch(url, init) : await fetch(url)
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`${resp.status} ${text}`)
  }
  return resp.json() as Promise<T>
}

export function getPipelineStatus(): Promise<PipelineStatus> {
  return request('/api/pipeline/status')
}

export function runPipeline(opts?: { fixture?: boolean }): Promise<{ run_id: string }> {
  const qs = opts?.fixture ? '?fixture=true' : ''
  return request(`/api/pipeline/run${qs}`, { method: 'POST' })
}

export function listContacts(opts?: { status?: string }): Promise<Contact[]> {
  const qs = opts?.status ? `?status=${opts.status}` : ''
  return request(`/api/contacts${qs}`)
}

export function getContact(id: string): Promise<ContactDetail> {
  return request(`/api/contacts/${id}`)
}

export function sendContact(
  id: string,
  opts?: { templateOverride?: string }
): Promise<{ ok: boolean; status: string }> {
  const qs = opts?.templateOverride ? `?template_override=${opts.templateOverride}` : ''
  return request(`/api/contacts/${id}/send${qs}`, { method: 'POST' })
}

export function skipContact(id: string): Promise<{ ok: boolean }> {
  return request(`/api/contacts/${id}/skip`, { method: 'POST' })
}
