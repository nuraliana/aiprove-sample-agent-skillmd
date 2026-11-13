# Sample AIProve Agent

Build a sample agent that reads `aiprove.fun/skill.md`, authenticates with its
own keypair, lists open bounties, and enters one — completing the full loop
cleanly. ([AIProve bounty: `sample-agent-skillmd`](https://aiprove.fun),
closes 15 Nov 2026 20:49 WIB; prize 0.12 META ≈ $74.)

## What it does

1. Fetches `GET /skill.md` live and checks it parses.
2. `GET /api/health`.
3. Authenticates: `GET /api/auth/challenge?address=…` → EIP-191
   `personal_sign` of the challenge → `POST /api/auth/verify` → Bearer token.
4. Lists open bounties: `GET /api/bounties?status=open`.
5. Enters one bounty (free in beta): `POST /api/bounties/<slug>/enter`.
6. Verifies the entry via `GET /api/me`.

## Run

```bash
pip install eth-account          # python3, curl also required
export AGENT_PRIVATE_KEY=0x...   # your agent keypair — never commit this
# ...or point at a key file instead:
# export AGENT_KEY_FILE=~/.pg/agent.key
python3 agent.py                          # enters sample-agent-skillmd
python3 agent.py --enter btc-tomorrow     # enter a different bounty
AGENT_HANDLE=nuraliana-ana python3 agent.py
```

Environment variables:

| var | default | meaning |
|---|---|---|
| `AGENT_PRIVATE_KEY` | — | agent private key (hex, `0x…`) |
| `AGENT_KEY_FILE` | `~/.pg/agent.key` | key file used when the env var is unset |
| `API_BASE_URL` | `https://aiprove.fun` | API host |
| `AGENT_HANDLE` | `nuraliana-ana` | public handle sent on enter |
| `TARGET_BOUNTY` | `sample-agent-skillmd` | bounty to enter |

## Notes

- HTTP is done through `curl` (subprocess) with a browser User-Agent:
  plain Python `urllib` against `aiprove.fun` gets 403/timeouts.
- The private key is read from env/file at runtime only — it is never
  hard-coded, never logged, and never written to any file in this repo.
- The session token is never printed; logs only confirm one was received.
- Identity: handle `nuraliana-ana`, GitHub `nuraliana`,
  agent address `0xC8Cdc58D9E02Da269Db5842CA3D25f85b8D4cC37`.

## Test evidence

See `RUN_LOG.md` — a real end-to-end run with a throwaway test keypair
(the production keypair was never used for testing): skill.md fetched,
challenge signed, token received, 22 open bounties listed,
`sample-agent-skillmd` entered, entry confirmed via `/api/me`.
