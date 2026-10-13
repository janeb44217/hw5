import type { AgentName, AuditEvent } from './types'

export type Accessory = 'crown' | 'box' | 'glasses' | 'hardhat' | 'headset'

export interface AgentMeta {
  name: AgentName
  title: string
  nickname: string
  role: string
  color: string
  accessory: Accessory
  /** seat on the floor, in % of the floor box */
  seat: { x: number; y: number }
}

export const AGENTS: AgentMeta[] = [
  { name: 'boss', title: 'Boss', nickname: 'Bossbubu', role: 'Reads tickets, routes work, makes the call',
    color: '#ff2e93', accessory: 'crown', seat: { x: 50, y: 22 } },
  { name: 'inventory', title: 'Inventory', nickname: 'Stockbubu', role: 'Stock by SKU & size, vendors, arrivals',
    color: '#ff7ac8', accessory: 'box', seat: { x: 15, y: 70 } },
  { name: 'accounting', title: 'Accounting', nickname: 'Ledgerbubu', role: 'Cash, invoices, margins, approvals',
    color: '#ff4f6d', accessory: 'glasses', seat: { x: 38, y: 82 } },
  { name: 'facilities', title: 'Facilities', nickname: 'Leasebubu', role: 'Leases, rent, the shop space',
    color: '#c86bff', accessory: 'hardhat', seat: { x: 62, y: 82 } },
  { name: 'customer_service', title: 'Customer Service', nickname: 'Chatbubu', role: 'Drafts every message (never sends)',
    color: '#ff9ad5', accessory: 'headset', seat: { x: 85, y: 70 } },
]

export const AGENT_BY_NAME = Object.fromEntries(AGENTS.map(a => [a.name, a])) as Record<AgentName, AgentMeta>

export const isAgent = (n: string): n is AgentName => n in AGENT_BY_NAME

export const money = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

/** Agents answer in markdown; the desk shows plain text. */
export const plain = (s: string) =>
  s.replace(/\*\*|__|`/g, '').replace(/^\s*[-*•]\s+/gm, '• ').replace(/^#+\s*/gm, '')

const clip = (s: string, n = 140) => {
  const t = plain(s)
  return t.length > n ? t.slice(0, n - 1) + '…' : t
}

const fmtArgs = (args: Record<string, unknown> | undefined) =>
  Object.entries(args ?? {})
    .filter(([k]) => !['author', 'requested_by', 'note', 'reason', 'body'].includes(k))
    .map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`)
    .join(', ')

function summarizeResult(tool: string, r: any): string {
  if (r == null) return 'done'
  if (typeof r === 'string') return clip(r, 90)
  if (r.error) return `refused: ${clip(String(r.error), 90)}`
  switch (tool) {
    case 'check_stock': return `${r.on_hand} on hand, short ${r.shortfall}`
    case 'check_vendor_can_ship':
      return r.can_ship ? `${r.name} can ship · arrives ${r.arrival_if_ordered_today}`
        : `${r.name} blocked by invoice ${r.open_invoices?.map((i: any) => '#' + i.invoice_id).join(', ')}`
    case 'get_lease_due': return `${money(r.monthly_rent)} due ${r.next_due} (${r.days_until_due} days)`
    case 'get_cash_position': return `cash ${money(r.total_cash)} · after pending ${money(r.cash_after_pending)}`
    case 'request_payment':
    case 'request_purchase_order': return `request #${r.request_id} · ${money(r.amount)} · pending human`
    case 'check_margin': return `${r.discount_pct}% off → ${money(r.unit_price_after_discount)}/unit · margin ${r.margin_pct}%`
    case 'draft_message': return `draft #${r.draft_id} saved (not sent)`
    case 'set_ticket_status': return `${r.old_status} → ${r.new_status}`
    case 'get_invoice': return `invoice #${r.id} ${money(r.amount)} · ${r.overdue ? `${r.days_overdue}d overdue` : r.status}`
    default: return 'ok'
  }
}

/** One readable line for the activity feed / speech bubble. */
export function describe(e: AuditEvent): { icon: string; text: string; kind: string } {
  const d = e.data ?? {}
  switch (e.event) {
    case 'ticket_start': return { icon: '🎫', text: `Ticket #${e.ticket_id} hits the desk`, kind: 'ticket' }
    case 'agent_start': return { icon: '👋', text: `Picks up: ${clip(String(d.prompt ?? ''), 120)}`, kind: 'start' }
    case 'model_response': {
      if (d.text) return { icon: '💬', text: clip(d.text, 220), kind: 'say' }
      const calls = (d.tool_calls ?? []).map((c: any) => c.tool).filter((t: string) => t !== 'final_result')
      return { icon: '🤔', text: calls.length ? `Deciding to use ${calls.join(', ')}` : 'Writing it up…', kind: 'think' }
    }
    case 'tool_call': return { icon: '🔧', text: `${e.detail}(${clip(fmtArgs(d.args), 80)})`, kind: 'tool' }
    case 'tool_result': return { icon: '📋', text: `${e.detail} → ${summarizeResult(e.detail, d.result)}`, kind: 'result' }
    case 'tool_blocked': return { icon: '⛔', text: `${e.detail} blocked (human only)`, kind: 'error' }
    case 'delegate': {
      const to = e.detail.split('->')[1]?.trim() ?? ''
      return { icon: '📨', text: `Asks ${AGENT_BY_NAME[to as AgentName]?.title ?? to}: ${clip(String(d.request ?? ''), 160)}`, kind: 'delegate' }
    }
    case 'delegate_result': {
      const from = e.detail.split('->')[0]?.trim() ?? ''
      return { icon: '📬', text: `Hears back from ${AGENT_BY_NAME[from as AgentName]?.title ?? from}`, kind: 'reply' }
    }
    case 'delegate_refused': return { icon: '🚫', text: `Delegation refused: ${clip(String(d.reason ?? ''), 100)}`, kind: 'error' }
    case 'agent_done': {
      const out = d.output
      const text = typeof out === 'string' ? out : out?.decision ?? 'Done'
      return { icon: '✅', text: clip(String(text), 220), kind: 'done' }
    }
    case 'ticket_done': return { icon: '🏁', text: `Boss's call: ${d.final_status} · ${clip(String(d.decision ?? ''), 160)}`, kind: 'ticket' }
    case 'limit_hit': return { icon: '⏱️', text: 'Hit a usage limit and stopped', kind: 'error' }
    case 'agent_error': return { icon: '💥', text: clip(String(d.error ?? 'error'), 140), kind: 'error' }
    case 'human_tool_call': return { icon: '🧑', text: `Human: ${e.detail}(${clip(fmtArgs(d.args), 80)})`, kind: 'human' }
    case 'human_tool_result': return { icon: '🧾', text: `Human ${e.detail} → ${summarizeResult(e.detail, d.result)}`, kind: 'human' }
    case 'database_reset': return { icon: '♻️', text: 'Database reset to the original', kind: 'human' }
    default: return { icon: '•', text: e.event, kind: 'other' }
  }
}
