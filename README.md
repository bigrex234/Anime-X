# AnimeX — Mega Update (Stages 3–7)

AnimeX is a Flask anime discovery application with AniList metadata, an optional Jikan-compatible adapter, Supabase Auth, user-owned watchlists, recent history, airing schedules and a curated rights-cleared downloads catalogue.

## Included
- Stage 2 retained: trending, popular, top-rated, upcoming, genre filters, search and anime details.
- Stage 3: email/password registration and login through Supabase Auth; private library, favourites, watch status, episode progress and recently viewed.
- Stage 4: seasonal catalogue and AniList airing schedule where supplied by AniList.
- Stage 5: trailer links, external official-provider discovery can be added, and an approved-download catalogue. AnimeX intentionally does not scrape or host unauthorised episodes.
- Stage 6: API validation, security response headers, RLS, bounded request values, server-side access-token verification.
- Stage 7: Vercel-ready Flask app and Supabase PostgreSQL schema.

## Local setup
1. Create a Supabase project.
2. In Supabase SQL Editor, run `supabase/schema.sql`.
3. Copy `.env.example` to `.env` and set:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY` (publishable/anon public key)
   - `SECRET_KEY` (generate a long random value)
4. Install and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open `http://127.0.0.1:5000`.

## Supabase Auth setup
In Supabase Dashboard:
1. Authentication → Providers → Email: enable Email.
2. Authentication → URL Configuration:
   - Site URL: your Vercel production URL (after first deployment).
   - Add redirect URLs for `http://127.0.0.1:5000/**`, your Vercel preview URL(s), and production URL.
3. For production, keep email confirmation enabled if you want verified email addresses. Signup will ask the user to confirm email before they can sign in.

The browser receives only the public publishable/anon key. The server verifies access tokens with Supabase Auth and forwards user JWTs to PostgREST. Row Level Security limits each user's data to their own `auth.uid()`.

## Deploy to Vercel
1. Push the project to a private or public GitHub repository.
2. In Vercel, Add New → Project → import the repository.
3. Framework should be detected as Flask. Keep the project root as the repository root.
4. Add these Environment Variables for Production and Preview as appropriate:
   - `APP_NAME=AnimeX`
   - `SECRET_KEY` = long random secret
   - `ANILIST_GRAPHQL_URL=https://graphql.anilist.co`
   - `SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co`
   - `SUPABASE_ANON_KEY=YOUR_PUBLIC_PUBLISHABLE_OR_ANON_KEY`
   - `API_TIMEOUT=20`
   - `FLASK_DEBUG=false`
   - `JIKAN_COMPATIBLE_BASE_URL` (leave blank unless you have a trusted compatible service)
5. Deploy.
6. Copy the Vercel production URL into Supabase Authentication → URL Configuration → Site URL and add it to Redirect URLs.
7. Redeploy if you changed Vercel environment variables.

Vercel supports zero-configuration Flask deployments by detecting the top-level `app` instance in `app.py`. `vercel.json` sets Flask framework metadata and excludes development-only files.

## Vercel CLI alternative
```bash
npm install -g vercel
vercel login
vercel
# Configure project and environment variables when prompted / in dashboard.
vercel --prod
```

## Test after deployment
- `/api/health` should show `status: ok` and `supabase_configured: true`.
- `/api/anime/trending`
- `/api/anime/search?q=naruto`
- `/api/seasonal`
- `/login`: create an account, confirm email if enabled, then sign in.
- `/library`: confirm signed-in library loads.
- Open an anime detail page, save it, change status/progress, and verify it appears in `/library`.
- Sign out and confirm `/library` sends you back to `/login`.
- Create a second test account and confirm it cannot see the first account's saved titles.

## Environment variable security
- Never commit `.env`.
- Never put `SUPABASE_SERVICE_ROLE_KEY` in browser code or Vercel public-prefixed variables.
- This release does not need a service-role key for library operations.
- The Supabase publishable/anon key is designed to be public, but database access must remain protected by RLS.

## Data and content limitations
- AniList supplies metadata and airing schedule data, not playable full episodes.
- Episode schedule data is not the same as a complete historical episode catalogue.
- The downloads list is empty until an administrator inserts assets with explicit distribution rights into `public.downloadable_assets`.
- This build does not implement arbitrary video uploads, torrenting, or scraping of unlicensed streams.
- Official provider links should be added only after verifying regional availability and provider URLs.

## Important Vercel deployment note
The Flask app is compatible with Vercel's Python runtime. Vercel is serverless: local filesystem writes are ephemeral, so user data belongs in Supabase, not SQLite or local files.
