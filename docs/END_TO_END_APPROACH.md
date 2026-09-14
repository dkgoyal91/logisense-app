# End-to-End Approach for the LogiSense Copilot Demo

## 1. Product goal
Build a senior-quality logistics AI copilot experience inspired by the CBRE-style assistant pattern: a right-side floating chatbot panel, a polished enterprise dashboard, and a realistic workflow that feels like a business tool rather than a toy demo.

The visual direction should use the Nagarro or FLO aesthetic instead of the CBRE brand and green palette. The default visual language should be:
- dark navy / blue background
- teal or cyan accents
- muted white/gray text
- soft purple or magenta gradients for richer hero surfaces
- clean rounded cards and low-contrast borders

The assistant should sit on the right side of the application, with a compact icon and a wide conversation panel. It must remain readable, polished, and credible for a 45-minute session.

## 2. Demo architecture
The app will have three clear layers:

### Frontend
- React + TypeScript + Vite
- dashboard shell for logistics KPIs and tables
- right-side floating chat panel
- WebSocket-driven streaming UX
- enterprise-style layout and typography

### Backend
- Python 3.12
- FastAPI
- WebSocket endpoint for chat
- safe SQL generation module
- validated SQLite access layer
- structured summary generation

### Data layer
- SQLite database initialized locally at startup
- realistic logistics tables with 200+ rows
- tables such as shipments, warehouses, routes, delays, customers, and opportunities

## 3. End-to-end runtime flow
1. User enters a natural-language prompt such as:
   - “Show opportunities with industrial properties in Birmingham”
   - “What are the top 3 banking clients within London?”
   - “Summarize opportunities open in 2025 Q2 by asset type”

2. The frontend sends the prompt over WebSocket to the backend.

3. The backend validates the incoming prompt and routes it to a query-intent layer.

4. The query-intent layer maps the natural-language request to an approved set of allowed tables and columns.

5. A safe SQL-generation module builds a read-only SQL statement based on the schema allowlist.

6. The backend executes the SQL against SQLite with strict safeguards:
   - read-only execution
   - row caps
   - execution timeout
   - allowlisted tables and fields only
   - no DDL/DCL/DML from user input

7. Results are returned as structured data.

8. The result is rendered in the chat panel and/or dashboard table area.

9. A summary agent translates the raw rows into business-friendly insight language.

10. The frontend displays:
   - answer card
   - table output
   - summary bullets
   - suggested prompts / next actions

## 4. UI pattern inspired by the CBRE assistant design
We will not use the CBRE brand, green palette, or name. Instead, we will re-create the same interaction pattern with a local product identity:

- floating assistant on the right side
- small circular icon with a clean stylized mark
- rounded chat bubble with business-friendly message output
- compact prompt tray at the bottom
- “Suggested prompts” row beneath the result
- polished enterprise dashboard background behind the assistant

The cluster should feel like a premium enterprise AI workspace, with the assistant acting like an internal copilot, not a consumer chat widget.

## 5. Recommended styling direction
Use a Nagarro/FLO-inspired palette:
- deep navy base
- blue-violet gradients
- teal highlights
- white and light gray text
- soft translucent cards

Avoid:
- bright green as the dominant accent
- CBRE naming text or branding
- heavy consumer-chat styling

## 6. Single-script startup model
To keep the demo easy to run on both Windows and Mac, we will use a single command wrapper that always does a clean start.

### Required behavior
- stop existing containers/processes before starting
- remove orphaned containers
- rebuild containers if code changed
- start the app as a background service
- print the URL and logs for quick verification

### Command pattern
```bash
./scripts/manage_app.sh start
./scripts/manage_app.sh stop
./scripts/manage_app.sh restart
```

This script will perform the following lifecycle behavior:
- `docker compose down --remove-orphans --volumes` on restart/start
- `docker compose up --build -d`
- `docker compose ps`
- optional log tail for quick local debugging

## 7. Docker strategy
For Windows, use Docker Desktop with WSL2 backend. For Mac, use Docker Desktop or any supported Docker runtime. The app will be designed to run locally with Docker Compose so there is no messy manual service orchestration.

The goal is a single script that works consistently across local developer machines without requiring a complex environment setup.

## 8. Security and AI safety requirements
This is a production-style demo, so safety remains mandatory.

- natural-language queries must map to allowed tables and columns only
- raw SQL from the browser is prohibited
- only read-only SQL is allowed
- row caps enforced on all queries
- no direct execution of DDL/DCL or write operations
- prompt injection attempts must be rejected or neutralized
- returned summaries must be grounded in real query outputs

## 9. Data model expectation
The local SQLite DB should contain realistic logistics or property-related records. The dataset must be large enough to demonstrate a real business dashboard and a credible AI workflow.

Recommended table set:
- opportunities
- clients
- salesforce
- warehouses
- routes
- deal status
- performance metrics

Minimum realistic target: 200+ rows in the main tables.

## 10. Execution plan
### Phase 1: scaffold and governance
- create repo structure
- add Copilot rule files
- define architecture and quality expectations

### Phase 2: backend and SQLite seed
- define DB schema
- seed test data
- implement safe query layer and WebSocket API

### Phase 3: frontend dashboard and assistant UI
- build dashboard shell
- create floating assistant styling
- implement prompt, result, and summary components

### Phase 4: integration and verification
- connect frontend to backend via WebSocket
- validate sample prompts
- verify summarization and result rendering
- verify app startup via single script

### Phase 5: session polish
- tune the look for Nagarro/FLO aesthetics
- ensure the demo is understandable in 45 minutes
- remove rough edges and inject a strong business narrative

## 11. Recommended next implementation step
The next work item is to scaffold the application skeleton and then implement the following in sequence:
1. single Docker Compose startup
2. SQLite seed script and schema
3. backend WebSocket API
4. safe SQL generation layer
5. frontend dashboard + RHS assistant
6. smoke tests for end-to-end prompt execution

## 12. Final expectation
The delivered demo should feel like a premium internal copilot for a logistics or enterprise operations domain, with a polished right-side assistant, live data results, and real-time business summarization.

The key story remains: ask a question in natural language, convert it to safe SQL, inspect the data, and convert the output into a business decision.
