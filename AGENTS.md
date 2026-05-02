# Agent and automation guardrails (Chakravyuh)

This document maps **known weak spots** of AI-assisted coding to **concrete controls** in this repository. It is the human-readable companion to `.cursor/rules/` and `.cursor/hooks/`.

## 1. Instruction conflicts

When system instructions, project rules, `AGENTS.md`, and a casual chat line disagree:

| Priority | Source |
|----------|--------|
| 1 | Explicit **user** instruction in the current turn (if unambiguous) |
| 2 | **Safety** (no secrets in chat, no destructive git without confirmation) |
| 3 | **This file** and **`.cursor/rules/*.mdc`** |
| 4 | General best practices |

If two instructions still conflict, **stop and ask the user** instead of guessing.

## 2. Partial context

- Do not claim a file’s behavior without **reading** it (or running a targeted search).
- For large or unfamiliar areas, **narrow the scope** (one module, one API) before asserting.
- Prefer **evidence** (paths, command output) over memory.

## 3. Verification gaps

After non-trivial changes, run checks **from the repo root** when possible:

| Area | Command |
|------|---------|
| Frontend (lint, types, build) | `npm run ci` |
| Backend tests | `cd backend && make test` (uses `backend/venv/bin/python` when present; otherwise ensure `pip install -r requirements.txt` for that interpreter) |
| Full local gate | `npm run verify` |

CI mirrors Node and Python versions (see `.github/workflows/ci.yml`). If local Node/Python differ from those files, fix the environment before trusting “green here.”

## 4. Secrets and sensitive data

- **Never** commit `backend/.env`, `frontend/.env.local`, or real API keys. Templates: `backend/.env.example`.
- **Do not** paste secrets into chat, PR descriptions, or hook audit logs.
- `.cursorignore` reduces accidental indexing of env files; it is not a substitute for correct `.gitignore` and review.

## 5. Tool and environment mismatch

Canonical versions:

- **Node:** `.nvmrc` at repo root; `frontend/package.json` `engines.node`.
- **Python:** `backend/.python-version` (use `pyenv` or your toolchain to match).

If CI fails locally, compare versions first, then dependency lockfiles.

## 6. Destructive actions (git / data)

Project hook **`beforeShellExecution`** prompts for confirmation on high-risk shell patterns (force push, hard reset, dangerous `rm`, etc.). **Review** before approving.

**Database migrations:** follow `backend/migrations/README.md`. Do not apply ad-hoc `DROP` / destructive SQL without explicit user approval and a backup story.

## 7. Audit trail (local)

Hooks append **metadata only** (no terminal bodies, no file contents) to:

- `.cursor/agent-shell-audit.log` — shell commands and duration
- `.cursor/agent-tool-audit.log` — tool name and safe parameters (e.g. paths, truncated commands)

These files are **gitignored**. They are for local accountability, not a full compliance system.

## 8. Human-in-the-loop

- Destructive git and risky shell: **hook asks**; you approve in the UI.
- Production deploys and schema-destroying changes: **require explicit human intent**; agents must not infer permission from silence.

---

For Cursor hook behavior and troubleshooting, see [Hooks | Cursor Docs](https://cursor.com/docs/agent/hooks).
