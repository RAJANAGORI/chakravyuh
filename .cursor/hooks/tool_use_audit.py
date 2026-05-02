#!/usr/bin/env python3
"""postToolUse: log tool name and non-sensitive parameters only (never file contents or shell output)."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone


def _safe_summary(tool_name: str, tool_input: object) -> dict[str, object]:
    if not isinstance(tool_input, dict):
        return {"tool_input_type": type(tool_input).__name__}

    ti = tool_input
    name = tool_name or ""

    if name == "Read":
        return {"path": ti.get("path") or ti.get("target_file") or ti.get("file_path")}
    if name in ("Write", "StrReplace", "Delete"):
        return {"path": ti.get("path") or ti.get("file_path") or ti.get("target_file")}
    if name == "Glob":
        return {
            "glob_pattern": (str(ti.get("glob_pattern") or ti.get("pattern") or ""))[:300],
            "target_directory": (str(ti.get("target_directory") or ""))[:300],
        }
    if name == "Grep":
        return {
            "pattern": (str(ti.get("pattern") or ""))[:200],
            "path": (str(ti.get("path") or ""))[:300],
        }
    if name == "Shell":
        cmd = str(ti.get("command") or "")
        return {"command": cmd[:400]}
    if name == "SemanticSearch":
        return {"query": (str(ti.get("query") or ""))[:200]}
    if name == "Task":
        return {"description": (str(ti.get("description") or ""))[:200]}

    allowed = {k: ti[k] for k in list(ti)[:8] if k in ("path", "file_path", "target_file", "command", "pattern")}
    return {k: (str(v)[:300] if isinstance(v, str) else v) for k, v in allowed.items()}


def main() -> None:
    log_path = os.path.join(".cursor", "agent-tool-audit.log")
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("{}")
        return

    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input")
    duration = payload.get("duration")
    cwd = str(payload.get("cwd") or "")[:500]

    os.makedirs(".cursor", exist_ok=True)
    line = json.dumps(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool_name": tool_name,
            "safe_input": _safe_summary(tool_name, tool_input),
            "duration_ms": duration,
            "cwd": cwd,
        },
        ensure_ascii=False,
    )
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

    print("{}")


if __name__ == "__main__":
    main()
