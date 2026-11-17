# Bundle & submit checklist (gta6-twitch-ccu-forecast-01)

Status: entry BUILT and validated. NOT submitted. Submitting needs
Seto's explicit approval per entry in the main chat, plus a public
GitHub repo. Do not submit from this subagent session.

## What is ready

- Entry code: `main.py` (stdlib only), `README.md`, `LICENSE` (MIT),
  `dev/validate.py` + `dev/practice_answers.json`.
- Local git commit: `cbd429bc50b8159d9e7b03a308dfc6e261299ba2`
  (run `git rev-parse HEAD` again at submit time — it changes if
  anything else is committed).
- Local validation: `python3 dev/validate.py` → mean pinball loss
  **0.1876** on the 4 practice cases vs house baseline **0.3871**;
  outputs deterministic (two runs byte-identical), ~0.1 s per case.
- Account: @plucky-owl-46, agent id
  `01a1ea12-642e-76e2-8f85-a1ca9f440a5e`, payout wallet
  `5TxpyvbdBHRgzShZMgGegJuBKdF89xNxK4osPQ45sKk9`. API key in
  `~/.makefun/credentials` (expires 2026-12-17T15:13:56Z). Escrow
  funded: 250 USDC, entries_count 0, entry_fee null.
- Deadline: **2026-11-19T01:00:00Z** (entries close).

## Bundle (transcripts) — must run from the TOP-LEVEL agent

`bundle --dry-run` already passes the run-record check from this
session (2 session files, 1 instruction file, prompt + MCP + system
prompt all resolve). The one thing this subagent cannot do: attach
usage rows. A subagent's usage row is written only once its run
completes, and bundle says to run it from the top-level agent
(agent_id `aacb46b2-a0da-4311-bca1-626080db2d00`) with `--muse-usage`
from the SELECT over its own agent_id plus each subagent's. Without
usage rows the entry is rejected where transcripts are required
(`handed_over_places: none`, so a handed-over bundle would take no
paid place either).

Exact command (from inside the unpacked kit directory):

```sh
node cli/makefun.mjs bundle \
  --repo ~/workspace/makefun/gta6-twitch-ccu-forecast-01 \
  --out ~/workspace/makefun/gta6-twitch-ccu-forecast-01-bundle.tar.gz \
  --session ~/agents/agent-76057740-394d-4ab1-8f63-bb2a0457d8d6/sessions/76057740-394d-4ab1-8f63-bb2a0457d8d6.jsonl \
  --session ~/agents/agent-36b4317b-9f63-47a9-857b-b7097050b73b/sessions/36b4317b-9f63-47a9-857b-b7097050b73b.jsonl \
  --harness Muse --harness-version 1 --provider meta --model muse-spark-1.3 \
  --effort default --mcp none \
  --prompt-file dev/prompt.txt --prompt-origin handed-off \
  --prompt-via "main chat -> parent orchestrator -> builder subagent handoff" \
  --muse-usage <file from the usage SELECT>
```

Notes:

- `--prompt-file dev/prompt.txt` holds Seto's own words that started
  this work, verbatim: "garap semua yg penting free".
- `--harness-version 1` is the value used in the dry run (taken from
  the session file's own `version` field — no separate Muse harness
  version was findable on this machine; confirm/adjust if the
  top-level agent knows better).
- No `--system-prompt` file is needed: the sessions carry the system
  prompt in-session. Instruction files: bundle collects `~/AGENTS.md`
  on its own (1 file).
- After bundling, run `node cli/makefun.mjs check` on the bundle
  before submitting.

## Submit (only with Seto's explicit approval)

1. Create the PUBLIC GitHub repo under Seto's own account, push this
   commit (main.py at the repo root, OSI-approved licence — MIT is
   already in the repo).
2. Submit with repo URL + full commit SHA + the bundle file, via the
   kit CLI / site. Quota: max 10 entries/day, 20 total per account.
3. Never submit from this builder session; never print the API key or
   the keypair contents anywhere.
