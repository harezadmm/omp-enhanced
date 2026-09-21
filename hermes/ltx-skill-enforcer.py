#!/usr/bin/env python3
"""
LTX-QUASAR skill-load enforcer (Hermes shell hook: pre_tool_call).
Blocks terminal/browser/exec tool calls until the agent has read a matching
skill file in this task. Enforces the persona's PRIORITIZE SKILL CALLING rule
at the harness level — text instructions alone get skipped.

Strategy:
- Track per-session whether a skill read has happened (state file keyed by session_id).
- On pre_tool_call for terminal/browser_exec/execute_code:
    * If a skill read already happened this session -> allow (exit 0, empty stdout).
    * If not -> block with a directive message telling the agent to read the
      matching skill file first. The agent retries the tool after reading.
- The "skill read happened" flag is set by a companion pre_tool_call matcher
  on read_file / fetch paths under skills/ (registered separately) — OR we
  simply allow the FIRST tool call of any session and rely on the message to
  nudge. Simpler + robust: block the first N terminal calls per session until
  a read of skills/ is observed.

This file is the block-side hook. The allow-side is implicit: any read of a
path containing "skills/" flips the session flag via the state file written
here.
"""
import json, os, sys, re
from pathlib import Path

STATE_DIR = Path.home() / ".hermes" / "ltx-hook-state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

# tool calls that count as "the agent actually doing work on target" — gate these
GATED_TOOLS = {"terminal", "browser_exec", "execute_code", "computer_use", "shell"}
# a tool call that reads a skill file flips the flag
SKILL_READ_RE = re.compile(r"skills/", re.IGNORECASE)

def state_path(session_id: str) -> Path:
    return STATE_DIR / f"{session_id or 'default'}.json"

def load_state(session_id: str) -> dict:
    p = state_path(session_id)
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        return {}

def save_state(session_id: str, st: dict) -> None:
    try:
        state_path(session_id).write_text(json.dumps(st))
    except Exception:
        pass

def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {}
    event = payload.get("hook_event_name", "")
    tool = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    session_id = payload.get("session_id") or "default"

    st = load_state(session_id)
    st.setdefault("skill_reads", 0)
    st.setdefault("gated_calls", 0)

    # If this tool call is a read of a skills/ path, count it and allow.
    blob = json.dumps(tool_input, default=str)
    if SKILL_READ_RE.search(blob):
        st["skill_reads"] += 1
        save_state(session_id, st)
        sys.stdout.write("")  # allow
        return 0

    # Gate terminal/browser/exec calls
    if tool in GATED_TOOLS:
        st["gated_calls"] += 1
        # Allow if agent has already read a skill file this session.
        if st["skill_reads"] > 0:
            save_state(session_id, st)
            sys.stdout.write("")
            return 0
        # Otherwise block with directive. Let the first gated call through
        # after the agent has been nudged twice (avoid hard-loop on benign
        # sessions like "hello"); but keep blocking substantive recon calls.
        msg = (
            "LTX-QUASAR ENFORCER: Before running terminal/browser commands on a "
            "security task, you MUST first read the matching skill file from "
            "skills/ (see SKILLS_INDEX.md / the auto-trigger map in SOUL.md). "
            "No skill file read yet this session. Action: open the relevant "
            "skills/impl/<name>/SKILL.md (and companion SCENARIOS/ADVANCED "
            "files), read it, THEN retry this tool call. This is a harness-level "
            "enforcement of PRIORITIZE SKILL CALLING — not optional."
        )
        save_state(session_id, st)
        # Claude-Code-style block via exit 2 + stderr
        sys.stderr.write(msg + "\n")
        sys.stdout.write(json.dumps({"decision": "block", "reason": msg}))
        return 2

    # Non-gated tool: allow silently
    save_state(session_id, st)
    sys.stdout.write("")
    return 0

if __name__ == "__main__":
    sys.exit(main())
