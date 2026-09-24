export type Stage =
  | 'saved'
  | 'applied'
  | 'recruiter_screen'
  | 'assessment'
  | 'technical'
  | 'final'
  | 'offer'
  | 'rejected'
  | 'withdrawn'

export type RecruiterStatus =
  | 'to_contact'
  | 'contacted'
  | 'replied'
  | 'referral_requested'
  | 'referred'
  | 'no_response'

export type Difficulty = 'easy' | 'medium' | 'hard'
export type PracticeStatus = 'todo' | 'attempted' | 'solved' | 'mastered'
export type Track = 'python' | 'sql' | 'backend' | 'genai' | 'system-design'

export interface Profile {
  name: string
  target_roles: string[]
  locations: string[]
  open_to_remote: boolean
  skills: string[]
  experience_years: number
  salary_expectation: string
  weekly_application_goal: number
  weekly_dsa_goal: number
  weekly_outreach_goal: number
}

export interface Job {
  id: number
  title: string
  company: string
  location: string
  remote: boolean
  salary: string
  url: string
  description: string
  skills: string[]
  source: string
  posted_at: string | null
  created_at: string
  archived: boolean
  match_score: number | null
  matched_skills: string[]
  missing_skills: string[]
  application_id: number | null
  application_stage: Stage | null
}

export interface JobInput {
  title: string
  company: string
  location?: string
  remote?: boolean
  salary?: string
  url?: string
  description?: string
}

export interface IngestResult {
  created: number
  duplicates: number
  created_ids: number[]
}

export interface Analysis {
  score: number
  skills: string[]
  matched_skills: string[]
  missing_skills: string[]
  reasons: string[]
}

export interface SkillGap {
  skill: string
  jobs: number
  track: string | null
}

export interface Application {
  id: number
  stage: Stage
  applied_on: string | null
  next_follow_up: string | null
  referral: boolean
  notes: string
  created_at: string
  updated_at: string
  job: Pick<Job, 'id' | 'title' | 'company' | 'location' | 'remote' | 'salary' | 'url' | 'match_score'>
  events: { from_stage: Stage | null; to_stage: Stage; at: string }[]
}

export interface Recruiter {
  id: number
  name: string
  company: string
  title: string
  email: string
  linkedin_url: string
  status: RecruiterStatus
  last_contacted: string | null
  next_follow_up: string | null
  notes: string
  created_at: string
}

export interface DSAProblem {
  id: number
  title: string
  url: string
  topic: string
  difficulty: Difficulty
  notes: string
  status: PracticeStatus
  attempts: number
  review_streak: number
  last_practiced: string | null
  next_review: string | null
}

export interface PrepQuestion {
  id: number
  track: Track
  question: string
  answer: string
  tags: string[]
  source: string
  confidence: number
  review_streak: number
  last_reviewed: string | null
  next_review: string | null
}

export interface TrackSummary {
  track: Track
  total: number
  reviewed: number
  due: number
  mastery: number
}

export interface FollowUp {
  kind: 'application' | 'recruiter' | 'dsa' | 'prep'
  id: number
  title: string
  subtitle: string
  due: string
  overdue_days: number
}

export interface Progress {
  totals: Record<string, number>
  funnel: { stage: Stage; count: number }[]
  response_rate: number
  interview_rate: number
  weekly_goals: { label: string; done: number; goal: number }[]
  applications_per_week: { week: string; count: number }[]
  dsa_by_difficulty: { difficulty: Difficulty; total: number; solved: number }[]
  dsa_by_topic: { topic: string; total: number; solved: number }[]
  prep_tracks: TrackSummary[]
  practice_streak_days: number
  skill_gaps: SkillGap[]
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

const BASE = import.meta.env.VITE_API_URL ?? ''

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = init.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' }
  const res = await fetch(`${BASE}${path}`, { ...init, headers: { ...headers, ...init.headers } })
  if (!res.ok) {
    let message = res.statusText
    try {
      const body = await res.json()
      message = typeof body.detail === 'string' ? body.detail : body.detail?.[0]?.msg ?? message
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, message)
  }
  return (res.status === 204 ? undefined : await res.json()) as T
}

const qs = (params: Record<string, string | number | boolean | undefined | null>) => {
  const search = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== '') search.set(k, String(v))
  const s = search.toString()
  return s ? `?${s}` : ''
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
})

export const api = {
  profile: {
    get: () => request<Profile>('/api/profile'),
    save: (p: Profile) => request<Profile>('/api/profile', json('PUT', p)),
  },
  jobs: {
    list: (p: { q?: string; source?: string; sort?: 'newest' | 'score'; untracked?: boolean } = {}) =>
      request<Job[]>(`/api/jobs${qs(p)}`),
    create: (j: JobInput) => request<Job>('/api/jobs', json('POST', j)),
    update: (id: number, j: Partial<JobInput> & { archived?: boolean }) =>
      request<Job>(`/api/jobs/${id}`, json('PATCH', j)),
    remove: (id: number) => request<void>(`/api/jobs/${id}`, json('DELETE')),
    upload: (file: File) => {
      const body = new FormData()
      body.append('file', file)
      return request<IngestResult>('/api/jobs/upload', { method: 'POST', body })
    },
    ingestRemotive: (search: string, limit: number) =>
      request<IngestResult>('/api/jobs/ingest/remotive', json('POST', { search, limit })),
  },
  matching: {
    top: (minScore: number, includeTracked = false) =>
      request<Job[]>(`/api/matching${qs({ min_score: minScore, include_tracked: includeTracked })}`),
    analyze: (body: { title: string; description: string; location: string }) =>
      request<Analysis>('/api/matching/analyze', json('POST', body)),
    gaps: () => request<SkillGap[]>('/api/matching/skill-gaps'),
    recompute: () => request<{ rescored: number }>('/api/matching/recompute', json('POST')),
  },
  applications: {
    list: () => request<Application[]>('/api/applications'),
    create: (body: { job_id?: number; job?: JobInput; stage?: Stage; notes?: string; referral?: boolean }) =>
      request<Application>('/api/applications', json('POST', body)),
    update: (id: number, body: Partial<Pick<Application, 'stage' | 'next_follow_up' | 'notes' | 'referral'>>) =>
      request<Application>(`/api/applications/${id}`, json('PATCH', body)),
    remove: (id: number) => request<void>(`/api/applications/${id}`, json('DELETE')),
  },
  recruiters: {
    list: () => request<Recruiter[]>('/api/recruiters'),
    create: (body: Partial<Recruiter> & { name: string }) => request<Recruiter>('/api/recruiters', json('POST', body)),
    update: (id: number, body: Partial<Recruiter>) => request<Recruiter>(`/api/recruiters/${id}`, json('PATCH', body)),
    remove: (id: number) => request<void>(`/api/recruiters/${id}`, json('DELETE')),
  },
  dsa: {
    list: () => request<DSAProblem[]>('/api/dsa'),
    create: (body: { title: string; topic: string; difficulty: Difficulty; url?: string }) =>
      request<DSAProblem>('/api/dsa', json('POST', body)),
    update: (id: number, body: Partial<DSAProblem>) => request<DSAProblem>(`/api/dsa/${id}`, json('PATCH', body)),
    practice: (id: number, quality: number, minutes?: number) =>
      request<DSAProblem>(`/api/dsa/${id}/practice`, json('POST', { quality, minutes })),
  },
  prep: {
    tracks: () => request<TrackSummary[]>('/api/prep/tracks'),
    questions: (p: { track?: Track; due?: boolean } = {}) => request<PrepQuestion[]>(`/api/prep/questions${qs(p)}`),
    recommended: (limit = 10) => request<PrepQuestion[]>(`/api/prep/recommended${qs({ limit })}`),
    create: (body: { track: Track; question: string; answer?: string }) =>
      request<PrepQuestion>('/api/prep/questions', json('POST', body)),
    update: (id: number, body: Partial<Pick<PrepQuestion, 'question' | 'answer'>>) =>
      request<PrepQuestion>(`/api/prep/questions/${id}`, json('PATCH', body)),
    review: (id: number, quality: number) =>
      request<PrepQuestion>(`/api/prep/questions/${id}/review`, json('POST', { quality })),
  },
  followups: {
    list: (horizonDays = 7) => request<FollowUp[]>(`/api/followups${qs({ horizon_days: horizonDays })}`),
    complete: (kind: 'application' | 'recruiter', id: number, rescheduleDays?: number) =>
      request<void>(`/api/followups/${kind}/${id}/complete`, json('POST', { reschedule_days: rescheduleDays ?? null })),
  },
  progress: () => request<Progress>('/api/progress'),
}
