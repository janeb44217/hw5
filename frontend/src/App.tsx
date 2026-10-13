import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import { API_URL, api } from './api'
import { money } from './agents'
import type { ApprovalRequest, AuditEvent, Cash, RunInfo, Ticket, TicketDecision, TicketDetail } from './types'
import ActivityFeed from './components/ActivityFeed'
import AgentFloor from './components/AgentFloor'
import AgentSummary from './components/AgentSummary'
import ApprovalInbox from './components/ApprovalInbox'
import CashRegister from './components/CashRegister'
import Labubu from './components/Labubu'
import TicketBoard from './components/TicketBoard'

interface Toast { id: number; text: string; tone: 'good' | 'bad' | 'info'; ticketId?: number }

const fmtShopDate = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [shopToday, setShopToday] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detail, setDetail] = useState<TicketDetail | null>(null)
  const [cash, setCash] = useState<Cash | null>(null)
  const [pending, setPending] = useState<ApprovalRequest[]>([])
  const [paid, setPaid] = useState<ApprovalRequest[]>([])
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [run, setRun] = useState<RunInfo | null>(null)
  const [offline, setOffline] = useState(false)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [approver, setApproverState] = useState(() => localStorage.getItem('cc-approver') ?? '')
  const lastIndex = useRef(-1)

  const running = run?.status === 'queued' || run?.status === 'running'

  const toast = useCallback((text: string, tone: Toast['tone'] = 'info', ticketId?: number) => {
    const id = Date.now() + Math.random()
    setToasts(t => [...t, { id, text, tone, ticketId }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 7000)
  }, [])

  const setApprover = (name: string) => {
    setApproverState(name)
    localStorage.setItem('cc-approver', name)
  }

  // ---------------------------------------------------------------- loaders
  const loadBoard = useCallback(async () => {
    try {
      const [t, c, p, d] = await Promise.all([api.tickets(), api.cash(), api.approvals('pending'), api.approvals('paid')])
      setTickets(t.tickets)
      setShopToday(t.shop_today)
      setCash(c)
      setPending(p.requests)
      setPaid(d.requests)
      setSelectedId(id => id ?? t.tickets[0]?.id ?? null)
      setOffline(false)
    } catch {
      setOffline(true)
    }
  }, [])

  const loadEvents = useCallback(async () => {
    try {
      const r = await api.events(lastIndex.current, 1000)
      if (r.events.length) {
        lastIndex.current = r.last_index
        setEvents(ev => [...ev, ...r.events])
      } else if (r.last_index < lastIndex.current) {
        lastIndex.current = -1   // trail was replaced; start over
        setEvents([])
      }
    } catch { /* offline banner comes from loadBoard */ }
  }, [])

  const loadDetail = useCallback(async (id: number | null) => {
    if (id == null) return setDetail(null)
    try { setDetail(await api.ticket(id)) } catch { setDetail(null) }
  }, [])

  useEffect(() => { loadBoard(); loadEvents() }, [loadBoard, loadEvents])
  useEffect(() => { loadDetail(selectedId) }, [selectedId, loadDetail])

  // Poll fast while the team works, slowly otherwise.
  useEffect(() => {
    const t = setInterval(() => {
      loadEvents()
      if (running) loadDetail(selectedId)
    }, running ? 1200 : 5000)
    return () => clearInterval(t)
  }, [running, loadEvents, loadDetail, selectedId])

  useEffect(() => {
    if (!running) return
    const t = setInterval(loadBoard, 4000)
    return () => clearInterval(t)
  }, [running, loadBoard])

  // Watch the run until the Boss is done.
  useEffect(() => {
    if (!run || !running) return
    const t = setInterval(async () => {
      try {
        const r = await api.run(run.run_id)
        if (r.status === 'done' || r.status === 'error') {
          setRun(r)
          await Promise.all([loadBoard(), loadEvents(), loadDetail(r.ticket_id)])
          if (r.status === 'done') {
            const s = r.decision?.final_status ?? 'done'
            toast(`Ticket #${r.ticket_id}: the Boss marked it ${s.replace('_', ' ')}.`, s === 'resolved' ? 'good' : 'info')
          } else toast(`Run failed: ${r.error}`, 'bad')
        }
      } catch { /* keep polling */ }
    }, 1500)
    return () => clearInterval(t)
  }, [run, running, loadBoard, loadEvents, loadDetail, toast])

  // ---------------------------------------------------------------- actions
  const startTeam = async (ticketId: number) => {
    try {
      setSelectedId(ticketId)
      const r = await api.runTicket(ticketId)
      setRun(r)
      toast(`The team picked up ticket #${ticketId}.`)
    } catch (e) {
      toast(String((e as Error).message), 'bad')
    }
  }

  const approve = async (r: ApprovalRequest) => {
    try {
      const res = await api.approve(r.id, approver.trim()) as { new_balance: number }
      toast(`Paid ${money(r.amount)} to ${r.payee}. Checking is now ${money(res.new_balance)}.`, 'good', r.ticket_id ?? undefined)
    } catch (e) {
      toast(`Refused: ${(e as Error).message}`, 'bad')
    }
    await Promise.all([loadBoard(), loadEvents(), loadDetail(selectedId)])
  }

  const reject = async (r: ApprovalRequest) => {
    const note = window.prompt(`Why reject request #${r.id}? (optional)`) ?? ''
    try {
      await api.reject(r.id, approver.trim(), note)
      toast(`Rejected request #${r.id}. No money moved.`, 'info', r.ticket_id ?? undefined)
    } catch (e) {
      toast(`Couldn't reject: ${(e as Error).message}`, 'bad')
    }
    await Promise.all([loadBoard(), loadDetail(selectedId)])
  }

  const reset = async () => {
    if (!window.confirm('Reset the shop database to the original values? Agent history in the audit trail is kept.')) return
    try {
      await api.reset()
      setRun(null)
      toast('Fresh start: database reset to the original.', 'good')
      await Promise.all([loadBoard(), loadEvents(), loadDetail(selectedId)])
    } catch (e) {
      toast(String((e as Error).message), 'bad')
    }
  }

  // ---------------------------------------------------------------- derived
  const selected = tickets.find(t => t.id === selectedId) ?? null

  // Show the live run if it is on this ticket, else the latest finished run on it.
  const shownRunId = useMemo(() => {
    if (run && run.ticket_id === selectedId && (running || run.status === 'done')) return run.run_id
    // Only runs since the last database reset belong to the current shop state.
    const lastReset = events.reduce((i, e) => (e.event === 'database_reset' ? e.index : i), -1)
    const starts = events.filter(e => e.event === 'ticket_start' && e.ticket_id === selectedId && e.index > lastReset)
    return starts.length ? starts[starts.length - 1].run_id : null
  }, [run, running, selectedId, events])

  const runEvents = useMemo(
    () => (shownRunId ? events.filter(e => e.run_id === shownRunId && e.ticket_id === selectedId) : []),
    [events, shownRunId, selectedId],
  )

  const decision = useMemo<TicketDecision | null>(() => {
    const done = runEvents.filter(e => e.event === 'ticket_done')
    return done.length ? (done[done.length - 1].data as TicketDecision) : null
  }, [runEvents])

  const showingLive = running && run?.ticket_id === selectedId
  const ticketPending = pending.filter(p => p.ticket_id === selectedId)

  return (
    <div className="desk">
      <header className="topbar">
        <div className="brand">
          <Labubu color="#ff2e93" accessory="crown" mood={running ? 'working' : 'idle'} size={52} />
          <div>
            <h1>Campus Customs <span>Agent Desk</span></h1>
            <p>{shopToday ? `Shop date ${fmtShopDate(shopToday)}` : 'connecting…'} · gpt-6-luna team · humans sign for money</p>
          </div>
        </div>
        <div className="topbar-right">
          {running && <span className="working-pill">🛠️ team on #{run?.ticket_id}</span>}
          <button className="btn ghost small" onClick={reset} disabled={running}>↺ Reset shop</button>
        </div>
      </header>

      {offline && (
        <div className="offline">
          Can't reach the backend at <code>{API_URL}</code>. Start it from <code>backend/</code> with <code>uvicorn main:app --reload --port 8000</code>.
        </div>
      )}

      <main className="layout">
        <aside className="col-left">
          <TicketBoard tickets={tickets} selectedId={selectedId} runningTicketId={running ? run?.ticket_id ?? null : null}
            onSelect={setSelectedId} />
          {selected && (
            <section className="panel ticket-detail">
              <header className="panel-head"><h2>#{selected.id} up close</h2></header>
              <p className="quote">“{selected.notes}”</p>
              <p className="muted small">from {selected.requester} · {selected.created_at.slice(0, 16).replace('T', ' ')}</p>
              <button className="btn primary big" disabled={running || offline} onClick={() => startTeam(selected.id)}>
                {running ? (run?.ticket_id === selected.id ? 'Team is on it…' : `Busy with #${run?.ticket_id}`)
                  : selected.is_resolved ? 'Run the team again' : decision ? 'Hand back to the team' : 'Start the team'}
              </button>
              {ticketPending.length > 0 && !running && (
                <p className="hint">⏳ {ticketPending.length} request{ticketPending.length > 1 ? 's' : ''} on this ticket wait{ticketPending.length > 1 ? '' : 's'} for your signature. Approve, then hand it back to the team.</p>
              )}
              {detail && detail.log.length > 0 && (
                <details className="log">
                  <summary>Ticket log ({detail.log.length})</summary>
                  {detail.log.map((l, i) => (
                    <p key={i}><b>{l.author}</b>{l.status && <> → <i>{l.status}</i></>}: {l.note}</p>
                  ))}
                </details>
              )}
            </section>
          )}
        </aside>

        <section className="col-center">
          <AgentFloor events={runEvents} running={showingLive} />
          <div className="center-split">
            <ActivityFeed events={runEvents} />
            <AgentSummary events={showingLive ? [] : runEvents} decision={showingLive ? null : decision} detail={detail} />
          </div>
        </section>

        <aside className="col-right">
          <CashRegister cash={cash} paid={paid} />
          <ApprovalInbox requests={pending} cash={cash} approver={approver} setApprover={setApprover}
            onApprove={approve} onReject={reject} />
        </aside>
      </main>

      <div className="toasts">
        {toasts.map(t => (
          <div key={t.id} className={`toast ${t.tone}`}>
            <span>{t.text}</span>
            {t.ticketId && !running && (
              <button className="btn small" onClick={() => { startTeam(t.ticketId!); setToasts(x => x.filter(y => y.id !== t.id)) }}>
                Hand #{t.ticketId} back to the team
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
