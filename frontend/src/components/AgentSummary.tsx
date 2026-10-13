import { AGENTS, plain } from '../agents'
import type { AgentName, AuditEvent, TicketDecision, TicketDetail } from '../types'
import Labubu from './Labubu'

interface Props {
  events: AuditEvent[]          // events of the latest run on this ticket
  decision: TicketDecision | null
  detail: TicketDetail | null
}

interface Work {
  tools: Map<string, number>
  askedBy: Set<string>
  asked: Set<string>
  lastWords: string
}

function summarize(events: AuditEvent[]) {
  const work = new Map<AgentName, Work>()
  const get = (a: AgentName) => {
    if (!work.has(a)) work.set(a, { tools: new Map(), askedBy: new Set(), asked: new Set(), lastWords: '' })
    return work.get(a)!
  }
  for (const e of events) {
    const agent = e.agent as AgentName
    if (!AGENTS.some(a => a.name === agent)) continue
    if (e.event === 'agent_start') get(agent)
    if (e.event === 'tool_call') {
      const w = get(agent)
      w.tools.set(e.detail, (w.tools.get(e.detail) ?? 0) + 1)
    }
    if (e.event === 'delegate') {
      const to = e.detail.split('->')[1].trim() as AgentName
      get(agent).asked.add(to)
      get(to).askedBy.add(agent)
    }
    if (e.event === 'agent_done') {
      const out = e.data?.output
      get(agent).lastWords = plain(typeof out === 'string' ? out : out?.decision ?? '')
    }
  }
  return work
}

const title = (n: string) => AGENTS.find(a => a.name === n)?.title ?? n

export default function AgentSummary({ events, decision, detail }: Props) {
  const work = summarize(events)
  if (!events.length) {
    return (
      <section className="panel summary">
        <header className="panel-head"><h2>Who did what</h2></header>
        <p className="muted">Run the team on this ticket to see a summary for each agent.</p>
      </section>
    )
  }
  return (
    <section className="panel summary">
      <header className="panel-head"><h2>Who did what</h2><span className="count">latest run</span></header>

      {decision && (
        <div className={`decision status-${decision.final_status}`}>
          <div className="decision-status">{decision.final_status.replace('_', ' ')}</div>
          <p>{decision.decision}</p>
          {decision.next_step_for_human && decision.next_step_for_human.toLowerCase() !== 'nothing' && (
            <p className="next-step">👉 {decision.next_step_for_human}</p>
          )}
        </div>
      )}

      <div className="summary-grid">
        {AGENTS.map(a => {
          const w = work.get(a.name)
          return (
            <article key={a.name} className={`summary-card ${w ? '' : 'benched'}`} style={{ ['--agent' as string]: a.color }}>
              <div className="summary-head">
                <Labubu color={a.color} accessory={a.accessory} mood={w ? 'done' : 'away'} size={40} />
                <div><b>{a.title}</b><small>{w ? 'on this ticket' : 'not needed: sat this one out'}</small></div>
              </div>
              {w && <>
                {(w.askedBy.size > 0 || w.asked.size > 0) && (
                  <p className="summary-flow">
                    {w.askedBy.size > 0 && <>called by {[...w.askedBy].map(title).join(', ')}</>}
                    {w.askedBy.size > 0 && w.asked.size > 0 && ' · '}
                    {w.asked.size > 0 && <>handed off to {[...w.asked].map(title).join(', ')}</>}
                  </p>
                )}
                <div className="tool-chips">
                  {[...w.tools].map(([t, n]) => <code key={t}>{t}{n > 1 ? ` ×${n}` : ''}</code>)}
                </div>
                {w.lastWords && <p className="summary-words">{w.lastWords.length > 320 ? w.lastWords.slice(0, 319) + '…' : w.lastWords}</p>}
              </>}
            </article>
          )
        })}
      </div>

      {detail && detail.drafts.length > 0 && (
        <div className="drafts">
          <h3>✉️ Drafts on the board <small>(saved, never sent)</small></h3>
          {detail.drafts.map(d => (
            <details key={d.id} className="draft">
              <summary><b>To {d.recipient}</b>: {d.subject}</summary>
              <pre>{d.body}</pre>
            </details>
          ))}
        </div>
      )}
    </section>
  )
}
