import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, type PrepQuestion, type Track } from '../api'
import Markdown from '../components/Markdown'
import { Bar, Card, Empty, Field, Modal, PageHeader, QualityButtons, Status } from '../components/ui'
import { localToday, relativeDue, TRACK_LABELS } from '../format'
import { useApi } from '../hooks'

const TRACKS: Track[] = ['python', 'sql', 'backend', 'genai', 'system-design']
type Tab = 'for-you' | Track

export default function Prep() {
  const [params, setParams] = useSearchParams()
  const tab = (params.get('track') as Tab) || 'for-you'
  const setTab = (t: Tab) => setParams(t === 'for-you' ? {} : { track: t })

  const tracks = useApi(() => api.prep.tracks())
  const { data: questions, error, loading, reload } = useApi(
    () => (tab === 'for-you' ? api.prep.recommended(20) : api.prep.questions({ track: tab })),
    [tab],
  )
  const [mode, setMode] = useState<'practice' | 'browse'>('practice')
  const [adding, setAdding] = useState(false)

  const today = localToday()
  const queue = (questions ?? []).filter((q) => !q.next_review || q.next_review <= today)

  const refresh = () => {
    reload()
    tracks.reload()
  }

  return (
    <>
      <PageHeader
        title="Interview prep"
        subtitle="Flashcards with spaced repetition. “For you” prioritises tracks where your matched jobs show skill gaps."
        actions={
          <button className="btn primary" onClick={() => setAdding(true)}>
            + Add question
          </button>
        }
      />
      <div className="grid stats">
        {tracks.data?.map((t) => (
          <button key={t.track} className="card stat" style={{ textAlign: 'left', cursor: 'pointer', font: 'inherit', color: 'inherit' }} onClick={() => setTab(t.track)}>
            <div className="stat-label">{TRACK_LABELS[t.track]}</div>
            <div className="stat-value">{Math.round(t.mastery)}%</div>
            <Bar value={t.mastery} label={`${t.track} mastery`} />
            <div className="stat-hint">
              {t.reviewed}/{t.total} reviewed · {t.due} due
            </div>
          </button>
        ))}
      </div>

      <div className="section filters">
        <div className="tabs" style={{ margin: 0 }}>
          <button className={`tab ${tab === 'for-you' ? 'active' : ''}`} onClick={() => setTab('for-you')}>
            For you
          </button>
          {TRACKS.map((t) => (
            <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
              {TRACK_LABELS[t]}
            </button>
          ))}
        </div>
        <select value={mode} onChange={(e) => setMode(e.target.value as 'practice' | 'browse')} aria-label="Mode" style={{ marginLeft: 'auto' }}>
          <option value="practice">Practice ({queue.length} due)</option>
          <option value="browse">Browse all</option>
        </select>
      </div>

      <Status loading={loading && !questions} error={error} />
      {questions && mode === 'practice' && (
        queue.length === 0 ? (
          <Card>
            <Empty>All caught up in this track. Come back when reviews are due, or browse to read ahead.</Empty>
          </Card>
        ) : (
          <Flashcard key={queue[0].id} question={queue[0]} remaining={queue.length} onRated={refresh} />
        )
      )}
      {questions && mode === 'browse' && (
        <Card>
          {questions.map((q) => (
            <details key={q.id} className="list-item" style={{ display: 'block' }}>
              <summary style={{ cursor: 'pointer', display: 'flex', gap: 12, alignItems: 'center' }}>
                <span className="grow title" style={{ flex: 1 }}>{q.question}</span>
                <Confidence value={q.confidence} reviewed={!!q.last_reviewed} />
                <span className={`small tone-${relativeDue(q.next_review).tone}`}>{q.next_review ? relativeDue(q.next_review).text : 'new'}</span>
              </summary>
              {q.answer ? <Markdown text={q.answer} /> : <p className="muted">No model answer yet.</p>}
            </details>
          ))}
        </Card>
      )}
      {adding && (
        <AddQuestion
          defaultTrack={tab === 'for-you' ? 'python' : tab}
          onClose={() => setAdding(false)}
          onSaved={() => {
            setAdding(false)
            refresh()
          }}
        />
      )}
    </>
  )
}

function Confidence({ value, reviewed }: { value: number; reviewed: boolean }) {
  if (!reviewed) return <span className="small muted">not reviewed</span>
  return (
    <span className="dots" aria-label={`confidence ${value} of 5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span key={n} className={n <= value ? '' : 'off'}>
          ●
        </span>
      ))}
    </span>
  )
}

function Flashcard({ question, remaining, onRated }: { question: PrepQuestion; remaining: number; onRated: () => void }) {
  const [revealed, setRevealed] = useState(false)
  const [busy, setBusy] = useState(false)
  const rate = async (q: number) => {
    setBusy(true)
    await api.prep.review(question.id, q)
    onRated()
  }
  return (
    <Card className="flashcard">
      <div className="small muted">
        {TRACK_LABELS[question.track]} · {remaining} in queue
        {question.tags.length > 0 && ` · ${question.tags.join(', ')}`}
      </div>
      <div className="q">{question.question}</div>
      {!revealed && <p className="muted">Answer out loud first — as you would in the interview — then reveal.</p>}
      {revealed && (question.answer ? <Markdown text={question.answer} /> : <p className="muted">No model answer yet — edit the question to add one.</p>)}
      <div className="footer">
        {!revealed ? (
          <button className="btn primary" onClick={() => setRevealed(true)}>
            Show answer
          </button>
        ) : (
          <>
            <span className="small muted">How did you do?</span>
            <QualityButtons onRate={rate} disabled={busy} />
          </>
        )}
      </div>
    </Card>
  )
}

function AddQuestion({ defaultTrack, onClose, onSaved }: { defaultTrack: Track; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ track: defaultTrack, question: '', answer: '' })
  const [err, setErr] = useState<string | null>(null)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.prep.create(form)
      onSaved()
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex))
    }
  }
  return (
    <Modal title="Add question" onClose={onClose}>
      <p className="muted small" style={{ marginTop: -6 }}>
        Add questions you were actually asked in interviews — they're the most valuable ones to drill.
      </p>
      <form className="form" onSubmit={submit}>
        <Field label="Track">
          <select value={form.track} onChange={(e) => setForm({ ...form, track: e.target.value as Track })}>
            {TRACKS.map((t) => (
              <option key={t} value={t}>
                {TRACK_LABELS[t]}
              </option>
            ))}
          </select>
        </Field>
        <div />
        <Field label="Question *" full>
          <input required value={form.question} onChange={(e) => setForm({ ...form, question: e.target.value })} />
        </Field>
        <Field label="Model answer (Markdown: - bullets, **bold**, `code`, ``` blocks)" full>
          <textarea rows={7} value={form.answer} onChange={(e) => setForm({ ...form, answer: e.target.value })} />
        </Field>
        {err && <div className="alert full">{err}</div>}
        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary">Add</button>
        </div>
      </form>
    </Modal>
  )
}
