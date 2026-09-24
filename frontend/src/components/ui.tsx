import { useEffect, type ReactNode } from 'react'
import { scoreTone } from '../format'

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {actions && <div className="actions">{actions}</div>}
    </header>
  )
}

export function Card({ title, actions, children, className = '' }: {
  title?: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-head">
          {title && <h2>{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </section>
  )
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="card stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  )
}

export function Bar({ value, max = 100, label }: { value: number; max?: number; label?: string }) {
  const width = max ? Math.min(100, (value / max) * 100) : 0
  return (
    <div className="bar" role="progressbar" aria-valuenow={value} aria-valuemax={max} aria-label={label}>
      <i style={{ width: `${width}%` }} />
    </div>
  )
}

export function Score({ value }: { value: number | null }) {
  return <span className={`score ${scoreTone(value)}`}>{value === null ? '—' : Math.round(value)}</span>
}

export function Chip({ children, tone = 'default' }: { children: ReactNode; tone?: 'default' | 'good' | 'danger' | 'warn' | 'accent' }) {
  return <span className={`chip ${tone}`}>{children}</span>
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>
}

export function Status({ loading, error }: { loading: boolean; error: string | null }) {
  if (error) return <div className="alert">Could not reach the API: {error}. Is the backend running on :8000?</div>
  if (loading) return <div className="empty">Loading…</div>
  return null
}

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title}>
        <div className="card-head">
          <h2>{title}</h2>
          <button className="btn ghost" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function Field({ label, children, full }: { label: string; children: ReactNode; full?: boolean }) {
  return (
    <label className={`field ${full ? 'full' : ''}`}>
      <span>{label}</span>
      {children}
    </label>
  )
}

const QUALITY_LABELS = ['Blank', 'Wrong', 'Hard', 'OK', 'Good', 'Easy']

/** Self-rating buttons for spaced repetition. 0–2 = needs review tomorrow. */
export function QualityButtons({ onRate, disabled }: { onRate: (q: number) => void; disabled?: boolean }) {
  return (
    <div className="quality" role="group" aria-label="How well did you do?">
      {[1, 3, 4, 5].map((q) => (
        <button key={q} className={`btn small q${q}`} disabled={disabled} onClick={() => onRate(q)}>
          {QUALITY_LABELS[q]}
        </button>
      ))}
    </div>
  )
}
