import { api } from '../api'
import { Bar, Card, Empty, PageHeader, Stat, Status } from '../components/ui'
import { pct, stageLabel, TRACK_LABELS } from '../format'
import { useApi } from '../hooks'

export default function ProgressPage() {
  const { data, error, loading } = useApi(() => api.progress())
  if (!data)
    return (
      <>
        <PageHeader title="Progress" />
        <Status loading={loading} error={error} />
      </>
    )
  const t = data.totals
  const funnelMax = Math.max(1, ...data.funnel.map((f) => f.count))
  const weekMax = Math.max(1, ...data.applications_per_week.map((w) => w.count))

  return (
    <>
      <PageHeader title="Progress" subtitle="The numbers that tell you what to change: volume, conversion, and preparation." />
      <div className="grid stats">
        <Stat label="Applications" value={t.applications} hint={`${t.jobs} jobs in pipeline`} />
        <Stat label="Response rate" value={`${data.response_rate}%`} hint="applied → recruiter screen" />
        <Stat label="Interview rate" value={`${data.interview_rate}%`} hint="applied → technical round" />
        <Stat label="Recruiter replies" value={`${t.recruiters_replied}/${t.recruiters}`} hint={`${t.referrals} referrals`} />
        <Stat label="Practice streak" value={`${data.practice_streak_days}d`} />
      </div>

      <div className="grid halves section">
        <Card title="Application funnel">
          <p className="muted small" style={{ marginTop: -6, marginBottom: 12 }}>
            Applications that ever reached each stage.
          </p>
          {data.funnel.map((f) => (
            <div className="hbar" key={f.stage} data-tip={`${stageLabel(f.stage)}: ${f.count}`}>
              <span>{stageLabel(f.stage)}</span>
              <div className="track">
                <i style={{ width: `${(f.count / funnelMax) * 100}%` }} />
              </div>
              <span className="num">{f.count}</span>
            </div>
          ))}
        </Card>
        <Card title="Applications per week">
          <p className="muted small" style={{ marginTop: -6 }}>
            Last 8 weeks, by date applied.
          </p>
          <div className="columns-chart" role="img" aria-label="Applications per week">
            {data.applications_per_week.map((w) => (
              <div className="col" key={w.week} data-tip={`Week of ${w.week}: ${w.count}`}>
                {w.count > 0 && <span className="val">{w.count}</span>}
                <i style={{ height: `${(w.count / weekMax) * 85}%` }} />
              </div>
            ))}
          </div>
          <div className="columns-axis">
            {data.applications_per_week.map((w) => (
              <span key={w.week}>{new Date(w.week + 'T00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid halves section">
        <Card title="This week's goals">
          {data.weekly_goals.map((g) => (
            <div className="goal" key={g.label}>
              <div className="goal-row">
                <span>{g.label}</span>
                <b>
                  {g.done}/{g.goal} · {pct(g.done, g.goal)}%
                </b>
              </div>
              <Bar value={g.done} max={g.goal} label={g.label} />
            </div>
          ))}
        </Card>
        <Card title="Interview prep mastery">
          {data.prep_tracks.map((tr) => (
            <div className="goal" key={tr.track}>
              <div className="goal-row">
                <span>{TRACK_LABELS[tr.track]}</span>
                <b>
                  {Math.round(tr.mastery)}% · {tr.reviewed}/{tr.total} reviewed
                </b>
              </div>
              <Bar value={tr.mastery} label={`${tr.track} mastery`} />
            </div>
          ))}
        </Card>
      </div>

      <div className="grid halves section">
        <Card title="DSA by difficulty">
          {data.dsa_by_difficulty.map((d) => (
            <div className="hbar" key={d.difficulty} data-tip={`${d.solved} of ${d.total} solved`}>
              <span style={{ textTransform: 'capitalize' }}>{d.difficulty}</span>
              <div className="track">
                <i style={{ width: `${pct(d.solved, d.total)}%` }} />
              </div>
              <span className="num">
                {d.solved}/{d.total}
              </span>
            </div>
          ))}
          <h3 style={{ margin: '16px 0 10px' }}>By topic</h3>
          {data.dsa_by_topic.map((d) => (
            <div className="hbar" key={d.topic} data-tip={`${d.solved} of ${d.total} solved`}>
              <span>{d.topic}</span>
              <div className="track">
                <i style={{ width: `${pct(d.solved, d.total)}%` }} />
              </div>
              <span className="num">
                {d.solved}/{d.total}
              </span>
            </div>
          ))}
        </Card>
        <Card title="Skill gaps in your matches">
          {data.skill_gaps.length === 0 ? (
            <Empty>No gaps detected yet.</Empty>
          ) : (
            data.skill_gaps.map((g) => (
              <div className="hbar" key={g.skill} data-tip={`Missing in ${g.jobs} matched job(s)`}>
                <span>{g.skill}</span>
                <div className="track">
                  <i style={{ width: `${(g.jobs / data.skill_gaps[0].jobs) * 100}%` }} />
                </div>
                <span className="num">{g.jobs} jobs</span>
              </div>
            ))
          )}
        </Card>
      </div>
    </>
  )
}
