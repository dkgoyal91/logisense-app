# LogiSense AI Copilot Demo

This project is a phased implementation of a logistics AI assistant built with:

- React + TypeScript frontend
- Python 3.12 + FastAPI backend
- SQLite local database
- WebSocket-driven chat flow
- secure, read-only text-to-SQL pattern

## Phase 1 goals
- working dashboard shell
- right-side floating AI assistant inspired by enterprise productivity tools
- local SQLite with realistic demo data
- backend health and chat endpoints
- single script to start and stop the app

## What is included now
- Logistics operations layout with KPI cards, route risk radar, and live query table
- Real chatbot data flow: chat request -> validated SQL -> row results shown in UI
- Seeded logistics dataset above 400 rows (opportunities, jobs, shipments, vehicles)
- Team workflow script for 5 parallel member instances

## Environment configuration

Create a local `.env` file from `.env.example` and keep API keys out of source control.

```bash
cp .env.example .env
```

Update the following values as needed:
- `AI_PROVIDER` = `groq` or `gemini`
- `GROQ_API_KEY` if using Groq
- `GEMINI_API_KEY` if using Gemini
- `ENABLE_EXTERNAL_AI` = `true` only when you want live provider calls
- `ROW_LIMIT` controls max rows returned per chat query (default 50)
- `BACKEND_PORT` and `FRONTEND_PORT` can be set for parallel local runs

The backend also includes a backend-local example at `backend/.env.example`.

## Run locally

### Start
```bash
./scripts/manage_app.sh start
```

### Stop
```bash
./scripts/manage_app.sh stop
```

### Restart
```bash
./scripts/manage_app.sh restart
```

## Access
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

## Team mode (5 members)

Initialize member-specific env files:

```bash
chmod +x scripts/team_demo.sh
./scripts/team_demo.sh init
```

Start one member instance (example member3):

```bash
./scripts/team_demo.sh start member3
```

Stop a member instance:

```bash
./scripts/team_demo.sh stop member3
```

Reseed a member database:

```bash
./scripts/team_demo.sh reseed member3
```

## Design direction
This demo uses a Nagarro/FLO-style visual direction:

- dark blue / navy base
- teal and cyan highlights
- soft purple and magenta accents
- polished enterprise dashboard patterns
- right-side AI assistant card

## Safety model
- only read-only SQL is allowed
- tables and columns are validated against an allowlist
- row caps and timeout controls apply
- all payloads are treated as untrusted input

## Notes
This is a progressive implementation. The first phase establishes a credible foundation and a working UI flow for a 45-minute demo session.
