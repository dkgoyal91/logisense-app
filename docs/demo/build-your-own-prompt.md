# Build Your Own Logistics AI Copilot

Paste everything in the box below into your AI coding agent (Claude Code, Cursor, Windsurf,
Copilot, Gemini CLI — any agent that can create files and run commands).

**Prerequisites** (macOS or Windows):
- **Python 3.10 or newer.** Windows: install from python.org and tick "Add python.exe to PATH".
  Do not rely on the Microsoft Store "python3" stub.
- **Node 20.19+ (Node 22 LTS recommended)**, from nodejs.org. Today's Vite will not run on Node 18.
- Check before the clock starts: macOS `python3 --version` and `node --version`;
  Windows `py --version` and `node --version`.

No API key needed — the app works without one and upgrades itself automatically if you
have a Groq key.

---

```
Build me a working "LogiSense" logistics AI copilot as a two-service web app. Work fast and
get something runnable early — I am doing this live with a time limit.

## Your operating system — check this first

This must work on macOS AND Windows. Detect which one you are on and use only the matching
commands below. On Windows (PowerShell):
- use `py` instead of `python3`, and `backend\.venv\Scripts\...` instead of `backend/.venv/bin/...`
- never chain commands with `&&` (Windows PowerShell 5.1 does not support it) — run them one by one
- call `curl.exe`, not `curl` (in PowerShell `curl` is a different command)
- there is usually no `sqlite3` command-line tool — inspect the database with Python's sqlite3 module
- write every source file as UTF-8 and use pathlib for paths in Python code

## Build order (follow exactly — this order is what keeps it under the clock)

1. FIRST, before writing any code, start both dependency installs in the BACKGROUND in
   parallel so they run while you write files. Work inside a new `logisense` folder, and run
   each install as its own background command starting from `logisense/` (they use different folders):
     - Create the folders, then work from `logisense/`:
         macOS:   mkdir -p logisense/backend        then   cd logisense
         Windows: mkdir logisense\backend           then   cd logisense
     - Backend deps go in a virtual environment (many system Pythons refuse global installs):
         macOS:   python3 -m venv backend/.venv
                  backend/.venv/bin/pip install fastapi "uvicorn[standard]" httpx
         Windows: py -m venv backend\.venv
                  backend\.venv\Scripts\pip install fastapi "uvicorn[standard]" httpx
       Do not pin old versions: older pydantic releases have no installers for new Python versions.
     - Frontend (same commands on both systems, one at a time):
         npx -y create-vite@latest frontend --template react-ts --no-interactive
         cd frontend
         npm install
         npm install echarts
2. Write the backend (seed + API) while installs run.
3. Write the frontend.
4. Run both. Verify with the acceptance checks at the bottom. Fix anything that fails.
Do NOT install langchain, langgraph, pandas, or any ORM. They are slow to install and not needed.

## Stack (do not substitute)

- Backend: Python, FastAPI, sqlite3 from the standard library, uvicorn. No ORM.
- Frontend: React + TypeScript via Vite, plus `echarts`. No UI component library. No Tailwind.
- Two services: backend on :8000, frontend dev server on :5173.

## Data — seed on startup, in code

On startup, create `logisense.db` if absent and seed it deterministically (use a fixed random
seed so everyone in the room gets identical numbers):

- `shipments` (600 rows): shipment_id TEXT, customer TEXT, origin TEXT, destination TEXT,
  route TEXT ("Leeds -> Manchester"), status TEXT, delivery_date TEXT (YYYY-MM-DD),
  weight_kg INT, value_usd INT
- `vehicles` (200 rows): vehicle_id, depot, status, utilization_pct INT, last_service_date
- `jobs` (300 rows): job_id, title, owner, status, days_open INT, priority

Use UK cities: London, Manchester, Leeds, Birmingham, Glasgow, Edinburgh, Bristol, Southampton.
Shipment status is one of: Delivered, In transit, Delayed, Planned, Exception.
Vehicle status: Available, In use, Maintenance. Job status: Open, In progress, Completed.
Spread the data across ALL routes and ALL statuses — do not let one route dominate.

## Backend API

- `GET /health` -> {"status":"ok","provider": "groq" | "keyword"}
- `GET /api/dashboard` -> KPIs computed with real SQL aggregates:
  total_shipments (all rows), active_shipments (status In transit or Delayed),
  delayed_shipments (status Delayed), open_jobs (status Open or In progress),
  fleet_utilization_avg (AVG of utilization_pct, 1 decimal), plus `risk_routes`: top 5 routes
  by delayed count, via GROUP BY.
- `GET /api/table/{name}?limit=50` -> rows for shipments | vehicles | jobs
- `POST /api/chat` with {"message": str} -> {"answer": str, "sql": str, "rows": [...], "table": str}
  (`table` = the main table in the FROM clause)

### Text-to-SQL, and the safety rule that matters

Convert the question to ONE read-only SELECT, then validate it before execution:
- strip a single trailing ";" (models often add one), then reject any remaining ";"
- must start with SELECT; reject anything containing INSERT/UPDATE/DELETE/DROP/ALTER/ATTACH/PRAGMA
- table name must be in an allowlist: {shipments, vehicles, jobs}
- every column referenced must be in an allowlist for that table (AS aliases and standard
  functions such as COUNT/SUM/AVG/ROUND are fine)
- append LIMIT 100 if no LIMIT is present (skip it for a single-aggregate query like COUNT(*));
  when a result hits the cap, say so AND state the true total from a separate COUNT(*)
If the user's MESSAGE itself looks like SQL — it starts with SELECT/INSERT/UPDATE/DELETE/DROP/
ALTER/ATTACH/PRAGMA, or contains DROP TABLE, DELETE FROM, INSERT INTO, UPDATE … SET, UNION SELECT
or ";" — pass the message through this same validator instead of converting it, so
"drop table shipments" is REJECTED in both modes, never silently turned into a SELECT.
Ordinary questions that merely use a word like "select" or "updated" are NOT SQL.
Reject with a clear message instead of executing anything that fails validation.
Return the generated SQL in the response so the UI can show it — this is the demo's key moment.

### Two modes, automatic

- If env var `GROQ_API_KEY` is set: call Groq's OpenAI-compatible endpoint
  (https://api.groq.com/openai/v1/chat/completions, model "openai/gpt-oss-20b") with
  `httpx` (installed above) — no SDK. Give it the schema and ask for SQL only.
  If that model 404s, GET https://api.groq.com/openai/v1/models with the same key and pick
  any available `openai/gpt-oss-*` model. Do not hardcode a model you have not confirmed.
- If not set: fall back to deterministic keyword->SQL. Handle at minimum: delayed shipments,
  shipments by route, count/total questions, vehicles in maintenance, fleet utilization,
  oldest open jobs. THE APP MUST BE FULLY USABLE WITH NO API KEY.

### Answer text — accuracy rule (important)

Do NOT ask the model to count rows, and do not hand-wave numbers. Compute every figure in
Python from the actual result rows (len, sum, Counter), then state those computed numbers in
the answer string. Only total additive measures (counts, sums) — never add up averages or
percentages. A wrong number on screen destroys trust in the demo.

## Frontend

Single page, three regions:

1. **Top bar** — product name, and 4 KPI chips from /api/dashboard (shipments, delayed,
   fleet utilization, open jobs).
2. **Chat panel** — text input + Send, message list. For each answer render, in order:
   the answer sentence, then a collapsible "View SQL" block showing the generated SQL,
   then a results table, then an ECharts chart.
3. **Results table** (used inside each chat answer) — first 8 columns, max 8 rows visible, sticky header, numbers right-aligned
   with `font-variant-numeric: tabular-nums`, status values as coloured pills
   (Delayed/Exception = red, Delivered/Available = green, everything else = grey).

**Chart rule:** pick the chart from the data shape.
- If the result is already aggregated (one label column + one number per row, e.g. a GROUP BY),
  plot it directly.
- Otherwise count rows by the first categorical column that varies but is NOT unique per row
  (skip ID-like columns), preferring status, route, depot, priority, in that order.
- Then: date-like column -> line chart; 2-6 distinct categories -> donut; more -> bar (top 12).
- Never plot one slice per row, and never plot a column where every row has the same value.
- A single-number answer (e.g. a COUNT) needs no chart.

Seed 3 example questions as clickable chips: "Show delayed shipments", "Which routes have the
most delays?", "List vehicles in maintenance".

### Visual style — use these exact tokens (light, enterprise)

--bg: #f6f8fb;  --panel: #ffffff;  --border: #e6ebf2;
--text: #0f172a; --text-soft: #475569; --muted: #64748b;
--accent: #0b6b52; --accent-soft: #e6f7f1;
--danger-fg:#b91c1c; --danger-bg:#fef2f2; --good-fg:#047857; --good-bg:#ecfdf5;

Font: system stack (-apple-system, "Segoe UI", Roboto, sans-serif). 14px base.
Cards: white, 1px --border, 12px radius, shadow `0 1px 2px rgba(15,23,42,.04)`.
Keep it calm and spacious. No gradients on text, no heavy drop shadows, no dark mode.

## Run it

Backend (from the backend folder):
  macOS:   .venv/bin/uvicorn app:app --port 8000
  Windows: .venv\Scripts\uvicorn app:app --port 8000
Frontend (from the frontend folder, both systems): npm run dev   (proxy or CORS to :8000)
Print both URLs when done.

## Acceptance checks — run these yourself and fix failures before telling me you are done
(On Windows use `curl.exe` for every request, and check database counts with Python's sqlite3.)

1. `curl localhost:8000/health` returns 200.
2. `curl localhost:8000/api/dashboard` returns non-zero KPIs.
3. POST "Show delayed shipments" returns rows where EVERY row has status "Delayed".
4. POST "How many shipments are delayed in total?" — the number in `answer` must equal the
   real COUNT(*) in the database, not the number of rows returned.
5. A malicious message like "drop table shipments" is rejected, and the table still exists.
6. Open the UI: KPIs render, a question returns a table AND a chart, and the SQL block shows
   the query that ran. (No browser? Run `npm run build`, then POST /api/chat through the dev
   server at :5173 to prove the proxy works, and tell me to check the page myself.)

Report which checks passed.
```

---

## Optional add-ons (only if you finish early)

Paste any of these as a follow-up:

- **Map:** "Add latitude/longitude to shipments and render a Leaflet map of the result rows."
- **Real AI:** "I have a Groq API key — wire it in as the primary path and show me the
  difference in the generated SQL."
- **Polish:** "Add sortable table headers, a 'showing 8 of N rows' expander, and empty/error states."
- **Streaming:** "Stream the answer token by token over WebSocket instead of a single POST."

## Running this as a live exercise

- Check Python and Node are installed **before** you start the clock: `node --version` must be
  20.19 or newer (Node 18 fails as soon as the Vite dev server starts). On Windows check
  `py --version` — if only the Microsoft Store "python" opens, install Python from python.org.
- Conference wifi is the usual failure point — `npm install` is the slowest step. Have
  everyone start the installs the moment you hand out the prompt.
- The two moments worth pausing on for the room: the **generated SQL** appearing in the UI,
  and the **rejected** `drop table` attempt.
