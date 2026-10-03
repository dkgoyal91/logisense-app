# Beat the Copilot: Day-of-Show Runbook

## The night before
1. `cd frontend && npm install && npm run build`
2. `cd backend && rm -f data/game_snapshot.json`
3. Rehearse with bots (two terminals):
   - `cd backend && GAME_HOST_PIN=rehearsal-pin-1234 ../.venv/bin/python -m uvicorn app.main:app --port 8000`
   - `.venv/bin/python scripts/game_bots.py --bots 300 --pin rehearsal-pin-1234 --drive-host`
   Every phase must reach 300 bots in under 1 s.
4. `rm -f backend/data/game_snapshot.json` again so the real show starts clean.

## On stage (30 minutes before)
1. Start the tunnel: `cloudflared tunnel --url http://localhost:8000`; copy the `https://….trycloudflare.com` URL.
2. Start the backend with that URL and a long PIN only you know (8+ characters, e.g. three random words; the server refuses shorter PINs and locks the host remote for 60 s after 10 wrong guesses):
   `cd backend && GAME_PUBLIC_URL=https://….trycloudflare.com GAME_HOST_PIN=<pin> ../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
3. Projector browser (full screen): `http://localhost:8000/show`
4. Your phone: `https://….trycloudflare.com/host?pin=<pin>`
5. Scan the projector QR with a second phone and check it joins over mobile data.
6. Keep the copilot dashboard at `http://localhost:8000/` in another tab for the live demo.

## Running the show
| Moment | Host remote |
|---|---|
| Story hook, builders paste the prompt | **🏁 Start build race** |
| Round 1 | **Start Round 1** → wait for votes → **Reveal** → **Next** (×5) |
| Round 2 | after Q5 **Next** opens Break It; tap **☆ Star** on the best attacks; **Close attacks** |
| Round 3 | **Show race podium**; fastest builder demos; tap **+500 demo** |
| Bonus (optional) | **Bonus round**; **Ask on screen** on the top question; or **Skip bonus → finale** |
| Finale | **Finale** — the leaderboard counts up and confetti fires |

## If something goes wrong
- **Phones cannot connect** (tunnel down): tap **✋ Hands mode**. Keep driving `/show` and `/host` on localhost; ask for a show of hands, reveal, award prizes by applause.
- **Server restarts**: start it again with the same command; the game resumes from `backend/data/game_snapshot.json` and phones reconnect automatically.
- **Someone posts something rude**: find them under Players on the host remote and tap **Kick** twice.
- **Need a clean slate**: **Reset game**, tapped twice.
