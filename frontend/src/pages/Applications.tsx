import { useState } from 'react'
import { api, ApiError, type Application, type Stage } from '../api'
import { Chip, Empty, Field, Modal, PageHeader, Score, Status } from '../components/ui'
import { formatDate, relativeDue, STAGES, stageLabel } from '../format'
import { useApi } from '../hooks'

const BOARD: Stage[] = ['saved', 'applied', 'recruiter_screen', 'assessment', 'technical', 'final', 'offer']
const CLOSED: Stage[] = ['rejected', 'withdrawn']

export default function Applications() {
  const { data: apps, error, loading, reload } = useApi(() => api.applications.list())
  const [adding, setAdding] = useState(false)
  const [openId, setOpenId] = useState<number | null>(null)
  const [showClosed, setShowClosed] = useState(false)

  const move = async (app: Application, stage: Stage) => {
    await api.applications.update(app.id, { stage })
    reload()
  }
  const open = apps?.find((a) => a.id === openId) ?? null
  const closed = apps?.filter((a) => CLOSED.includes(a.stage)) ?? []

  return (
    <>
      <PageHeader
        title="Applications"
        subtitle="Move cards through the pipeline — follow-up dates are set for you at every stage."
        actions={
          <button className="btn primary" onClick={() => setAdding(true)}>
            + Add application
          </button>
        }
      />
      <Status loading={loading && !apps} error={error} />
      {apps && apps.length === 0 && <Empty>No applications yet. Track a job from Jobs or Matching, or add one here.</Empty>}
      {apps && apps.length > 0 && (
        <>
          <div className="board">
            {BOARD.map((stage) => {
              const items = apps.filter((a) => a.stage === stage)
              return (
                <div className="column" key={stage}>
                  <div className="column-head">
                    <span>{stageLabel(stage)}</span>
                    <span>{items.length}</span>
                  </div>
                  {items.map((a) => (
                    <AppCard key={a.id} app={a} onOpen={() => setOpenId(a.id)} onMove={(s) => move(a, s)} />
                  ))}
                </div>
              )
            })}
          </div>
          {closed.length > 0 && (
            <div className="section">
              <button className="btn ghost" onClick={() => setShowClosed(!showClosed)}>
                {showClosed ? '▾' : '▸'} Closed ({closed.length})
              </button>
              {showClosed && (
                <div className="board" style={{ marginTop: 8 }}>
                  <div className="column">
                    {closed.map((a) => (
                      <AppCard key={a.id} app={a} onOpen={() => setOpenId(a.id)} onMove={(s) => move(a, s)} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
      {adding && (
        <AddApplication
          onClose={() => setAdding(false)}
          onSaved={() => {
            setAdding(false)
            reload()
          }}
        />
      )}
      {open && <ApplicationDetail app={open} onClose={() => setOpenId(null)} onChanged={reload} />}
    </>
  )
}

function AppCard({ app, onOpen, onMove }: { app: Application; onOpen: () => void; onMove: (s: Stage) => void }) {
  const due = relativeDue(app.next_follow_up)
  return (
    <div className="app-card" onClick={onOpen}>
      <div className="title">{app.job.title}</div>
      <div className="sub">
        {app.job.company}
        {app.referral && ' · referral'}
      </div>
      <div className="meta">
        {app.next_follow_up ? <span className={`tone-${due.tone}`}>Follow up {due.text.toLowerCase()}</span> : <span className="tone-muted">{app.applied_on ? `Applied ${formatDate(app.applied_on)}` : 'Not applied yet'}</span>}
        <select
          value={app.stage}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => onMove(e.target.value as Stage)}
          aria-label="Stage"
          style={{ padding: '2px 4px', fontSize: 12, maxWidth: 118 }}
        >
          {STAGES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}

function AddApplication({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ title: '', company: '', location: '', url: '', stage: 'applied' as Stage, referral: false, notes: '' })
  const [err, setErr] = useState<string | null>(null)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const { stage, referral, notes, ...job } = form
      await api.applications.create({ job, stage, referral, notes })
      onSaved()
    } catch (ex) {
      setErr(ex instanceof ApiError ? ex.message : String(ex))
    }
  }
  return (
    <Modal title="Add application" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <Field label="Role *">
          <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </Field>
        <Field label="Company *">
          <input required value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
        </Field>
        <Field label="Location">
          <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
        </Field>
        <Field label="Stage">
          <select value={form.stage} onChange={(e) => setForm({ ...form, stage: e.target.value as Stage })}>
            {STAGES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Link" full>
          <input type="url" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
        </Field>
        <Field label="Notes" full>
          <textarea rows={3} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </Field>
        <label className="field checkbox full">
          <input type="checkbox" checked={form.referral} onChange={(e) => setForm({ ...form, referral: e.target.checked })} />
          Applied through a referral
        </label>
        {err && <div className="alert full">{err}</div>}
        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary">Save</button>
        </div>
      </form>
    </Modal>
  )
}

function ApplicationDetail({ app, onClose, onChanged }: { app: Application; onClose: () => void; onChanged: () => void }) {
  const [notes, setNotes] = useState(app.notes)
  const [followUp, setFollowUp] = useState(app.next_follow_up ?? '')
  const save = async () => {
    await api.applications.update(app.id, { notes, next_follow_up: followUp || null })
    onChanged()
    onClose()
  }
  const remove = async () => {
    if (!confirm('Stop tracking this application? The job stays in your Jobs list.')) return
    await api.applications.remove(app.id)
    onChanged()
    onClose()
  }
  return (
    <Modal title={app.job.title} onClose={onClose}>
      <p className="muted" style={{ marginTop: -6 }}>
        {app.job.company} · {app.job.location || '—'} {app.job.url && <a href={app.job.url} target="_blank" rel="noreferrer">posting ↗</a>}
      </p>
      <div className="list-item">
        <Score value={app.job.match_score} />
        <Chip tone="accent">{stageLabel(app.stage)}</Chip>
        <span className="small muted">Applied {formatDate(app.applied_on)}</span>
      </div>
      <div className="form" style={{ marginTop: 10 }}>
        <Field label="Next follow-up">
          <input type="date" value={followUp} onChange={(e) => setFollowUp(e.target.value)} />
        </Field>
        <div />
        <Field label="Notes (interviewers, questions asked, salary discussed…)" full>
          <textarea rows={5} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </Field>
      </div>
      <h3 style={{ margin: '14px 0 6px' }}>Timeline</h3>
      <ul className="timeline">
        {app.events.map((e, i) => (
          <li key={i}>
            <b>{stageLabel(e.to_stage)}</b> <span className="muted small">{new Date(e.at).toLocaleDateString()}</span>
          </li>
        ))}
      </ul>
      <div className="form-actions" style={{ marginTop: 14 }}>
        <button className="btn danger" onClick={remove}>
          Remove
        </button>
        <button className="btn primary" onClick={save}>
          Save
        </button>
      </div>
    </Modal>
  )
}
