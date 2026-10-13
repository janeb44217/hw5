import { useState } from 'react'
import { AGENT_BY_NAME, isAgent, money } from '../agents'
import type { ApprovalRequest, Cash } from '../types'

interface Props {
  requests: ApprovalRequest[]
  cash: Cash | null
  approver: string
  setApprover: (name: string) => void
  onApprove: (r: ApprovalRequest) => Promise<void>
  onReject: (r: ApprovalRequest) => Promise<void>
}

const KIND: Record<string, { icon: string; label: string }> = {
  invoice: { icon: '🧾', label: 'Pay invoice' },
  rent: { icon: '🏠', label: 'Pay rent' },
  purchase_order: { icon: '📦', label: 'Place purchase order' },
}

export default function ApprovalInbox({ requests, cash, approver, setApprover, onApprove, onReject }: Props) {
  const [busy, setBusy] = useState<number | null>(null)
  const act = async (id: number, fn: () => Promise<void>) => {
    setBusy(id)
    try { await fn() } finally { setBusy(null) }
  }
  return (
    <section className={`panel inbox ${requests.length ? 'has-items' : ''}`}>
      <header className="panel-head">
        <h2>Needs your signature</h2>
        {requests.length > 0 && <span className="badge">{requests.length}</span>}
      </header>
      <label className="approver">
        Signing as
        <input value={approver} onChange={e => setApprover(e.target.value)} placeholder="your name" />
      </label>
      {requests.length === 0 && <p className="muted">No payments waiting. Agents can only <i>prepare</i> payments; only you can move money.</p>}
      {requests.map(r => {
        const k = KIND[r.kind] ?? { icon: '💸', label: r.kind }
        const tooMuch = cash != null && r.amount > cash.balance
        const who = isAgent(r.requested_by) ? AGENT_BY_NAME[r.requested_by] : null
        return (
          <article key={r.id} className="approval">
            <div className="approval-top">
              <span className="approval-icon">{k.icon}</span>
              <div>
                <b>{k.label}</b>
                <small>request #{r.id}{r.ticket_id ? ` · ticket #${r.ticket_id}` : ''} · prepared by <span style={{ color: who?.color }}>{who?.title ?? r.requested_by}</span></small>
              </div>
              <span className="approval-amount">{money(r.amount)}</span>
            </div>
            <p className="approval-payee">to <b>{r.payee}</b>
              {r.kind === 'purchase_order' && <> · {r.qty}× {r.sku} size {r.size}{r.expected_arrival && <> · arrives ~{r.expected_arrival}</>}</>}
            </p>
            <p className="approval-reason">{r.reason}</p>
            {tooMuch && <p className="warn">Not enough cash. The backend will refuse this.</p>}
            <div className="approval-actions">
              <button className="btn approve" disabled={!approver.trim() || busy === r.id}
                onClick={() => act(r.id, () => onApprove(r))}>
                {busy === r.id ? 'Paying…' : `Approve & pay ${money(r.amount)}`}
              </button>
              <button className="btn ghost" disabled={!approver.trim() || busy === r.id}
                onClick={() => act(r.id, () => onReject(r))}>Reject</button>
            </div>
          </article>
        )
      })}
    </section>
  )
}
