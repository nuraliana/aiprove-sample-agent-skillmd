"""Sample AIProve agent — reads skill.md, authenticates with its own keypair,
lists open bounties, and enters one. Full loop, exactly as
https://aiprove.fun/skill.md prescribes.

Identity = an Ethereum-style address. The private key is NEVER hard-coded:
it is read from the AGENT_PRIVATE_KEY environment variable, or from the file
named by AGENT_KEY_FILE (default: ~/.pg/agent.key). The session token is
never printed; logs only record that a token was received.

HTTP goes through `curl` (subprocess) with a browser User-Agent: plain
Python urllib against aiprove.fun is blocked (403/timeouts).

Usage:
    export AGENT_PRIVATE_KEY=0x...          # or AGENT_KEY_FILE=~/.pg/agent.key
    python3 agent.py [--enter sample-agent-skillmd] [--handle nuraliana-ana]

Requires: python3, curl, eth-account (pip install eth-account).
"""

import json
import os
import subprocess
import sys

API_BASE = os.environ.get("API_BASE_URL", "https://aiprove.fun")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
HANDLE = os.environ.get("AGENT_HANDLE", "nuraliana-ana")
TARGET_BOUNTY = os.environ.get("TARGET_BOUNTY", "sample-agent-skillmd")


def log(msg):
    print(f"[agent] {msg}", flush=True)


def curl_json(method, path, data=None, token=None, raw=False):
    """One HTTP call via curl. Returns (status_code, parsed_json_or_text)."""
    url = API_BASE + path if path.startswith("/") else path
    cmd = ["curl", "-s", "-A", UA, "-X", method, url,
           "-w", "\nHTTP_CODE:%{http_code}"]
    if data is not None:
        cmd += ["-H", "content-type: application/json", "-d", json.dumps(data)]
    if token:
        cmd += ["-H", "Authorization: Bearer " + token]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    txt = out.stdout
    code = txt.rsplit("HTTP_CODE:", 1)[-1].strip() if "HTTP_CODE:" in txt else "?"
    body = txt.rsplit("HTTP_CODE:", 1)[0].strip()
    if raw:
        return (int(code) if code.isdigit() else 0), body
    try:
        return (int(code) if code.isdigit() else 0), json.loads(body) if body else {}
    except Exception:
        return (int(code) if code.isdigit() else 0), {"_raw": body[:500]}


def load_keypair():
    """Private key from env or file; returns (address, Account). Never logs the key."""
    from eth_account import Account
    pk = os.environ.get("AGENT_PRIVATE_KEY", "").strip()
    if not pk:
        key_file = os.path.expanduser(
            os.environ.get("AGENT_KEY_FILE", "~/.pg/agent.key"))
        with open(key_file) as f:
            pk = f.read().strip()
    acct = Account.from_key(pk)
    return acct.address, acct


def authenticate(address, acct):
    from eth_account.messages import encode_defunct
    code, chal = curl_json("GET", f"/api/auth/challenge?address={address}")
    if code != 200 or "challenge" not in chal:
        raise SystemExit(f"challenge failed: HTTP {code} {str(chal)[:300]}")
    log(f"challenge received ({len(chal['challenge'])} chars)")
    sig = "0x" + acct.sign_message(
        encode_defunct(text=chal["challenge"])).signature.hex()
    code, ver = curl_json("POST", "/api/auth/verify",
                          {"address": address, "signature": sig})
    if code != 200 or not ver.get("token"):
        raise SystemExit(f"verify failed: HTTP {code} {str(ver)[:300]}")
    log(f"authenticated as {ver.get('address', address)}; session token received")
    return ver["token"]


def main():
    target = TARGET_BOUNTY
    if "--enter" in sys.argv:
        target = sys.argv[sys.argv.index("--enter") + 1]

    # 1. Read skill.md (the agent's instructions, fetched live).
    code, skill = curl_json("GET", "/skill.md", raw=True)
    if code != 200 or "Authenticate" not in skill:
        raise SystemExit(f"skill.md fetch failed: HTTP {code}")
    log(f"skill.md read OK ({len(skill)} chars, {skill.count(chr(10))} lines)")

    # 2. Health check.
    code, health = curl_json("GET", "/api/health")
    log(f"health: HTTP {code} {str(health)[:200]}")

    # 3. Authenticate with own keypair.
    address, acct = load_keypair()
    log(f"agent address: {address}")
    token = authenticate(address, acct)

    # 4. List open bounties.
    code, data = curl_json("GET", "/api/bounties?status=open")
    bounties = data if isinstance(data, list) else data.get("bounties", [])
    log(f"open bounties: {len(bounties)}")
    for b in bounties:
        log(f"  - {b.get('slug')} [{b.get('cat')}/{b.get('lane')}] "
            f"{b.get('title', '')[:60]}")

    # 5. Enter one bounty (free in beta).
    code, entered = curl_json("POST", f"/api/bounties/{target}/enter",
                              {"handle": HANDLE}, token=token)
    log(f"enter {target}: HTTP {code} {str(entered)[:300]}")
    if code not in (200, 201):
        raise SystemExit(f"enter failed: HTTP {code}")

    # 6. Verify via /api/me that the entry is recorded.
    code, me = curl_json("GET", "/api/me", token=token)
    competing = me.get("competing") or me.get("entries") or []
    log(f"/api/me: HTTP {code}; competing/entries: {json.dumps(competing)[:500]}")
    slugs = [e.get("bountySlug") or e.get("slug") for e in competing
             if isinstance(e, dict)]
    if target in slugs or target in json.dumps(me):
        log(f"VERIFIED: entry for '{target}' recorded in /api/me")
    else:
        log(f"WARNING: '{target}' not found in /api/me payload; "
            f"full payload keys: {sorted(me.keys()) if isinstance(me, dict) else type(me)}")
    log("LOOP COMPLETE")


if __name__ == "__main__":
    main()
