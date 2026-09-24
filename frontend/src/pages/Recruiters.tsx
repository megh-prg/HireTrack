import { useState } from 'react'
import { api, type Recruiter, type RecruiterStatus } from '../api'
import { Card, Empty, Field, Modal, PageHeader, Status } from '../components/ui'
import { formatDate, RECRUITER_STATUSES, relativeDue } from '../format'
import { useApi } from '../hooks'

const BLANK = { name: '', company: '', title: '', email: '', linkedin_url: '', status: 'to_contact' as RecruiterStatus, notes: '' }

export default function Recruiters() {
  const { data, error, loading, reload } = useApi(() => api.recruiters.list())
  const [editing, setEditing] = useState<Partial<Recruiter> | null>(null)

  const update = async (r: Recruiter, body: Partial<Recruiter>) => {
    await api.recruiters.update(r.id, body)
    reload()
  }

  return (
    <>
      <PageHeader
        title="Recruiters & referrals"
        subtitle="Changing status to Contacted or Referral requested schedules a follow-up 5 days later."
        actions={
          <button className="btn primary" onClick={() => setEditing(BLANK)}>
            + Add contact
          </button>
        }
      />
      <Card>
        <Status loading={loading && !data} error={error} />
        {data && data.length === 0 && <Empty>No contacts yet. Aim for 5–10 targeted messages a week.</Empty>}
        {data && data.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Contact</th>
                  <th>Status</th>
                  <th className="hide-sm">Last contacted</th>
                  <th>Follow up</th>
                  <th className="hide-sm">Links</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.map((r) => {
                  const due = relativeDue(r.next_follow_up)
                  return (
                    <tr key={r.id}>
                      <td className="title-cell">
                        <b>{r.name}</b>
                        <span>{[r.title, r.company].filter(Boolean).join(' · ')}</span>
                      </td>
                      <td>
                        <select value={r.status} onChange={(e) => update(r, { status: e.target.value as RecruiterStatus })} aria-label="Status">
                          {RECRUITER_STATUSES.map((s) => (
                            <option key={s.value} value={s.value}>
                              {s.label}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="hide-sm">{formatDate(r.last_contacted)}</td>
                      <td className={`tone-${due.tone}`}>{due.text}</td>
                      <td className="hide-sm">
                        {r.email && <a href={`mailto:${r.email}`}>Email</a>} {r.linkedin_url && <a href={r.linkedin_url} target="_blank" rel="noreferrer">LinkedIn</a>}
                      </td>
                      <td>
                        <button className="btn small" onClick={() => setEditing(r)}>
                          Edit
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {editing && (
        <RecruiterForm
          initial={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null)
            reload()
          }}
        />
      )}
    </>
  )
}

function RecruiterForm({ initial, onClose, onSaved }: { initial: Partial<Recruiter>; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ ...BLANK, ...initial, next_follow_up: initial.next_follow_up ?? '' })
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: e.target.value })

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const body = {
      name: form.name,
      company: form.company,
      title: form.title,
      email: form.email,
      linkedin_url: form.linkedin_url,
      status: form.status,
      notes: form.notes,
      ...(form.next_follow_up ? { next_follow_up: form.next_follow_up } : {}),
    }
    if (initial.id) await api.recruiters.update(initial.id, body)
    else await api.recruiters.create(body)
    onSaved()
  }
  const remove = async () => {
    if (initial.id && confirm(`Delete ${initial.name}?`)) {
      await api.recruiters.remove(initial.id)
      onSaved()
    }
  }

  return (
    <Modal title={initial.id ? 'Edit contact' : 'Add contact'} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <Field label="Name *">
          <input required value={form.name} onChange={set('name')} />
        </Field>
        <Field label="Company">
          <input value={form.company} onChange={set('company')} />
        </Field>
        <Field label="Title">
          <input value={form.title} onChange={set('title')} placeholder="Talent Partner, EM…" />
        </Field>
        <Field label="Status">
          <select value={form.status} onChange={set('status')}>
            {RECRUITER_STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Email">
          <input type="email" value={form.email} onChange={set('email')} />
        </Field>
        <Field label="LinkedIn URL">
          <input type="url" value={form.linkedin_url} onChange={set('linkedin_url')} />
        </Field>
        <Field label="Next follow-up">
          <input type="date" value={form.next_follow_up} onChange={set('next_follow_up')} />
        </Field>
        <Field label="Notes" full>
          <textarea rows={3} value={form.notes} onChange={set('notes')} />
        </Field>
        <div className="form-actions">
          {initial.id && (
            <button type="button" className="btn danger" onClick={remove} style={{ marginRight: 'auto' }}>
              Delete
            </button>
          )}
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary">Save</button>
        </div>
      </form>
    </Modal>
  )
}
