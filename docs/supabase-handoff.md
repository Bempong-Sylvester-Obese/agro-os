# Supabase project handoff

## Add collaborators

1. Project owner opens [Supabase Dashboard](https://supabase.com/dashboard) → Project Settings → Team.
2. Invite teammates by email with **Developer** role (schema read + connection strings).

## Link CLI locally

```bash
npm install -g supabase
supabase login
supabase link --project-ref <PROJECT_REF>
```

Copy `DATABASE_URL` from **Project Settings → Database → Connection string (URI)** into `backend/.env`.

## Preview vs production branches

| Environment | Branch | Use |
|---|---|---|
| Local / preview | Supabase dev branch or local Docker | Sandbox Moolre keys |
| Production | Supabase main branch | Live keys, Render production |

## Migrations

```bash
supabase db push          # apply supabase/migrations/*.sql
supabase db reset         # local only — runs migrations + seed.sql
```

Runtime tables are also created by FastAPI `create_all()` until Alembic (#69) fully replaces it.

## Without org owner access

Request `DATABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from the project owner via secure channel. Do not commit credentials.
