import { useState } from 'react'
import { api, type Profile } from '../api'
import { Card, Field, PageHeader, Status } from '../components/ui'
import { useApi } from '../hooks'

const list = (s: string) => s.split(',').map((x) => x.trim()).filter(Boolean)

export default function Settings() {
  const { data, error, loading } = useApi(() => api.profile.get())
  if (!data)
    return (
      <>
        <PageHeader title="Profile & goals" />
        <Status loading={loading} error={error} />
      </>
    )
  return <ProfileForm initial={data} />
}

function ProfileForm({ initial }: { initial: Profile }) {
  const [form, setForm] = useState(initial)
  const [text, setText] = useState({
    roles: initial.target_roles.join(', '),
    locations: initial.locations.join(', '),
    skills: initial.skills.join(', '),
  })
  const [saved, setSaved] = useState(false)

  const num = (k: keyof Profile) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: Number(e.target.value) })

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    const updated = await api.profile.save({
      ...form,
      target_roles: list(text.roles),
      locations: list(text.locations),
      skills: list(text.skills),
    })
    setForm(updated)
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  return (
    <>
      <PageHeader title="Profile & goals" subtitle="Your roles, skills and locations drive every match score. Saving rescores all jobs." />
      <form onSubmit={save} className="stack">
        <Card title="What you're looking for">
          <div className="form">
            <Field label="Name">
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field>
            <Field label="Years of experience">
              <input type="number" min={0} max={50} step={0.5} value={form.experience_years} onChange={num('experience_years')} />
            </Field>
            <Field label="Target roles (comma separated)" full>
              <input value={text.roles} onChange={(e) => setText({ ...text, roles: e.target.value })} />
            </Field>
            <Field label="Skills (comma separated — synonyms like Postgres/PostgreSQL are understood)" full>
              <textarea rows={3} value={text.skills} onChange={(e) => setText({ ...text, skills: e.target.value })} />
            </Field>
            <Field label="Preferred locations">
              <input value={text.locations} onChange={(e) => setText({ ...text, locations: e.target.value })} />
            </Field>
            <Field label="Salary expectation">
              <input value={form.salary_expectation} onChange={(e) => setForm({ ...form, salary_expectation: e.target.value })} />
            </Field>
            <label className="field checkbox full">
              <input type="checkbox" checked={form.open_to_remote} onChange={(e) => setForm({ ...form, open_to_remote: e.target.checked })} />
              Open to remote roles
            </label>
          </div>
        </Card>
        <Card title="Weekly goals">
          <div className="form">
            <Field label="Applications per week">
              <input type="number" min={0} value={form.weekly_application_goal} onChange={num('weekly_application_goal')} />
            </Field>
            <Field label="DSA problems per week">
              <input type="number" min={0} value={form.weekly_dsa_goal} onChange={num('weekly_dsa_goal')} />
            </Field>
            <Field label="Recruiter / referral messages per week">
              <input type="number" min={0} value={form.weekly_outreach_goal} onChange={num('weekly_outreach_goal')} />
            </Field>
          </div>
        </Card>
        <div className="actions" style={{ justifyContent: 'flex-end' }}>
          {saved && <span className="tone-muted" style={{ alignSelf: 'center' }}>Saved · matches rescored</span>}
          <button className="btn primary">Save profile</button>
        </div>
      </form>
    </>
  )
}
