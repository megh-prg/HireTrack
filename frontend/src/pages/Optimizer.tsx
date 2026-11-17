import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, type BuildProfileResult, type Optimization, type OptimizedResume } from '../api'
import { Card, Chip, Empty, Field, PageHeader, Score, Status } from '../components/ui'
import { useApi } from '../hooks'

function ResumePreview({ resume }: { resume: OptimizedResume }) {
  return (
    <div className="optimized">
      {resume.summary && (
        <>
          <h4>Summary</h4>
          <p className="muted">{resume.summary}</p>
        </>
      )}
      {resume.skills && resume.skills.length > 0 && (
        <>
          <h4>Skills</h4>
          <div className="chips">
            {resume.skills.map((s) => (
              <Chip key={s} tone="good">{s}</Chip>
            ))}
          </div>
        </>
      )}
      {resume.experience && resume.experience.length > 0 && (
        <>
          <h4>Experience</h4>
          <ul>{resume.experience.map((e, i) => <li key={i}>{e}</li>)}</ul>
        </>
      )}
      {resume.projects && resume.projects.length > 0 && (
        <>
          <h4>Projects</h4>
          <ul>{resume.projects.map((p, i) => <li key={i}>{p}</li>)}</ul>
        </>
      )}
    </div>
  )
}

export default function Optimizer() {
  const [params, setParams] = useSearchParams()
  const { data, error, loading } = useApi(() => Promise.all([api.resume.get(), api.jobs.list()]), [])
  const [resumeText, setResumeText] = useState('')
  const [savedText, setSavedText] = useState('')
  const [sections, setSections] = useState<{ present: string[]; missing: string[] }>({ present: [], missing: [] })
  const [jobId, setJobId] = useState<number | null>(null)
  const [result, setResult] = useState<Optimization | null>(null)
  const [profileResult, setProfileResult] = useState<BuildProfileResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!data) return
    const [resume] = data
    setResumeText(resume.resume_text)
    setSavedText(resume.resume_text)
    setSections({ present: resume.sections_present, missing: resume.sections_missing })
    const q = Number(params.get('job'))
    if (q) setJobId(q)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  const jobs = data?.[1] ?? []
  const dirty = resumeText !== savedText

  const saveResume = async () => {
    setBusy(true)
    setMsg(null)
    try {
      const r = await api.resume.save(resumeText)
      setSavedText(r.resume_text)
      setSections({ present: r.sections_present, missing: r.sections_missing })
      setMsg('Resume saved.')
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const upload = async (file: File) => {
    setBusy(true)
    setMsg(null)
    try {
      const r = await api.resume.upload(file)
      setResumeText(r.resume_text)
      setSavedText(r.resume_text)
      setSections({ present: r.sections_present, missing: r.sections_missing })
      setMsg('Resume uploaded.')
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const buildProfile = async () => {
    setBusy(true)
    setMsg(null)
    try {
      setProfileResult(await api.resume.buildProfile())
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const optimize = async () => {
    if (!jobId) return
    setBusy(true)
    setMsg(null)
    setResult(null)
    try {
      setResult(await api.optimizer.run(jobId))
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const selectJob = (id: number | null) => {
    setJobId(id)
    setResult(null)
    setParams(id ? { job: String(id) } : {})
  }

  return (
    <>
      <PageHeader
        title="Resume Optimizer"
        subtitle="Tailor your resume to a specific job — scored, rewritten, and checked so it never adds experience you don't actually have."
      />
      <Status loading={loading && !data} error={error} />

      <div className="grid two">
        <Card title="Your resume">
          <textarea
            rows={14}
            value={resumeText}
            placeholder="Paste your resume text here, or upload a PDF/DOCX below…"
            onChange={(e) => setResumeText(e.target.value)}
            style={{ width: '100%' }}
          />
          <div className="chips" style={{ marginTop: 8 }}>
            {sections.present.map((s) => <Chip key={s} tone="good">✓ {s}</Chip>)}
            {sections.missing.map((s) => <Chip key={s} tone="warn">missing: {s}</Chip>)}
          </div>
          <div className="form-actions" style={{ marginTop: 10, display: 'flex', gap: 8, alignItems: 'center' }}>
            <button className="btn primary" disabled={busy || !dirty} onClick={saveResume}>
              Save resume
            </button>
            <label className="btn small" style={{ cursor: 'pointer' }}>
              Upload PDF/DOCX
              <input
                type="file"
                accept=".pdf,.docx"
                hidden
                onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
              />
            </label>
            {msg && <span className="small muted">{msg}</span>}
          </div>

          <div style={{ marginTop: 14, borderTop: '1px solid rgba(128,128,128,0.25)', paddingTop: 12 }}>
            <p className="small muted" style={{ marginTop: 0 }}>
              New here? Build your skill profile straight from your résumé — works for any tech stack.
            </p>
            <button className="btn" disabled={busy || !savedText.trim()} onClick={buildProfile}>
              {busy ? 'Reading your résumé…' : 'Build my profile & match jobs'}
            </button>
            {profileResult && (
              <div style={{ marginTop: 10 }}>
                <div className="sub">
                  Added {profileResult.skills.length} skill{profileResult.skills.length === 1 ? '' : 's'} · matched{' '}
                  {profileResult.matched} job{profileResult.matched === 1 ? '' : 's'}
                </div>
                <div className="chips" style={{ marginTop: 4 }}>
                  {profileResult.skills.slice(0, 24).map((s) => (
                    <Chip key={s} tone="good">{s}</Chip>
                  ))}
                </div>
                <div style={{ marginTop: 8 }}>
                  <Link className="btn small" to="/matching">View matched jobs →</Link>
                </div>
              </div>
            )}
          </div>
        </Card>

        <Card title="Optimize for a job">
          {jobs.length === 0 ? (
            <Empty>Add a job first in the Jobs tab, then come back to tailor your resume to it.</Empty>
          ) : (
            <>
              <Field label="Pick a saved job">
                <select
                  value={jobId ?? ''}
                  onChange={(e) => selectJob(e.target.value ? Number(e.target.value) : null)}
                >
                  <option value="">— choose a job —</option>
                  {jobs.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.title} · {j.company}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="form-actions" style={{ marginTop: 10 }}>
                <button className="btn primary" disabled={busy || !jobId || !savedText.trim()} onClick={optimize}>
                  {busy ? 'Optimizing…' : 'Optimize my resume'}
                </button>
              </div>
              {!savedText.trim() && <p className="small muted">Save your resume first.</p>}
            </>
          )}
        </Card>
      </div>

      {result && (
        <Card className="section" title="Result">
          <div className="list-item">
            <div className="grow">
              <div className="sub">ATS score for this job</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 4 }}>
                <span>
                  <Score value={result.score_before} /> <span className="small muted">before</span>
                </span>
                {result.score_after !== null && (
                  <span>
                    → <Score value={result.score_after} /> <span className="small muted">after</span>
                  </span>
                )}
              </div>
            </div>
            {result.optimized_resume && (
              <div style={{ display: 'flex', gap: 8 }}>
                <a className="btn small" href={api.optimizer.downloadUrl(result.job_id, 'pdf')}>PDF</a>
                <a className="btn small" href={api.optimizer.downloadUrl(result.job_id, 'docx')}>DOCX</a>
              </div>
            )}
          </div>

          {result.missing_keywords.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div className="sub">Missing keywords from this job</div>
              <div className="chips" style={{ marginTop: 4 }}>
                {result.missing_keywords.map((k) => <Chip key={k} tone="danger">{k}</Chip>)}
              </div>
            </div>
          )}

          {!result.ai_available && (
            <div className="alert" style={{ marginTop: 12 }}>
              Showing the deterministic ATS score and keyword gaps. Add a free <code>GEMINI_API_KEY</code> on the
              server to enable the AI rewrite.
            </div>
          )}

          {result.unsupported_claims.length > 0 && (
            <div className="alert" style={{ marginTop: 12 }}>
              <strong>Kept honest</strong> — removed or flagged claims not supported by your original resume:
              <ul>{result.unsupported_claims.map((c, i) => <li key={i}>{c}</li>)}</ul>
            </div>
          )}

          {result.optimized_resume && (
            <div style={{ marginTop: 12 }}>
              <h3>Tailored resume</h3>
              <ResumePreview resume={result.optimized_resume} />
            </div>
          )}
        </Card>
      )}
    </>
  )
}
