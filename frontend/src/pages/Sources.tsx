import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError, type JobSource, type SourceInput, type SourceKind } from '../api'
import { Card, Chip, Empty, Field, PageHeader, Status } from '../components/ui'
import { useApi } from '../hooks'

// Company careers boards verified to publish live postings through a public ATS API.
const SUGGESTED: { name: string; url: string; note: string }[] = [
  { name: 'Groww', url: 'https://job-boards.greenhouse.io/groww', note: 'Bengaluru' },
  { name: 'CRED', url: 'https://jobs.lever.co/cred', note: 'Bengaluru' },
  { name: 'Meesho', url: 'https://jobs.lever.co/meesho', note: 'Bengaluru' },
  { name: 'Zeta', url: 'https://jobs.lever.co/zeta', note: 'Bengaluru / Hyderabad' },
  { name: 'Sarvam AI', url: 'https://jobs.ashbyhq.com/sarvam', note: 'GenAI, Bengaluru' },
  { name: 'Atlan', url: 'https://jobs.ashbyhq.com/atlan', note: 'Remote India' },
  { name: 'Databricks', url: 'https://boards.greenhouse.io/databricks', note: 'Bengaluru office' },
  { name: 'GitLab', url: 'https://boards.greenhouse.io/gitlab', note: 'All-remote' },
  { name: 'Cohere', url: 'https://jobs.ashbyhq.com/cohere', note: 'GenAI' },
]

const DEFAULT_TITLES = 'engineer, developer, sde, scientist, architect, ml, llm, genai'
const DEFAULT_PLACES = 'india, bengaluru, bangalore, hyderabad, pune, remote'

const KIND_LABEL: Record<SourceKind, string> = {
  greenhouse: 'Greenhouse',
  lever: 'Lever',
  ashby: 'Ashby',
  adzuna: 'Adzuna India',
  remotive: 'Remotive',
}

type Mode = 'company' | 'adzuna' | 'remotive' | 'file'

export default function Sources() {
  const { data: sources, error, loading, reload } = useApi(() => api.sources.list())
  const [mode, setMode] = useState<Mode>('company')
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState<{ tone: 'ok' | 'err'; text: string } | null>(null)

  const run = async (key: string, fn: () => Promise<string>) => {
    setBusy(key)
    setMessage(null)
    try {
      setMessage({ tone: 'ok', text: await fn() })
      reload()
    } catch (e) {
      setMessage({ tone: 'err', text: e instanceof ApiError || e instanceof Error ? e.message : String(e) })
    } finally {
      setBusy(null)
    }
  }

  const add = (body: SourceInput, label: string) =>
    run('add', async () => {
      const r = await api.sources.create(body)
      return `${label}: ${r.found} matching job${r.found === 1 ? '' : 's'} found, ${r.created} new. Saved — it refreshes automatically.`
    })

  const savedUrls = new Set(sources?.map((s) => `${s.kind}:${s.query}`))

  return (
    <>
      <PageHeader
        title="Job sources"
        subtitle="Real openings pulled from company careers pages and job boards through their official APIs. Duplicates are skipped and every job is scored against your profile."
        actions={
          sources && sources.length > 0 ? (
            <button
              className="btn primary"
              disabled={!!busy}
              onClick={() =>
                run('all', async () => {
                  const results = await api.sources.runAll()
                  const created = results.reduce((n, r) => n + r.created, 0)
                  const failed = results.filter((r) => r.source.last_error).length
                  return `Refreshed ${results.length} source${results.length === 1 ? '' : 's'}: ${created} new job${created === 1 ? '' : 's'}${failed ? `, ${failed} failed` : ''}.`
                })
              }
            >
              {busy === 'all' ? 'Refreshing…' : '↻ Refresh all'}
            </button>
          ) : undefined
        }
      />
      {message && (
        <div className={message.tone === 'ok' ? 'notice' : 'alert'}>
          {message.text} {message.tone === 'ok' && <Link to="/jobs">View jobs →</Link>}
        </div>
      )}

      <div className="grid two">
        <Card title="Your sources">
          <Status loading={loading && !sources} error={error} />
          {sources && sources.length === 0 && (
            <Empty>No sources yet. Add a company on the right — try one of the suggestions.</Empty>
          )}
          {sources?.map((s) => (
            <SourceRow
              key={s.id}
              source={s}
              busy={busy === `run-${s.id}`}
              onRun={() =>
                run(`run-${s.id}`, async () => {
                  const r = await api.sources.run(s.id)
                  if (r.source.last_error) throw new Error(r.source.last_error)
                  return `${sourceName(s)}: ${r.found} matching, ${r.created} new.`
                })
              }
              onDelete={() =>
                run(`del-${s.id}`, async () => {
                  if (!confirm(`Stop importing from ${sourceName(s)}? Jobs already imported stay.`)) return 'Cancelled.'
                  await api.sources.remove(s.id)
                  return `Removed ${sourceName(s)}.`
                })
              }
            />
          ))}
        </Card>

        <Card title="Add a source">
          <div className="tabs">
            {(
              [
                ['company', 'Company careers page'],
                ['adzuna', 'Adzuna (India)'],
                ['remotive', 'Remote jobs'],
                ['file', 'CSV / JSON'],
              ] as [Mode, string][]
            ).map(([m, label]) => (
              <button key={m} className={`tab ${mode === m ? 'active' : ''}`} onClick={() => setMode(m)}>
                {label}
              </button>
            ))}
          </div>
          {mode === 'company' && (
            <CompanyForm busy={busy === 'add'} saved={savedUrls} onAdd={add} />
          )}
          {mode === 'adzuna' && (
            <SearchForm
              kind="adzuna"
              busy={busy === 'add'}
              onAdd={add}
              help={
                <>
                  Adzuna aggregates listings from Indian job sites. It needs a free API key: sign up at{' '}
                  <a href="https://developer.adzuna.com" target="_blank" rel="noreferrer">developer.adzuna.com</a>, then set{' '}
                  <code>ADZUNA_APP_ID</code> and <code>ADZUNA_APP_KEY</code> for the backend and restart it.
                </>
              }
            />
          )}
          {mode === 'remotive' && (
            <SearchForm
              kind="remotive"
              busy={busy === 'add'}
              onAdd={add}
              help="Remote-only roles worldwide from Remotive. Many are restricted to US/EU time zones — the match score marks those."
            />
          )}
          {mode === 'file' && (
            <div>
              <p className="muted small">
                For boards without an API (LinkedIn, Naukri, Instahyre…), keep a spreadsheet of roles you find and upload it. Columns:{' '}
                <code>title, company, location, salary, url, description, remote</code>.
              </p>
              <input
                type="file"
                accept=".csv,.json"
                disabled={!!busy}
                style={{ marginTop: 10 }}
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file)
                    run('add', async () => {
                      const r = await api.jobs.upload(file)
                      return `Imported ${r.created} new job${r.created === 1 ? '' : 's'} (${r.duplicates} duplicate${r.duplicates === 1 ? '' : 's'} skipped).`
                    })
                  e.target.value = ''
                }}
              />
            </div>
          )}
        </Card>
      </div>
    </>
  )
}

function sourceName(s: JobSource) {
  if (s.kind === 'adzuna' || s.kind === 'remotive') return `${KIND_LABEL[s.kind]} “${s.query}”${s.location ? ` in ${s.location}` : ''}`
  return s.company_name || s.query
}

function SourceRow({ source: s, busy, onRun, onDelete }: { source: JobSource; busy: boolean; onRun: () => void; onDelete: () => void }) {
  const ran = s.last_run_at ? new Date(s.last_run_at) : null
  return (
    <div className="list-item">
      <div className="grow">
        <div className="title">
          {sourceName(s)} <Chip>{KIND_LABEL[s.kind]}</Chip>
        </div>
        <div className="sub">
          {s.last_error ? (
            <span className="tone-danger">{s.last_error}</span>
          ) : ran ? (
            <>
              Last run {ran.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })} · {s.last_found} matching · {s.last_created} new
            </>
          ) : (
            'Never run'
          )}
        </div>
        {(s.title_keywords || s.location_keywords) && (
          <div className="sub" title="Only jobs matching these filters are imported">
            Filters: {[s.title_keywords && `title ~ ${s.title_keywords}`, s.location_keywords && `location ~ ${s.location_keywords}`].filter(Boolean).join(' · ')}
          </div>
        )}
      </div>
      <div className="actions">
        <button className="btn small" disabled={busy} onClick={onRun}>
          {busy ? '…' : 'Refresh'}
        </button>
        <button className="btn small danger" onClick={onDelete} aria-label="Remove source">
          ✕
        </button>
      </div>
    </div>
  )
}

function Filters({ titles, places, setTitles, setPlaces }: { titles: string; places: string; setTitles: (v: string) => void; setPlaces: (v: string) => void }) {
  return (
    <>
      <Field label="Only titles containing (comma separated, blank = all)" full>
        <input value={titles} onChange={(e) => setTitles(e.target.value)} />
      </Field>
      <Field label="Only locations containing (remote jobs always pass)" full>
        <input value={places} onChange={(e) => setPlaces(e.target.value)} />
      </Field>
    </>
  )
}

function CompanyForm({ busy, saved, onAdd }: { busy: boolean; saved: Set<string>; onAdd: (b: SourceInput, label: string) => void }) {
  const [url, setUrl] = useState('')
  const [name, setName] = useState('')
  const [titles, setTitles] = useState(DEFAULT_TITLES)
  const [places, setPlaces] = useState(DEFAULT_PLACES)
  const slugOf = (u: string) => {
    const m = u.match(/(greenhouse\.io|lever\.co|ashbyhq\.com)\/([\w.-]+)/)
    return m ? `${m[1].startsWith('green') ? 'greenhouse' : m[1].startsWith('lever') ? 'lever' : 'ashby'}:${m[2]}` : ''
  }
  return (
    <form
      className="form"
      onSubmit={(e) => {
        e.preventDefault()
        onAdd({ url, company_name: name, title_keywords: titles, location_keywords: places }, name || 'Company')
      }}
    >
      <p className="muted small full" style={{ margin: 0 }}>
        Paste the company's careers-board link. Most startups use Greenhouse, Lever or Ashby — open a job on their careers page and
        look for <code>greenhouse.io</code>, <code>lever.co</code> or <code>ashbyhq.com</code> in the address bar.
      </p>
      <div className="chips full">
        {SUGGESTED.map((c) => {
          const done = saved.has(slugOf(c.url))
          return (
            <button
              type="button"
              key={c.url}
              className="btn small"
              disabled={done}
              title={c.note}
              onClick={() => {
                setUrl(c.url)
                setName(c.name)
              }}
            >
              {done ? '✓ ' : '+ '}
              {c.name}
            </button>
          )
        })}
      </div>
      <Field label="Careers board URL *">
        <input required value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://jobs.lever.co/company" />
      </Field>
      <Field label="Company name">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Shown on each job" />
      </Field>
      <Filters titles={titles} places={places} setTitles={setTitles} setPlaces={setPlaces} />
      <div className="form-actions">
        <button className="btn primary" disabled={busy}>
          {busy ? 'Fetching…' : 'Add & fetch jobs'}
        </button>
      </div>
    </form>
  )
}

function SearchForm({ kind, busy, onAdd, help }: { kind: 'adzuna' | 'remotive'; busy: boolean; onAdd: (b: SourceInput, label: string) => void; help: React.ReactNode }) {
  const [query, setQuery] = useState(kind === 'adzuna' ? 'python developer' : 'python')
  const [location, setLocation] = useState(kind === 'adzuna' ? 'Bangalore' : '')
  const [titles, setTitles] = useState(kind === 'adzuna' ? '' : DEFAULT_TITLES)
  const [places, setPlaces] = useState('')
  return (
    <form
      className="form"
      onSubmit={(e) => {
        e.preventDefault()
        onAdd({ kind, query, location, title_keywords: titles, location_keywords: places, limit: 100 }, KIND_LABEL[kind])
      }}
    >
      <p className="muted small full" style={{ margin: 0 }}>
        {help}
      </p>
      <Field label="Search keywords *">
        <input required value={query} onChange={(e) => setQuery(e.target.value)} />
      </Field>
      {kind === 'adzuna' ? (
        <Field label="City / region">
          <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Bangalore" />
        </Field>
      ) : (
        <div />
      )}
      <Filters titles={titles} places={places} setTitles={setTitles} setPlaces={setPlaces} />
      <div className="form-actions">
        <button className="btn primary" disabled={busy}>
          {busy ? 'Fetching…' : 'Add & fetch jobs'}
        </button>
      </div>
    </form>
  )
}
