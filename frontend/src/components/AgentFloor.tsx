import { AGENTS, AGENT_BY_NAME, describe, isAgent } from '../agents'
import type { AgentName, AuditEvent } from '../types'
import Labubu, { type Mood } from './Labubu'

interface Props {
  events: AuditEvent[]   // events of the run being shown
  running: boolean
}

interface AgentState {
  mood: Mood
  bubble: string | null
  icon: string
  tools: number
}

/** Work out what every agent is doing from the run's audit events. */
function floorState(events: AuditEvent[], running: boolean) {
  const state = Object.fromEntries(AGENTS.map(a => [a.name, {
    mood: events.length ? 'away' : 'idle', bubble: null, icon: '', tools: 0,
  } as AgentState])) as Record<AgentName, AgentState>
  const active: Record<string, number> = {}
  const openLinks = new Map<string, number>()
  const usedLinks = new Set<string>()

  for (const e of events) {
    if (!isAgent(e.agent)) continue
    const s = state[e.agent]
    const line = describe(e)
    if (e.event === 'agent_start') active[e.agent] = (active[e.agent] ?? 0) + 1
    if (e.event === 'agent_done' || e.event === 'agent_error' || e.event === 'limit_hit') active[e.agent] = Math.max(0, (active[e.agent] ?? 1) - 1)
    if (e.event === 'tool_call') s.tools += 1
    if (e.event === 'delegate' || e.event === 'delegate_result') {
      const [from, to] = e.detail.split('->').map(x => x.trim())
      const key = e.event === 'delegate' ? `${from}>${to}` : `${to}>${from}`
      usedLinks.add(key)
      openLinks.set(key, (openLinks.get(key) ?? 0) + (e.event === 'delegate' ? 1 : -1))
    }
    if (['model_response', 'tool_call', 'tool_result', 'delegate', 'agent_start', 'agent_done', 'delegate_result'].includes(e.event)) {
      s.bubble = line.text
      s.icon = line.icon
    }
    s.mood = e.event === 'agent_done' ? 'done' : e.event === 'model_response' && e.data?.text ? 'talking' : 'working'
  }
  for (const a of AGENTS) {
    const s = state[a.name]
    if (s.mood === 'away' || !events.length) continue
    if (!running || !active[a.name]) s.mood = 'done'
  }
  const links = [...usedLinks].map(k => {
    const [from, to] = k.split('>') as [AgentName, AgentName]
    return { from, to, live: running && (openLinks.get(k) ?? 0) > 0 }
  })
  return { state, links }
}

export default function AgentFloor({ events, running }: Props) {
  const { state, links } = floorState(events, running)
  const anyone = events.length > 0
  return (
    <section className="panel floor">
      <header className="panel-head">
        <h2>The floor</h2>
        <span className={`live-dot ${running ? 'on' : ''}`}>{running ? 'LIVE' : anyone ? 'last run' : 'quiet'}</span>
      </header>
      <div className="floor-stage">
        <svg className="floor-links" viewBox="0 0 100 100" preserveAspectRatio="none">
          {links.map(l => {
            const a = AGENT_BY_NAME[l.from].seat, b = AGENT_BY_NAME[l.to].seat
            return <line key={`${l.from}-${l.to}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
              className={l.live ? 'link live' : 'link'} vectorEffect="non-scaling-stroke" />
          })}
        </svg>
        <div className="rug" />
        {AGENTS.map(a => {
          const s = state[a.name]
          return (
            <div key={a.name} className={`seat mood-${s.mood} ${a.name === 'boss' ? 'boss-seat' : ''}`}
              style={{ left: `${a.seat.x}%`, top: `${a.seat.y}%`, ['--agent' as string]: a.color }}>
              {s.bubble && s.mood !== 'away' && (
                <div className={`bubble ${a.seat.y > 50 ? 'above' : 'below'}`}>
                  <span>{s.icon}</span> {s.bubble}
                </div>
              )}
              <Labubu color={a.color} accessory={a.accessory} mood={s.mood} size={a.name === 'boss' ? 96 : 78} />
              <div className="nameplate">
                <b>{a.title}</b>
                <small>{s.mood === 'away' ? (anyone ? 'sat this one out' : a.role) : `${s.tools} tool call${s.tools === 1 ? '' : 's'}`}</small>
              </div>
            </div>
          )
        })}
        {!anyone && <p className="floor-empty">Pick a ticket and press <b>Start the team</b>. The Labubus will get to work.</p>}
      </div>
    </section>
  )
}
