# LogiSense @ Flo 2026 — Walkthrough Video Script

Voice: Siri "Tara" (English, India). Target length: about 7 minutes.
Slides come from `LogiSense_Flo2026_Session_v2.pptx`; footage is recorded from the local app.
Each scene's narration is one block; the renderer voices each block separately and fits the visuals to it.

---

## S01 · Title — slide 1
Welcome to Build a Logistics AI Copilot, a hands-on session at Flo 2026, on the ninth of October, from four to five p.m., presented by Rachit Singhal, with Dinesh Kumar, Sunil Gupta, Gaurav Tyagi and Punhik Gandhi from Nagarro. This walkthrough shows you everything we will do in the room.

## S02 · The problem — slide 2
Let's start with the problem. It's Monday, eight a.m. An operations lead asks a simple question: why are Leeds deliveries late? That question becomes a ticket, and the ticket joins a queue of fourteen other data requests. Tuesday and Wednesday pass while it waits for an analyst who is free to write the SQL. On Thursday at eleven, a spreadsheet finally arrives. Five minutes later, the truck has already left. Three days, for an answer the database could have given in milliseconds. The data was never the problem. Getting to it was.

## S03 · Meet LogiSense — slide 3
Meet LogiSense. You ask in plain English. It writes validated SQL, runs it against your own data, and gives you real rows and a chart. It is read-only, and every answer is grounded in what is actually in the database.

## S04 · Beat the Copilot — slide 4, then lobby footage
And because this is a big room, we are not just going to show you. You are going to play. Beat the Copilot is a live game. Scan the QR code, pick a nickname, and you are in. No app, no login. There are three rounds: predict the copilot, break it, and a build race. Prizes go to the top predictor, the best hacker, and the fastest builder.

## S05 · Live demo — slide 5, then copilot footage
Here is the copilot in action. We ask: show delayed shipments by delivery date. Open show thinking, and you can see every step. The router matched the question to the approved data model, and the SQL agent ran a validated, read-only query that returned twenty records. The summary is computed from those rows, and one click turns them into a chart. Now let's be mischievous, and ask it to drop table shipments. It doesn't argue, and it doesn't comply. It never runs what you type. It answers with a safe, pre-written query, and the table is still there.

## S06 · Round 1, Predict the Copilot — game footage
That is exactly what round one is about. The room sees the question the copilot is about to receive, like, which work orders have been open longest, and has twenty seconds to predict which table it will query. Fast, correct answers score the most. Then we reveal the real result: the live SQL, the rows, and the leaderboard.

## S07 · How it works — slide 6
Under the hood, it is deliberately simple. A router picks the table. Text to SQL drafts one SELECT. A validator checks it. SQLite executes it, read-only, and the answer is built from the returned rows. FastAPI and SQLite on one side, React and TypeScript on the other. No warehouse, no vector store. The whole thing runs on a laptop.

## S08 · The guardrail — slide 7
Every query passes a guardrail before it runs. It must be a single SELECT. The table, and every column, must be on an allowlist, and a row cap is applied automatically. Anything else is refused, not executed.

## S09 · Round 2, Break It — game footage
In round two, the audience gets to attack. Prompt injections, drop table, union selects against the system tables. They all stream onto the big screen, each one labelled with the safety layer that stopped it. And if someone finds a genuine gap in the validator, they win best hacker. Nothing is ever executed, so it is safe to learn from.

## S10 · The hard part — slide 8
The hard part isn't the SQL. It's making the numbers true. Ask a model to count twenty rows, and it will confidently say three. So we don't let it count. Totals are computed in code from the returned rows, and the model only writes the sentence around them.

## S11 · Your turn — slide 9
Then it's your turn. Open any AI coding agent, paste our prompt, and build your own copilot in fifteen minutes. It works with no API key. Python and Node are the only prerequisites. The build race clock starts the moment you paste.

## S12 · What you'll have — slide 10, then race podium footage
You will leave with a running two-service app: a seeded logistics database, chat to SQL to table and chart, a KPI dashboard, and the SQL guard, working. When you are done, tap I'm done on your phone. The fastest builders take the podium, and show their copilot on the big screen.

## S13 · Show and tell — slide 11
Then we compare notes. Who got a chart? Who broke it in an interesting way? Who got a wrong number, and why? The failures are the most useful part of the session.

## S14 · Takeaways — slide 12, then finale footage
Five takeaways. Text to SQL is the easy half. Trust is the hard half. Validate the query, never the intent. Compute numbers in code, and let the model do language. Show the SQL, because people believe what they can inspect. And a laptop-sized demo beats a slide about a platform. Then the final leaderboard counts down, and the confetti flies.

## S15 · Thank you — slide 13
Thank you. The prompt, the repo, and these slides are yours to take away. See you at Flo 2026: area six point zero two N, on the ninth of October, at four p.m.
