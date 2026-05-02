#!/usr/bin/env python3
"""afterShellExecution: append command metadata to a local audit log (no stdout bodies)."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone


def main() -> None:
    log_path = os.path.join(".cursor", "agent-shell-audit.log")
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("{}")
        return

    cmd = str(payload.get("command") or "")[:800]
    duration = payload.get("duration")
    sandbox = payload.get("sandbox")
    cwd = str(payload.get("cwd") or "")[:500]

    os.makedirs(".cursor", exist_ok=True)
    line = json.dumps(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "cwd": cwd,
            "command": cmd,
            "duration_ms": duration,
            "sandbox": sandbox,
        },
        ensure_ascii=False,
    )
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

    print("{}")


if __name__ == "__main__":
    main()
