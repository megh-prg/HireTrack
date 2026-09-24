import { Link } from 'react-router-dom'
import { api } from '../api'
import { Bar, Card, Chip, Empty, PageHeader, Score, Stat, Status } from '../components/ui'
import { relativeDue, TRACK_LABELS } from '../format'
import { useApi } from '../hooks'

export default function Today() {
  const { data, error, loading } = useApi(() =>
    Promise.all([api.progress(), api.followups.list(0), api.matching.top(50), api.prep.recommended(4)]),
  )
  const header = (
    <PageHeader
      title="Today"
      subtitle={new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
      actions={
        <Link className="btn primary" to="/jobs">
          + Add jobs
        </Link>
      }
    />
  )
  if (!data) return (<>{header}<Status loading={loading} error={error} /></>)
  const [progress, due, matches, prep] = data
  const t = progress.totals

  return (
    <>
      {header}
      <div className="grid stats">
        <Stat label="Applications" value={t.applications} hint={`${t.active} active`} />
        <Stat label="Response rate" value={`${progress.response_rate}%`} hint="reached recruiter screen" />
        <Stat label="Interviews" value={t.interviews} hint={`${t.offers} offer${t.offers === 1 ? '' : 's'}`} />
        <Stat label="DSA solved" value={`${t.dsa_solved}/${t.dsa_total}`} />
        <Stat label="Streak" value={`${progress.practice_streak_days}d`} hint="days with practice or applications" />
      </div>

      <div className="grid two section">
        <div className="stack">
          <Card title="Due today" actions={<Link to="/followups">All follow-ups →</Link>}>
            {due.length === 0 ? (
              <Empty>Nothing due. Go find a new role or solve a problem.</Empty>
            ) : (
              due.slice(0, 6).map((item) => {
                const rel = relativeDue(item.due)
                return (
                  <div className="list-item" key={`${item.kind}-${item.id}`}>
                    <Chip tone={item.kind === 'application' ? 'accent' : 'default'}>{item.kind}</Chip>
                    <div className="grow">
                      <div className="title">{item.title}</div>
                      <div className="sub">{item.subtitle}</div>
                    </div>
                    <span className={`tone-${rel.tone} small`}>{rel.text}</span>
                  </div>
                )
              })
            )}
          </Card>
          <Card title="Best new matches" actions={<Link to="/matching">Matching →</Link>}>
            {matches.length === 0 ? (
              <Empty>
                No untracked matches above 50. <Link to="/jobs">Import jobs</Link> or update your{' '}
                <Link to="/settings">skills</Link>.
              </Empty>
            ) : (
              matches.slice(0, 5).map((job) => (
                <div className="list-item" key={job.id}>
                  <Score value={job.match_score} />
                  <div className="grow">
                    <div className="title">{job.title}</div>
                    <div className="sub">
                      {job.company} · {job.location || 'Location n/a'}
                    </div>
                  </div>
                </div>
              ))
            )}
          </Card>
        </div>
        <div className="stack">
          <Card title="This week">
            {progress.weekly_goals.map((g) => (
              <div className="goal" key={g.label}>
                <div className="goal-row">
                  <span>{g.label}</span>
                  <b>
                    {g.done} / {g.goal}
                  </b>
                </div>
                <Bar value={g.done} max={g.goal} label={g.label} />
              </div>
            ))}
          </Card>
          <Card title="Prep for you" actions={<Link to="/prep">Practice →</Link>}>
            {prep.map((q) => (
              <div className="list-item" key={q.id}>
                <div className="grow">
                  <div className="title">{q.question}</div>
                  <div className="sub">{TRACK_LABELS[q.track]}</div>
                </div>
              </div>
            ))}
            {progress.skill_gaps.length > 0 && (
              <p className="muted small">
                Based on gaps in your matches: {progress.skill_gaps.slice(0, 4).map((g) => g.skill).join(', ')}
              </p>
            )}
          </Card>
        </div>
      </div>
    </>
  )
}
