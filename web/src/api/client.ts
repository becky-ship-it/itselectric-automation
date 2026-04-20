export interface PipelineStatus {
  status: 'idle' | 'running'
  last_run_at: string | null
  run_id: string | null
}

export async function getPipelineStatus(): Promise<PipelineStatus> {
  return { status: 'idle', last_run_at: null, run_id: null }
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

export async function runPipeline(_opts?: { fixture?: boolean }): Promise<{ run_id: string }> {
  return { run_id: '' }
}

export async function listContacts(_opts?: { status?: string }): Promise<Contact[]> {
  return []
}

export async function getContact(_id: string): Promise<ContactDetail> {
  return { contact: {} as Contact, outbound_emails: [] }
}

export async function sendContact(
  _id: string,
  _opts?: { templateOverride?: string }
): Promise<{ ok: boolean; status: string }> {
  return { ok: false, status: '' }
}

export async function skipContact(_id: string): Promise<{ ok: boolean }> {
  return { ok: false }
}
