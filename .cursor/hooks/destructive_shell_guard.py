#!/usr/bin/env python3
"""beforeShellExecution: prompt user on high-risk shell commands (fail-open on errors)."""
from __future__ import annotations

import json
import re
import sys


def _risk_message(cmd: str) -> str | None:
    c = cmd.strip()
    low = c.lower()

    patterns: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"\bgit\s+push\b.*(\s-f\b|--force)"), "git push --force"),
        (re.compile(r"\bgit\s+reset\s+--hard\b"), "git reset --hard"),
        (re.compile(r"\bgit\s+clean\b.*\s-x"), "git clean … -x (may delete ignored/untracked files)"),
        (re.compile(r"\bgit\s+branch\s+-D\b"), "git branch -D (force delete branch)"),
        (re.compile(r"\bgit\s+push\b\s+origin\s+:"), "git push origin :branch (delete remote branch)"),
        (re.compile(r"\brm\s+(-[a-z]*f[a-z]*\s|\s+-[a-z]*f)"), "rm -rf / destructive rm"),
        (re.compile(r"\bsudo\s+rm\b"), "sudo rm"),
        (re.compile(r"\bdd\s+if="), "dd"),
        (re.compile(r"\bmkfs\b"), "mkfs"),
        (re.compile(r"\bshred\b"), "shred"),
        (re.compile(r"\bcurl\b[^|]*\|\s*(ba)?sh\b"), "curl | sh"),
        (re.compile(r"\bwget\b[^|]*\|\s*(ba)?sh\b"), "wget | sh"),
        (re.compile(r"\bdrop\s+database\b", re.I), "DROP DATABASE"),
        (re.compile(r"\btruncate\s+table\b", re.I), "TRUNCATE TABLE"),
    ]
    for rx, label in patterns:
        if rx.search(low):
            return label
    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"permission": "allow"}))
        return

    cmd = str(payload.get("command") or "")
    hit = _risk_message(cmd)
    if hit:
        print(
            json.dumps(
                {
                    "permission": "ask",
                    "user_message": f"High-risk shell pattern flagged: {hit}. Approve only if you intend this.",
                    "agent_message": "A project hook requested human confirmation before this shell command.",
                }
            )
        )
        return

    print(json.dumps({"permission": "allow"}))


if __name__ == "__main__":
    main()
