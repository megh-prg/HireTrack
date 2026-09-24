import { useMemo, useState } from 'react'
import { api, type Difficulty, type DSAProblem, type PracticeStatus } from '../api'
import { Bar, Card, Chip, Empty, Field, Modal, PageHeader, QualityButtons, Stat, Status } from '../components/ui'
import { localToday, pct, relativeDue } from '../format'
import { useApi } from '../hooks'

const DIFF_TONE: Record<Difficulty, 'good' | 'warn' | 'danger'> = { easy: 'good', medium: 'warn', hard: 'danger' }
const STATUS_TONE: Record<PracticeStatus, 'default' | 'warn' | 'accent' | 'good'> = {
  todo: 'default',
  attempted: 'warn',
  solved: 'accent',
  mastered: 'good',
}

export default function DSA() {
  const { data: problems, error, loading, setData } = useApi(() => api.dsa.list())
  const today = localToday()
  const [topic, setTopic] = useState('')
  const [difficulty, setDifficulty] = useState('')
  const [view, setView] = useState<'all' | 'due' | 'todo'>('all')
  const [adding, setAdding] = useState(false)

  const topics = useMemo(() => [...new Set(problems?.map((p) => p.topic))].sort(), [problems])
  const filtered = (problems ?? []).filter(
    (p) =>
      (!topic || p.topic === topic) &&
      (!difficulty || p.difficulty === difficulty) &&
      (view === 'all' || (view === 'due' ? !!p.next_review && p.next_review <= today : p.status === 'todo')),
  )
  const solved = problems?.filter((p) => p.status === 'solved' || p.status === 'mastered').length ?? 0
  const due = problems?.filter((p) => p.next_review && p.next_review <= today).length ?? 0

  const practice = async (p: DSAProblem, quality: number) => {
    const updated = await api.dsa.practice(p.id, quality)
    setData((prev) => prev?.map((x) => (x.id === p.id ? updated : x)) ?? null)
  }

  return (
    <>
      <PageHeader
        title="DSA practice"
        subtitle="Solve, then rate yourself honestly. Weak problems come back tomorrow; strong ones in 1 → 3 → 7 → 14 → 30 days."
        actions={
          <button className="btn primary" onClick={() => setAdding(true)}>
            + Add problem
          </button>
        }
      />
      <Status loading={loading && !problems} error={error} />
      {problems && (
        <>
          <div className="grid stats">
            <Stat label="Solved" value={`${solved}/${problems.length}`} hint={`${pct(solved, problems.length)}% of the list`} />
            <Stat label="Due for review" value={due} />
            <Stat label="Mastered" value={problems.filter((p) => p.status === 'mastered').length} />
            <Stat label="Attempts" value={problems.reduce((n, p) => n + p.attempts, 0)} />
          </div>
          <Card className="section">
            <div className="filters">
              <div className="tabs" style={{ margin: 0 }}>
                {(['all', 'due', 'todo'] as const).map((v) => (
                  <button key={v} className={`tab ${view === v ? 'active' : ''}`} onClick={() => setView(v)}>
                    {v === 'all' ? 'All' : v === 'due' ? `Due (${due})` : 'Not started'}
                  </button>
                ))}
              </div>
              <select value={topic} onChange={(e) => setTopic(e.target.value)} aria-label="Topic">
                <option value="">All topics</option>
                {topics.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
              <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)} aria-label="Difficulty">
                <option value="">Any difficulty</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
            {filtered.length === 0 && <Empty>Nothing here. {view === 'due' && 'No reviews due — nice.'}</Empty>}
            {filtered.length > 0 && (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Problem</th>
                      <th className="hide-sm">Topic</th>
                      <th>Status</th>
                      <th className="hide-sm">Next review</th>
                      <th>Log attempt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((p) => {
                      const rel = relativeDue(p.next_review)
                      return (
                        <tr key={p.id}>
                          <td className="title-cell">
                            <b>{p.url ? <a href={p.url} target="_blank" rel="noreferrer">{p.title}</a> : p.title}</b>
                            <span>
                              <Chip tone={DIFF_TONE[p.difficulty]}>{p.difficulty}</Chip>
                              {p.attempts > 0 && `${p.attempts} attempt${p.attempts === 1 ? '' : 's'}`}
                            </span>
                          </td>
                          <td className="hide-sm">{p.topic}</td>
                          <td>
                            <Chip tone={STATUS_TONE[p.status]}>{p.status}</Chip>
                          </td>
                          <td className={`hide-sm tone-${rel.tone}`}>{rel.text}</td>
                          <td>
                            <QualityButtons onRate={(q) => practice(p, q)} />
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
          <Card className="section" title="By topic">
            <div className="grid halves">
              {topics.map((t) => {
                const items = problems.filter((p) => p.topic === t)
                const done = items.filter((p) => p.status === 'solved' || p.status === 'mastered').length
                return (
                  <div className="goal" key={t}>
                    <div className="goal-row">
                      <span>{t}</span>
                      <b>
                        {done}/{items.length}
                      </b>
                    </div>
                    <Bar value={done} max={items.length} label={t} />
                  </div>
                )
              })}
            </div>
          </Card>
        </>
      )}
      {adding && (
        <AddProblem
          topics={topics}
          onClose={() => setAdding(false)}
          onSaved={(p) => {
            setAdding(false)
            setData((prev) => [...(prev ?? []), p])
          }}
        />
      )}
    </>
  )
}

function AddProblem({ topics, onClose, onSaved }: { topics: string[]; onClose: () => void; onSaved: (p: DSAProblem) => void }) {
  const [form, setForm] = useState({ title: '', topic: topics[0] ?? 'arrays & hashing', difficulty: 'medium' as Difficulty, url: '' })
  const [err, setErr] = useState<string | null>(null)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      onSaved(await api.dsa.create(form))
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex))
    }
  }
  return (
    <Modal title="Add problem" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <Field label="Title *" full>
          <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </Field>
        <Field label="Topic">
          <input list="topics" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} />
          <datalist id="topics">
            {topics.map((t) => (
              <option key={t} value={t} />
            ))}
          </datalist>
        </Field>
        <Field label="Difficulty">
          <select value={form.difficulty} onChange={(e) => setForm({ ...form, difficulty: e.target.value as Difficulty })}>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </Field>
        <Field label="Link" full>
          <input type="url" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="https://leetcode.com/problems/…" />
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
