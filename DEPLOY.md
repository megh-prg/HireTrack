# Deploying HireTrack (Career Copilot)

Three free services: **Render** (backend + Postgres), **Vercel** (frontend), and a
**Gemini API key** (for the AI resume rewrite). ~15 minutes.

## 1. Backend + database on Render
1. Go to <https://render.com> and sign up (use "Sign in with GitHub").
2. Click **New +** -> **Blueprint**, pick the **HireTrack** repo, and approve.
   Render reads `render.yaml` and creates a Postgres database + the API service.
3. When it finishes, open the **hiretrack-api** service -> **Environment** and add:
   - `GEMINI_API_KEY` = your Gemini key (from `elevatecv-ai/backend/.env`, or
     <https://aistudio.google.com/apikey>)
   - `CORS_ORIGINS` = your Vercel URL — you'll have this after step 2 below, so
     come back and fill it in then.
4. Note your backend URL, e.g. `https://hiretrack-api.onrender.com`.
   Open `<that URL>/api/health` — it should say `{"status":"ok"}`.

## 2. Frontend on Vercel
1. Go to <https://vercel.com> and sign up with GitHub.
2. **Add New -> Project**, import the **HireTrack** repo.
3. Set **Root Directory** to `frontend`.
4. Under **Environment Variables**, add:
   - `VITE_API_URL` = your Render backend URL (from step 1.4)
5. Click **Deploy**. Note your site URL, e.g. `https://hiretrack.vercel.app`.

## 3. Connect them
Back in Render (step 1.3), set `CORS_ORIGINS` to your Vercel URL and save — the
API redeploys. Open your Vercel URL and you're live.

## Notes
- **Free backend sleeps** after ~15 min idle, so the first request after a nap
  takes ~50 seconds to wake. Normal for the free tier.
- **Free Postgres on Render expires after 30 days.** For something permanent,
  swap in a free [Neon](https://neon.tech) database: create one, copy its
  connection string, and set it as `DATABASE_URL` on the Render service instead.
- Without `GEMINI_API_KEY` the app still scores resumes and lists missing
  keywords; the AI rewrite just stays off.
