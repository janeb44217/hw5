import { useEffect, useRef } from 'react'
import { AGENT_BY_NAME, describe, isAgent } from '../agents'
import type { AuditEvent } from '../types'

const SHOWN = new Set([
  'ticket_start', 'agent_start', 'model_response', 'tool_call', 'tool_result', 'tool_blocked',
  'delegate', 'delegate_result', 'delegate_refused', 'agent_done', 'ticket_done', 'limit_hit', 'agent_error',
  'human_tool_result',
])

export default function ActivityFeed({ events }: { events: AuditEvent[] }) {
  const end = useRef<HTMLDivElement>(null)
  const shown = events.filter(e => SHOWN.has(e.event) && !(e.event === 'model_response' && !e.data?.text && !(e.data?.tool_calls?.length)))
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }) }, [shown.length])

  return (
    <section className="panel feed">
      <header className="panel-head"><h2>Desk chatter</h2><span className="count">{shown.length} events</span></header>
      <div className="feed-scroll">
        {shown.length === 0 && <p className="muted">Nothing yet. Every model step, tool call and handoff will show up here.</p>}
        {shown.map(e => {
          const line = describe(e)
          const meta = isAgent(e.agent) ? AGENT_BY_NAME[e.agent] : null
          return (
            <div key={e.index} className={`feed-line kind-${line.kind}`} style={{ ['--agent' as string]: meta?.color ?? '#888' }}
              title={e.ts}>
              <span className="feed-time">{e.ts.slice(11, 19)}</span>
              <span className="feed-who" style={{ paddingLeft: `${e.depth * 10}px` }}>{meta?.title ?? e.agent}</span>
              <span className="feed-icon">{line.icon}</span>
              <span className="feed-text">{line.text}</span>
            </div>
          )
        })}
        <div ref={end} />
      </div>
    </section>
  )
}
