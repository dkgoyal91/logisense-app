# Beat the Copilot — Interactive Workshop Game Design

Date: 2026-10-03
Status: Draft for review

## 1. Intent

**Goal:** make the 45-minute Flo workshop the session people talk about afterwards ("that was a show"),
by turning the LogiSense copilot demo into a live game the audience plays against the product.

**What the presenter said:**
- The room is mixed: some attendees build along on laptops, the rest join from phones.
- The priority outcome is wow factor / a high-energy game-like experience.
- A few days of build time are available.
- Chosen direction: approach A, "Beat the Copilot" (live game layer on the existing app).

**Assumptions (confirm before the event):**
- Audience of up to ~300 concurrent players.
- The presenter's laptop runs the app; it has internet (venue Wi-Fi or phone hotspot).
- Attendees need no API keys. A Groq key on the presenter's machine is optional and only enables the bonus round.

**Success criteria:**
- Every attendee with a phone can join in under 30 seconds by scanning a QR code.
- Every scored moment works with no LLM and no API key.
- The show can continue (degraded) if phones cannot connect at all.
- A 300-bot rehearsal runs a full game with no dropped state.

## 2. Run-of-show (45 minutes)

The build race runs in the background for the whole session; builders code while phone rounds play.

| Time | Segment | Description |
|---|---|---|
| Pre-start | Lobby | Projector shows a large QR code; joining nicknames animate onto the screen with a live count. |
| 0:00–0:04 | Cold open + race start | Story hook ("7am, London deliveries are failing…"). Builders paste `docs/demo/build-your-own-prompt.md`; a race clock starts and stays in the projector corner. |
| 0:04–0:16 | Round 1: Predict the Copilot | 5 scripted questions, ~2 min each. 20 s phone vote (4 options) → live answer-distribution bars → presenter asks the copilot for real → answer, SQL, chart revealed → points. |
| 0:16–0:26 | Round 2: Break It | 3 min free-text attack window. Attacks stream onto the projector labelled with the guard layer that stopped them. Presenter reads highlights and explains guardrails. |
| 0:26–0:34 | Round 3: Build race finish | Builders tap "I'm done"; podium fills by finish time. Fastest builder demos on the big screen. |
| 0:34–0:39 | Bonus: Ask Anything (optional) | Only with a Groq key and working connectivity. Phones submit and upvote questions; top 2–3 go to the copilot live. Otherwise this time extends Round 2. |
| 0:39–0:45 | Finale | Leaderboard countdown 10 → 1, confetti, three prizes, closing QR to the build prompt. |

The presenter drives every transition from the host remote; nothing advances automatically.

## 3. Game mechanics

### 3.1 Screens

| Screen | Path | User | Purpose |
|---|---|---|---|
| Projector | `/show` | Room | Large, high-contrast, animated view of the current state |
| Player | `/play` | Each attendee | Join, answer, attack, finish, see rank |
| Host remote | `/host?pin=<PIN>` | Presenter | Next / Reveal / Skip / Kick / Star attack; phone-friendly |

### 3.2 Game states

`lobby → question_open(n) → question_revealed(n) → … (n = 1..5) → break_it_open → break_it_closed
→ race_podium → bonus (optional) → finale`

The build race is not a state; the "I'm done" action is accepted in any state after race start until `finale`.

Host actions: `start_race`, `next`, `reveal`, `skip`, `kick(player_id)`, `star_attack(attack_id)`, `reset` (confirm twice).

### 3.3 Player phone view per state

| State | Phone shows |
|---|---|
| lobby | "You're in, <name>! Watch the big screen." |
| question_open | 4 large coloured answer buttons + countdown |
| question_revealed | Correct/incorrect, points earned, current rank |
| break_it_open | Text box + Send; own attempts with their verdict |
| any (after race start, builders) | "I'm done!" button — single tap, then locked |
| finale | Final rank; confetti if top 3 in any category |

### 3.4 Scoring

| Event | Points |
|---|---|
| Correct prediction | `1000 − round(500 × elapsed / window)` (500–1000) |
| Streak (3rd+ consecutive correct) | +200 per answer |
| Attack submitted | +50 each, max 5 counted per player |
| Host-starred "Best Attack" | +1000 |
| Race finish | 1st +3000, 2nd +2000, 3rd +1000, other finishers +500 |
| Demo on big screen | +500 (host-awarded) |

Category boards are computed separately:
- **Top Predictor** — Round 1 points (incl. streaks)
- **Best Hacker** — Round 2 points
- **Fastest Builder** — earliest race finish

The **overall leaderboard** is the sum, so a phone-only player can still win overall.
Race finishes use the honour system; the on-stage demo keeps the winner honest.

### 3.5 Round 1 questions

Five scripted questions; **correct answers and distractors are computed from the live database at
startup**, never hard-coded, so they always match the seeded data. Each teaches one concept.

| # | Question | Answer source | Concept taught |
|---|---|---|---|
| 1 | How many shipments are currently delayed? | `COUNT(*) WHERE status='Delayed'`; distractors ±15–40% | Text → SQL |
| 2 | Which route has the most delays? | Top 4 routes by delayed count; #1 correct | GROUP BY aggregation |
| 3 | Which depot has the most vehicles in maintenance? | Top 4 depots | Filtering + grouping |
| 4 | What is the average fleet utilisation? | `AVG(utilization_pct)` rounded; distractors ±5–15 pts | Aggregates the model must not guess |
| 5 | What chart will the copilot draw for "delays by route"? | Mirror of `chartPlan.ts`: ≤6 distinct routes → donut, else bar (currently 6 → donut). Options: bar, donut, line, table | Chart choice from data shape |

Distractors must be unique and differ from the correct answer. Option order is shuffled with a fixed
seed per question so all phones show the same order.

### 3.6 Round 2 guard classification

The copilot never executes user-written SQL: `execute_safe_query` maps a question to a pre-written
template, then `_validate_sql` checks it. Each attack is classified (never executed) by the first
layer that stops it:

1. **Scope guard** — `detect_table_from_message` finds no approved table → "Outside approved data".
2. **No raw SQL** — the attack contains SQL-like text; label "Copilot only runs pre-written queries".
3. **Validator** — if the attack contains SQL-like text, also run `_validate_sql` on it and show its
   message (e.g. "Unsafe SQL detected.").
4. Otherwise → "Answered safely" (it was just a question).

Known gap, owned openly on stage: `_validate_sql` is regex-based and checks only the first `FROM`.
An attack the validator would pass is shown as **"Found a gap!"** — a Best Hacker candidate. Nothing is
executed, so this is harmless.

### 3.7 Fairness and safety

- Nicknames: trimmed, 2–20 characters, basic profanity word list, de-duplicated with a numeric suffix.
- Attack text: max 200 characters; rendered as escaped plain text only (never as HTML).
- Rate limits: one answer per question per player; at most one attack per 3 seconds per player.
- The host can kick a player (removed from boards, phone shows "Removed by host").
- Reconnect: the phone stores a player token in `localStorage`; on reconnect the server restores the
  player and score.
- The host PIN is generated at startup and printed to the console; host WebSocket requires it.

## 4. Architecture

### 4.1 Backend — `backend/app/game/`

Self-contained package, wired in with one `app.include_router(game_router)` line in `main.py`.
No new Python dependencies.

| Module | Responsibility |
|---|---|
| `models.py` | Dataclasses: `Player`, `Answer`, `Attack`, `GameState` |
| `engine.py` | Pure state transitions: `apply(state, action) -> state`. No I/O |
| `scoring.py` | Point rules from §3.4 and category board computation |
| `questions.py` | Builds the 5 questions with answers/distractors from the DB at startup |
| `guard.py` | Attack classification from §3.6, reusing `detect_table_from_message` and `_validate_sql` |
| `views.py` | Projects `GameState` into role-specific payloads (show / play / host) |
| `hub.py` | WebSocket connection registry and per-role broadcast |
| `persistence.py` | Writes a JSON snapshot after each state change; loads it at startup to resume |
| `routes.py` | `WS /ws/game/show`, `WS /ws/game/play`, `WS /ws/game/host?pin=` |

State is in memory in a single process (one event at a time). Every mutation goes through
`engine.apply`, then `persistence.save`, then `hub.broadcast`.

### 4.2 Message protocol (JSON over WebSocket)

Client → server: `{"type": "join", "name", "token?"}`, `{"type": "answer", "question", "option"}`,
`{"type": "attack", "text"}`, `{"type": "race_done"}`, host: `{"type": "host", "action", ...}`.

Server → client: `{"type": "state", "view": {...}}` — the full role-specific view on every change
(views are small, so there is no diffing). Errors: `{"type": "error", "message"}`.

### 4.3 Frontend — `frontend/src/game/`

- `main.tsx` selects the root by `location.pathname`: `/show`, `/play`, `/host`, otherwise the existing `App`.
  `App.tsx` is not modified.
- `useGameSocket(role)` — connects, auto-reconnects with backoff, exposes the latest view and a `send` function.
- `ShowScreen`, `PlayScreen`, `HostScreen` — each composes small per-state components
  (e.g. `LobbyWall`, `QuestionCard`, `AnswerBars`, `AttackFeed`, `RaceClock`, `Podium`, `Leaderboard`).
- New dependencies: `qrcode` (QR generated locally) and `canvas-confetti`.
- Projector styling follows the Nagarro/Flo palette in `docs/END_TO_END_APPROACH.md` (dark navy, teal accents).
  Phone styling: large tap targets, readable in a bright room.

### 4.4 Single-origin serving

For the event, run `vite build` and have FastAPI serve `frontend/dist` (with an SPA fallback for
`/show`, `/play`, `/host`) on port 8000. Phones then need one URL, and the tunnel exposes one port.
The Vite dev server stays the development workflow; add a `/ws` and `/api` proxy to `vite.config.ts`.

## 5. Connectivity plan

- **Primary:** `cloudflared tunnel --url http://localhost:8000` produces a public HTTPS URL; the
  projector encodes it in the QR code. Phones can join over mobile data, independent of venue Wi-Fi.
  The laptop uses venue Wi-Fi, with a phone hotspot as backup.
- **Fallback:** if the tunnel is down, `/show` and `/host` keep working on localhost. The host remote
  offers "show of hands" mode: questions and reveals still run; scores are skipped; prizes go by applause.
- The public URL is configured via an env var (`GAME_PUBLIC_URL`) so the QR code is correct.

## 6. Error handling

- Malformed or out-of-state client messages → `error` reply; state unchanged.
- WebSocket send failures → connection dropped from the hub; the client reconnects.
- Process restart → state restored from the latest snapshot; clients reconnect and re-sync.
- Question generation failure at startup (e.g. empty DB) → fail fast with a clear console message
  during rehearsal, never silently mid-show.

## 7. Testing

- **Unit (pytest):** `engine` transitions (including invalid actions), `scoring` formulas and streaks,
  `guard` classification for a corpus of benign, out-of-scope, SQL-injection and gap-finding inputs,
  `questions` generation against the seeded DB (unique options, correct answer present).
- **Integration:** FastAPI `TestClient` WebSocket test: host + 3 players play through a full game.
- **Load rehearsal:** `scripts/game_bots.py` spawns ~300 bot players that join, answer and attack,
  driven by a scripted host; verify broadcast latency and that the final leaderboard matches.
- **Manual dress rehearsal:** real phones on mobile data through the tunnel, projector on a second screen.

## 8. Out of scope

- Accounts, persistence beyond the single event, multiple simultaneous games.
- Automated verification of build-race finishes.
- Changes to the existing copilot behaviour or `App.tsx`.
- Fixing the `_validate_sql` gap before the event (it is a deliberate stage moment; a follow-up ticket
  can harden it afterwards).
