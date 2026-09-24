import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError, type Job, type JobInput } from '../api'
import { Card, Chip, Empty, Field, Modal, PageHeader, Score, Status } from '../components/ui'
import { formatDate, formatLocation, stageLabel } from '../format'
import { useApi } from '../hooks'

export default function Jobs() {
  const [q, setQ] = useState('')
  const [source, setSource] = useState('')
  const [sort, setSort] = useState<'newest' | 'score'>('score')
  const [adding, setAdding] = useState(false)
  const [selected, setSelected] = useState<Job | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const { data: jobs, error, loading, reload } = useApi(() => api.jobs.list({ q, source, sort }), [q, source, sort])

  const track = async (job: Job) => {
    await api.applications.create({ job_id: job.id, stage: 'saved' })
    setNotice(`Tracking “${job.title}” — find it under Applications.`)
    reload()
  }

  return (
    <>
      <PageHeader
        title="Jobs"
        subtitle="Every role you're considering, de-duplicated and scored against your profile."
        actions={
          <>
            <Link className="btn" to="/sources">
              ↻ Job sources
            </Link>
            <button className="btn primary" onClick={() => setAdding(true)}>
              + Add job
            </button>
          </>
        }
      />
      {notice && <div className="notice">{notice}</div>}
      <Card>
        <div className="filters">
          <input type="search" placeholder="Search title, company or location" value={q} onChange={(e) => setQ(e.target.value)} />
          <select value={source} onChange={(e) => setSource(e.target.value)} aria-label="Source">
            <option value="">All sources</option>
            <option value="manual">Manual</option>
            <option value="greenhouse">Greenhouse</option>
            <option value="lever">Lever</option>
            <option value="ashby">Ashby</option>
            <option value="adzuna">Adzuna</option>
            <option value="remotive">Remotive</option>
            <option value="upload">Upload</option>
          </select>
          <select value={sort} onChange={(e) => setSort(e.target.value as 'newest' | 'score')} aria-label="Sort">
            <option value="score">Best match</option>
            <option value="newest">Newest</option>
          </select>
        </div>
        <Status loading={loading && !jobs} error={error} />
        {jobs && jobs.length === 0 && (
          <Empty>
            {q || source ? 'No jobs match these filters.' : <>No jobs yet. <Link to="/sources">Add a job source</Link> to pull real openings from company careers pages, or add one by hand.</>}
          </Empty>
        )}
        {jobs && jobs.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Match</th>
                  <th>Role</th>
                  <th className="hide-sm">Location</th>
                  <th className="hide-sm">Skills</th>
                  <th className="hide-sm">Added</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id} className="clickable" onClick={() => setSelected(job)}>
                    <td>
                      <Score value={job.match_score} />
                    </td>
                    <td className="title-cell">
                      <b>{job.title}</b>
                      <span>
                        {job.company}
                        {job.salary && ` · ${job.salary}`}
                      </span>
                    </td>
                    <td className="hide-sm">{formatLocation(job)}</td>
                    <td className="hide-sm">
                      <div className="chips">
                        {job.skills.slice(0, 4).map((s) => (
                          <Chip key={s} tone={job.matched_skills.includes(s) ? 'good' : 'default'}>
                            {s}
                          </Chip>
                        ))}
                        {job.skills.length > 4 && <Chip>+{job.skills.length - 4}</Chip>}
                      </div>
                    </td>
                    <td className="hide-sm small">{formatDate(job.created_at)}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      {job.application_stage ? (
                        <Chip tone="accent">{stageLabel(job.application_stage)}</Chip>
                      ) : (
                        <button className="btn small" onClick={() => track(job)}>
                          Track
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {adding && (
        <AddJobModal
          onClose={() => setAdding(false)}
          onSaved={(job) => {
            setAdding(false)
            setNotice(`Added “${job.title}” with a ${Math.round(job.match_score ?? 0)} match.`)
            reload()
          }}
        />
      )}
      {selected && (
        <JobDetail
          job={selected}
          onClose={() => setSelected(null)}
          onChanged={() => {
            setSelected(null)
            reload()
          }}
          onTrack={async () => {
            await track(selected)
            setSelected(null)
          }}
        />
      )}
    </>
  )
}

function AddJobModal({ onClose, onSaved }: { onClose: () => void; onSaved: (job: Job) => void }) {
  const [form, setForm] = useState<JobInput>({ title: '', company: '', location: '', salary: '', url: '', description: '' })
  const [err, setErr] = useState<string | null>(null)
  const set = (k: keyof JobInput) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: e.target.value })

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      onSaved(await api.jobs.create(form))
    } catch (ex) {
      setErr(ex instanceof ApiError ? ex.message : String(ex))
    }
  }

  return (
    <Modal title="Add job" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <Field label="Role *">
          <input required value={form.title} onChange={set('title')} placeholder="AI Engineer" />
        </Field>
        <Field label="Company *">
          <input required value={form.company} onChange={set('company')} />
        </Field>
        <Field label="Location">
          <input value={form.location} onChange={set('location')} placeholder="Bengaluru / Remote" />
        </Field>
        <Field label="Salary">
          <input value={form.salary} onChange={set('salary')} placeholder="₹8–12 LPA" />
        </Field>
        <Field label="Link" full>
          <input type="url" value={form.url} onChange={set('url')} placeholder="https://" />
        </Field>
        <Field label="Job description (paste it — skills are extracted automatically)" full>
          <textarea rows={6} value={form.description} onChange={set('description')} />
        </Field>
        {err && <div className="alert full">{err}</div>}
        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary">Save job</button>
        </div>
      </form>
    </Modal>
  )
}

function JobDetail({ job, onClose, onChanged, onTrack }: {
  job: Job
  onClose: () => void
  onChanged: () => void
  onTrack: () => void
}) {
  const remove = async () => {
    if (!confirm(`Delete “${job.title}” at ${job.company}? This also removes its application.`)) return
    await api.jobs.remove(job.id)
    onChanged()
  }
  const archive = async () => {
    await api.jobs.update(job.id, { archived: true })
    onChanged()
  }
  return (
    <Modal title={job.title} onClose={onClose}>
      <p className="muted" style={{ marginTop: -6 }}>
        {job.company} · {formatLocation(job)} {job.salary && `· ${job.salary}`}
      </p>
      <div className="list-item">
        <Score value={job.match_score} />
        <div className="grow">
          <div className="chips">
            {job.matched_skills.map((s) => (
              <Chip key={s} tone="good">
                ✓ {s}
              </Chip>
            ))}
            {job.missing_skills.map((s) => (
              <Chip key={s} tone="danger">
                ✗ {s}
              </Chip>
            ))}
            {job.skills.length === 0 && <span className="muted small">No recognised skills in the description.</span>}
          </div>
        </div>
      </div>
      {job.description && <div className="description">{job.description}</div>}
      <div className="form-actions" style={{ marginTop: 14 }}>
        <button className="btn danger" onClick={remove}>
          Delete
        </button>
        <button className="btn" onClick={archive}>
          Archive
        </button>
        {job.url && (
          <a className="btn" href={job.url} target="_blank" rel="noreferrer">
            Open posting ↗
          </a>
        )}
        {!job.application_id && (
          <button className="btn primary" onClick={onTrack}>
            Track application
          </button>
        )}
      </div>
    </Modal>
  )
}
