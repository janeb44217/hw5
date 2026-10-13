export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: string
  notes: string | null
  created_at: string
  is_open: boolean
  is_resolved: boolean
}

export interface TicketList {
  shop_today: string
  tickets: Ticket[]
}

export interface Draft {
  id: number
  recipient: string
  subject: string
  body: string
  author: string
  status: string
}

export interface LogLine {
  author: string
  status: string | null
  note: string
  created_at: string
}

export interface TicketDetail {
  shop_today: string
  ticket: Ticket
  log: LogLine[]
  drafts: Draft[]
  approval_requests: { id: number; kind: string; amount: number; payee: string; status: string }[]
}

export interface AuditEvent {
  index: number
  ts: string
  run_id: string
  ticket_id: number | null
  agent: string
  depth: number
  event: string
  detail: string
  data: any
  model: string | null
}

export interface EventsResponse {
  total: number
  last_index: number
  running: boolean
  events: AuditEvent[]
}

export interface TicketDecision {
  ticket_id: number
  final_status: string
  decision: string
  facts_used: string[]
  pending_approval_ids: number[]
  draft_ids: number[]
  blocked_by: string[]
  next_step_for_human: string
  delegation_chain?: string[]
}

export interface RunInfo {
  run_id: string
  ticket_id: number
  status: 'queued' | 'running' | 'done' | 'error'
  model: string
  started_at: string
  finished_at?: string
  decision?: TicketDecision | null
  error?: string
}

export interface ApprovalRequest {
  id: number
  kind: 'invoice' | 'rent' | 'purchase_order'
  ref_id: number | null
  ticket_id: number | null
  vendor_id: number | null
  sku: string | null
  size: string | null
  qty: number | null
  amount: number
  payee: string
  account: string
  reason: string
  requested_by: string
  status: 'pending' | 'paid' | 'rejected'
  decided_by: string | null
  decided_at: string | null
  expected_arrival: string | null
  created_at: string
}

export interface Cash {
  account: string
  balance: number
  as_of: string
  shop_today: string
  pending_total: number
  cash_after_pending: number
}
