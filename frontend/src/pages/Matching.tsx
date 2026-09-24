import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Analysis } from '../api'
import { Card, Chip, Empty, Field, PageHeader, Score, Status } from '../components/ui'
import { formatLocation, TRACK_LABELS } from '../format'
import { useApi } from '../hooks'

export default function Matching() {
  const [minScore, setMinScore] = useState(50)
  const { data, error, loading, reload } = useApi(
    () => Promise.all([api.matching.top(minScore), api.matching.gaps()]),
    [minScore],
  )
  const [jd, setJd] = useState({ title: '', location: '', description: '' })
  const [analysis, setAnalysis] = useState<Analysis | null>(null)

  const analyze = async (e: React.FormEvent) => {
    e.preventDefault()
    setAnalysis(await api.matching.analyze(jd))
  }
  const track = async (jobId: number) => {
    await api.applications.create({ job_id: jobId, stage: 'saved' })
    reload()
  }

  return (
    <>
      <PageHeader
        title="Matching"
        subtitle="Score = 55% skill coverage + 30% title fit + 15% location fit. Update your skills in Profile to rescore."
        actions={
          <button className="btn" onClick={async () => { await api.matching.recompute(); reload() }}>
            Rescore all
          </button>
        }
      />
      <div className="grid two">
        <Card title="Check a job description">
          <form className="form" onSubmit={analyze}>
            <Field label="Title">
              <input value={jd.title} onChange={(e) => setJd({ ...jd, title: e.target.value })} placeholder="GenAI Engineer" />
            </Field>
            <Field label="Location">
              <input value={jd.location} onChange={(e) => setJd({ ...jd, location: e.target.value })} placeholder="Remote" />
            </Field>
            <Field label="Paste the description" full>
              <textarea required rows={7} value={jd.description} onChange={(e) => setJd({ ...jd, description: e.target.value })} />
            </Field>
            <div className="form-actions">
              <button className="btn primary">Analyze fit</button>
            </div>
          </form>
          {analysis && (
            <div className="list-item" style={{ marginTop: 10 }}>
              <Score value={analysis.score} />
              <div className="grow">
                <div className="sub">{analysis.reasons.join(' · ')}</div>
                <div className="chips" style={{ marginTop: 6 }}>
                  {analysis.matched_skills.map((s) => <Chip key={s} tone="good">✓ {s}</Chip>)}
                  {analysis.missing_skills.map((s) => <Chip key={s} tone="danger">✗ {s}</Chip>)}
                </div>
              </div>
            </div>
          )}
        </Card>
        <Card title="Your skill gaps">
          <p className="muted small" style={{ marginTop: -6, marginBottom: 8 }}>
            Skills most often missing from jobs that otherwise fit you (score ≥ 40).
          </p>
          {data && data[1].length === 0 && <Empty>No gaps yet — add more jobs.</Empty>}
          {data?.[1].map((g) => (
            <div className="list-item" key={g.skill}>
              <div className="grow">
                <div className="title">{g.skill}</div>
                <div className="sub">missing in {g.jobs} job{g.jobs === 1 ? '' : 's'}</div>
              </div>
              {g.track && (
                <Link className="btn small" to={g.track === 'dsa' ? '/dsa' : `/prep?track=${g.track}`}>
                  Study {TRACK_LABELS[g.track]}
                </Link>
              )}
            </div>
          ))}
        </Card>
      </div>

      <Card
        className="section"
        title="Top untracked matches"
        actions={
          <label className="small muted" style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            Min score {minScore}
            <input type="range" min={0} max={90} step={5} value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} />
          </label>
        }
      >
        <Status loading={loading && !data} error={error} />
        {data && data[0].length === 0 && <Empty>No untracked jobs at this score. Lower the threshold or import more jobs.</Empty>}
        {data?.[0].map((job) => (
          <div className="list-item" key={job.id}>
            <Score value={job.match_score} />
            <div className="grow">
              <div className="title">
                {job.url ? <a href={job.url} target="_blank" rel="noreferrer">{job.title}</a> : job.title}
              </div>
              <div className="sub">
                {job.company} · {formatLocation(job)}
              </div>
              <div className="chips" style={{ marginTop: 4 }}>
                {job.matched_skills.map((s) => <Chip key={s} tone="good">{s}</Chip>)}
                {job.missing_skills.map((s) => <Chip key={s} tone="danger">{s}</Chip>)}
              </div>
            </div>
            <button className="btn small" onClick={() => track(job.id)}>
              Track
            </button>
          </div>
        ))}
      </Card>
    </>
  )
}
