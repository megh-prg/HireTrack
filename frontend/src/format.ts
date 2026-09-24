import type { RecruiterStatus, Stage } from './api'

export const STAGES: { value: Stage; label: string }[] = [
  { value: 'saved', label: 'Saved' },
  { value: 'applied', label: 'Applied' },
  { value: 'recruiter_screen', label: 'Recruiter screen' },
  { value: 'assessment', label: 'Assessment' },
  { value: 'technical', label: 'Technical' },
  { value: 'final', label: 'Final round' },
  { value: 'offer', label: 'Offer' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'withdrawn', label: 'Withdrawn' },
]
export const stageLabel = (s: Stage) => STAGES.find((x) => x.value === s)?.label ?? s

export const RECRUITER_STATUSES: { value: RecruiterStatus; label: string }[] = [
  { value: 'to_contact', label: 'To contact' },
  { value: 'contacted', label: 'Contacted' },
  { value: 'replied', label: 'Replied' },
  { value: 'referral_requested', label: 'Referral requested' },
  { value: 'referred', label: 'Referred' },
  { value: 'no_response', label: 'No response' },
]
export const recruiterLabel = (s: RecruiterStatus) => RECRUITER_STATUSES.find((x) => x.value === s)?.label ?? s

export const TRACK_LABELS: Record<string, string> = {
  python: 'Python',
  sql: 'SQL',
  backend: 'Backend',
  genai: 'GenAI',
  'system-design': 'System design',
  dsa: 'DSA',
}

const today = () => {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  return d
}

const parse = (iso: string) => {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return parse(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function relativeDue(iso: string | null | undefined): { text: string; tone: 'danger' | 'warn' | 'muted' } {
  if (!iso) return { text: '—', tone: 'muted' }
  const days = Math.round((parse(iso).getTime() - today().getTime()) / 86_400_000)
  if (days < 0) return { text: `${-days}d overdue`, tone: 'danger' }
  if (days === 0) return { text: 'Today', tone: 'warn' }
  if (days === 1) return { text: 'Tomorrow', tone: 'muted' }
  return { text: `in ${days}d`, tone: 'muted' }
}

export function formatLocation(job: { remote: boolean; location: string }): string {
  if (!job.remote) return job.location || '—'
  return /remote/i.test(job.location) ? job.location : `Remote${job.location ? ` · ${job.location}` : ''}`
}

export const scoreTone = (score: number | null) =>
  score === null ? 'muted' : score >= 70 ? 'good' : score >= 45 ? 'warn' : 'danger'

/** YYYY-MM-DD in the user's local timezone (the API stores plain dates). */
export function localToday(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export const pct = (done: number, total: number) => (total ? Math.round((done / total) * 100) : 0)
