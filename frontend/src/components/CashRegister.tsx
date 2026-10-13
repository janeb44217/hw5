import { useEffect, useRef, useState } from 'react'
import { money } from '../agents'
import type { ApprovalRequest, Cash } from '../types'

/** Tween a number so balance changes roll like a register. */
function useRolling(target: number, ms = 1100) {
  const [shown, setShown] = useState(target)
  const from = useRef(target)
  useEffect(() => {
    const start = performance.now(), a = from.current, b = target
    let raf = 0
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / ms)
      const eased = 1 - Math.pow(1 - p, 3)
      setShown(a + (b - a) * eased)
      if (p < 1) raf = requestAnimationFrame(tick)
      else from.current = b
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])
  return shown
}

export default function CashRegister({ cash, paid }: { cash: Cash | null; paid: ApprovalRequest[] }) {
  const balance = cash?.balance ?? 0
  const rolled = useRolling(balance)
  const prev = useRef<number | null>(null)
  const [drop, setDrop] = useState<number | null>(null)

  useEffect(() => {
    if (cash == null) return
    if (prev.current != null && cash.balance < prev.current) {
      setDrop(prev.current - cash.balance)
      const t = setTimeout(() => setDrop(null), 2600)
      prev.current = cash.balance
      return () => clearTimeout(t)
    }
    prev.current = cash.balance
  }, [cash])

  const committed = cash ? Math.min(cash.pending_total, cash.balance) : 0
  const pct = (n: number) => (balance > 0 ? Math.max(0, (n / balance) * 100) : 0)

  return (
    <section className="panel register">
      <header className="panel-head"><h2>Checking</h2><span className="count">as of {cash?.as_of ?? '…'}</span></header>
      <div className={`till ${drop ? 'ka-ching' : ''}`}>
        <div className="till-amount">{money(rolled)}</div>
        {drop && <div className="till-drop">−{money(drop)}</div>}
        <div className="till-label">cash on hand · money only goes out</div>
      </div>
      {cash && (
        <>
          <div className="cash-bar" title="free vs. waiting on approval">
            <div className="free" style={{ width: `${pct(cash.balance - committed)}%` }} />
            <div className="held" style={{ width: `${pct(committed)}%` }} />
          </div>
          <div className="cash-legend">
            <span><i className="dot free" /> free after pending <b>{money(cash.cash_after_pending)}</b></span>
            <span><i className="dot held" /> waiting on you <b>{money(cash.pending_total)}</b></span>
          </div>
        </>
      )}
      {paid.length > 0 && (
        <div className="ledger">
          <h3>Receipt tape</h3>
          {paid.map(p => (
            <div key={p.id} className="ledger-line">
              <span>{p.kind === 'purchase_order' ? `PO ${p.qty}× ${p.sku} ${p.size}` : p.kind === 'rent' ? 'Rent' : `Invoice #${p.ref_id}`} → {p.payee}</span>
              <b>−{money(p.amount)}</b>
              <small>approved by {p.decided_by}</small>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
