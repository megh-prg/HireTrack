import { useState } from 'react'
import { ApiError, api, setToken } from '../api'

export default function Login({ onAuthed }: { onAuthed: (email: string) => void }) {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const fn = mode === 'login' ? api.auth.login : api.auth.signup
      const res = await fn(email.trim(), password)
      setToken(res.token)
      onAuthed(res.email)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 16 }}>
      <div className="card" style={{ width: '100%', maxWidth: 380 }}>
        <div className="brand" style={{ marginBottom: 14 }}>
          HireTrack<small>Job search &amp; interview prep</small>
        </div>
        <h2 style={{ margin: '0 0 4px' }}>{mode === 'login' ? 'Welcome back' : 'Create your account'}</h2>
        <p className="muted small" style={{ marginTop: 0 }}>
          Your jobs, résumé and progress are private to your account.
        </p>
        <form className="form" onSubmit={submit}>
          <label className="field full">
            <span>Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
            />
          </label>
          <label className="field full">
            <span>Password</span>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />
          </label>
          {error && <div className="alert">{error}</div>}
          <button className="btn primary" disabled={busy} style={{ width: '100%', marginTop: 4 }}>
            {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Sign up'}
          </button>
        </form>
        <p className="small muted" style={{ marginTop: 12 }}>
          {mode === 'login' ? "New here? " : 'Already have an account? '}
          <button
            className="btn ghost small"
            type="button"
            onClick={() => {
              setMode(mode === 'login' ? 'signup' : 'login')
              setError(null)
            }}
          >
            {mode === 'login' ? 'Create an account' : 'Sign in'}
          </button>
        </p>
      </div>
    </div>
  )
}
