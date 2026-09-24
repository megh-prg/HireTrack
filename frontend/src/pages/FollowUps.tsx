import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type FollowUp } from '../api'
import { Card, Chip, Empty, PageHeader, Status } from '../components/ui'
import { formatDate, localToday } from '../format'
import { useApi } from '../hooks'

const KIND_LINK: Record<FollowUp['kind'], string> = {
  application: '/applications',
  recruiter: '/recruiters',
  dsa: '/dsa',
  prep: '/prep',
}

export default function FollowUps() {
  const [horizon, setHorizon] = useState(7)
  const { data, error, loading, reload } = useApi(() => api.followups.list(horizon), [horizon])
  const today = localToday()

  const complete = async (item: FollowUp, reschedule?: number) => {
    if (item.kind === 'application' || item.kind === 'recruiter') {
      await api.followups.complete(item.kind, item.id, reschedule)
      reload()
    }
  }

  const people = data?.filter((i) => i.kind === 'application' || i.kind === 'recruiter') ?? []
  const reviews = data?.filter((i) => i.kind === 'dsa' || i.kind === 'prep') ?? []
  const groups = [
    { title: 'Overdue', items: people.filter((i) => i.due < today) },
    { title: 'Today', items: people.filter((i) => i.due === today) },
    { title: 'Coming up', items: people.filter((i) => i.due > today) },
  ]

  return (
    <>
      <PageHeader
        title="Follow-ups"
        subtitle="A polite nudge 5–7 days after applying or messaging roughly doubles reply rates. Don't let these slip."
        actions={
          <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} aria-label="Horizon">
            <option value={0}>Due now</option>
            <option value={7}>Next 7 days</option>
            <option value={14}>Next 14 days</option>
            <option value={30}>Next 30 days</option>
          </select>
        }
      />
      <Status loading={loading && !data} error={error} />
      {data && (
        <div className="grid two">
          <div className="stack">
            {people.length === 0 && (
              <Card>
                <Empty>No follow-ups in this window.</Empty>
              </Card>
            )}
            {groups
              .filter((g) => g.items.length)
              .map((g) => (
                <Card key={g.title} title={`${g.title} (${g.items.length})`}>
                  {g.items.map((item) => (
                    <div className="list-item" key={`${item.kind}-${item.id}`}>
                      <Chip tone={item.kind === 'application' ? 'accent' : 'default'}>{item.kind}</Chip>
                      <div className="grow">
                        <div className="title">
                          <Link to={KIND_LINK[item.kind]}>{item.title}</Link>
                        </div>
                        <div className="sub">
                          {item.subtitle} · {item.overdue_days > 0 ? <span className="tone-danger">{item.overdue_days}d overdue</span> : formatDate(item.due)}
                        </div>
                      </div>
                      <div className="actions">
                        <button className="btn small" onClick={() => complete(item, 3)} title="Mark done and check again in 3 days">
                          Snooze 3d
                        </button>
                        <button className="btn small" onClick={() => complete(item, 7)} title="Mark done and follow up again in a week">
                          Done, +7d
                        </button>
                        <button className="btn small primary" onClick={() => complete(item)}>
                          Done
                        </button>
                      </div>
                    </div>
                  ))}
                </Card>
              ))}
          </div>
          <Card title={`Reviews due (${reviews.length})`}>
            {reviews.length === 0 ? (
              <Empty>No DSA or prep reviews due.</Empty>
            ) : (
              <>
                {reviews.slice(0, 12).map((item) => (
                  <div className="list-item" key={`${item.kind}-${item.id}`}>
                    <Chip>{item.kind}</Chip>
                    <div className="grow">
                      <div className="title">{item.title}</div>
                      <div className="sub">{item.subtitle}</div>
                    </div>
                  </div>
                ))}
                <div className="actions" style={{ marginTop: 10 }}>
                  <Link className="btn small" to="/dsa">Review DSA</Link>
                  <Link className="btn small" to="/prep">Review prep</Link>
                </div>
              </>
            )}
          </Card>
        </div>
      )}
    </>
  )
}
