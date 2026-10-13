import type { Ticket } from '../types'

const TYPE_ICON: Record<string, string> = {
  customer_order: '👕', rent_notice: '🏠', price_override: '🏷️', unpaid_bill: '🧾',
}

const STATUS_LABEL: Record<string, string> = {
  open: 'Open', in_progress: 'In progress', waiting_approval: 'Needs you', resolved: 'Resolved', declined: 'Declined',
}

interface Props {
  tickets: Ticket[]
  selectedId: number | null
  runningTicketId: number | null
  onSelect: (id: number) => void
}

export default function TicketBoard({ tickets, selectedId, runningTicketId, onSelect }: Props) {
  const done = tickets.filter(t => t.is_resolved).length
  return (
    <section className="panel board">
      <header className="panel-head">
        <h2>Ticket board</h2>
        <span className="count">{done}/{tickets.length} resolved</span>
      </header>
      <div className="progress"><div style={{ width: `${tickets.length ? (done / tickets.length) * 100 : 0}%` }} /></div>
      <ul className="ticket-list">
        {tickets.map(t => (
          <li key={t.id}>
            <button
              className={`ticket-card status-${t.status} ${selectedId === t.id ? 'selected' : ''} ${runningTicketId === t.id ? 'running' : ''}`}
              onClick={() => onSelect(t.id)}
            >
              <span className="ticket-icon">{TYPE_ICON[t.type] ?? '📌'}</span>
              <span className="ticket-main">
                <span className="ticket-id">#{t.id} · {t.type.replace('_', ' ')}</span>
                <span className="ticket-subject">{t.subject}</span>
                <span className="ticket-from">from {t.requester}</span>
                {t.sku && <span className="ticket-chips">
                  <i>{t.sku}</i>{t.size && <i>size {t.size}</i>}{t.qty != null && <i>× {t.qty}</i>}
                </span>}
              </span>
              <span className={`status-pill pill-${t.status}`}>
                {runningTicketId === t.id ? 'Agents working…' : STATUS_LABEL[t.status] ?? t.status}
              </span>
              {t.is_resolved && <span className="stamp">RESOLVED</span>}
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
