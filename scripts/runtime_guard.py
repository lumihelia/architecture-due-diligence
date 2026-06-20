#!/usr/bin/env python3
"""Runtime Guard companion for the Architecture Due Diligence skill.

Execution-time guardrails for Claude Code, wired in via hooks
(UserPromptSubmit, PreToolUse, PostToolUse, Stop). See docs/runtime-guard.md.

Design choice: the active mode (audit_read_only / remediation / feature_build)
is set EXPLICITLY by the agent via `set-mode`, never guessed from free-text
prompts. A prompt-text heuristic exists only to remind the agent to set the
mode -- it never blocks or decides anything by itself. This keeps the guard
scoped to sessions that actually opt in, instead of intercepting every prompt
in the project.

Stdlib only. No network calls. No third-party dependencies.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
RULES_PATH = SKILL_DIR / "guard" / "rules.json"

MUTATING_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
VALID_MODES = {"audit_read_only", "remediation", "feature_build", "unknown"}

HOOK_EVENT_ALIASES = {
    "userpromptsubmit": "user-prompt-submit",
    "pretooluse": "pre-tool-use",
    "posttooluse": "post-tool-use",
    "stop": "stop",
}


# --------------------------------------------------------------------------
# Rules / state plumbing
# --------------------------------------------------------------------------

def load_rules() -> dict:
    try:
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        # Fail safe: an unreadable rules file disables enforcement rather
        # than crashing the hook and breaking the user's session.
        return {}


def state_dir(cwd: Path, rules: dict) -> Path:
    return cwd / rules.get("state_dir", ".architecture-due-diligence")


def state_path(cwd: Path, rules: dict) -> Path:
    return state_dir(cwd, rules) / "runtime_guard_state.json"


def default_state() -> dict:
    return {
        "mode": "unknown",
        "changed_files": [],
        "risky_actions": [],
        "verification_commands": [],
        "stop_block_count": 0,
        "last_prompt_summary": "",
        "updated_at": now_iso(),
    }


def load_state(cwd: Path, rules: dict) -> dict:
    path = state_path(cwd, rules)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = default_state()
            merged.update(data if isinstance(data, dict) else {})
            return merged
    except (OSError, json.JSONDecodeError):
        return default_state()


def save_state(cwd: Path, rules: dict, state: dict) -> None:
    path = state_path(cwd, rules)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = now_iso()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except OSError:
        # If we can't persist state, the guard degrades to a no-op rather
        # than crashing the agent's tool call.
        pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Defensive payload extraction (hook JSON shape varies across CC versions)
# --------------------------------------------------------------------------

def read_stdin_json() -> dict:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def get_first(payload: dict, *keys: str):
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def get_tool_name(payload: dict) -> str:
    return get_first(payload, "tool_name", "tool", "toolName") or ""


def get_tool_input(payload: dict) -> dict:
    value = get_first(payload, "tool_input", "input", "toolInput")
    return value if isinstance(value, dict) else {}


def get_bash_command(tool_input: dict) -> str:
    return get_first(tool_input, "command", "cmd") or ""


def get_file_path(tool_input: dict) -> str:
    return get_first(tool_input, "file_path", "path", "notebook_path") or ""


def get_prompt(payload: dict) -> str:
    return get_first(payload, "prompt", "message", "user_prompt") or ""


def get_transcript_path(payload: dict) -> str:
    return get_first(payload, "transcript_path", "transcriptPath") or ""


def get_cwd(payload: dict) -> Path:
    raw = get_first(payload, "cwd", "working_directory") or "."
    return Path(raw).resolve()


def get_event_name(argv: list, payload: dict) -> str:
    if len(argv) > 1 and argv[1]:
        return argv[1].lower()
    raw = (get_first(payload, "hook_event_name", "hookEventName") or "").lower()
    return HOOK_EVENT_ALIASES.get(raw, raw or "unknown")


# --------------------------------------------------------------------------
# Matching helpers (best-effort, not a sandbox -- see docs/runtime-guard.md)
# --------------------------------------------------------------------------

def match_any(text: str, patterns: list) -> str:
    """Return the first pattern found in text (case-insensitive), or ""."""
    lowered = (text or "").lower()
    for pattern in patterns:
        if pattern.lower() in lowered:
            return pattern
    return ""


def path_matches(path: str, patterns: list) -> str:
    if not path:
        return ""
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        if pattern.endswith("/"):
            if f"/{pattern}" in f"/{normalized}" or normalized.startswith(pattern):
                return pattern
        elif normalized == pattern or normalized.endswith(f"/{pattern}") or normalized.endswith(pattern):
            return pattern
    return ""


# --------------------------------------------------------------------------
# Output helpers per Claude Code hook conventions
# Field names are written defensively (both legacy and current keys) because
# hook payload/response shape has changed across Claude Code versions.
# Verify against your installed version if a decision doesn't seem to apply.
# --------------------------------------------------------------------------

def emit(obj: dict) -> None:
    print(json.dumps(obj))


def emit_pretool_decision(event: str, decision: str, reason: str) -> None:
    # decision: "allow" | "ask" | "deny"
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }
    if decision == "deny":
        payload["decision"] = "block"
        payload["reason"] = reason
    emit(payload)


def emit_context(event_name: str, context: str) -> None:
    emit({
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": context,
        }
    })


def emit_stop_block(reason: str) -> None:
    emit({"decision": "block", "reason": reason})


def allow_silently() -> None:
    # No output / exit 0 is treated as "allow, no opinion" by Claude Code.
    sys.exit(0)


# --------------------------------------------------------------------------
# CLI: set-mode / status / reset
# --------------------------------------------------------------------------

def cmd_set_mode(argv: list, rules: dict) -> None:
    if len(argv) < 3 or argv[2] not in VALID_MODES:
        print(f"Usage: runtime_guard.py set-mode <{'|'.join(sorted(VALID_MODES))}>")
        sys.exit(1)
    mode = argv[2]
    cwd = Path.cwd()
    state = default_state()
    state["mode"] = mode
    save_state(cwd, rules, state)
    print(f"runtime guard mode set to: {mode}")


def cmd_status(rules: dict) -> None:
    cwd = Path.cwd()
    state = load_state(cwd, rules)
    print(json.dumps(state, indent=2))


def cmd_reset(rules: dict) -> None:
    cwd = Path.cwd()
    save_state(cwd, rules, default_state())
    print("runtime guard state reset")


# --------------------------------------------------------------------------
# Hook handlers
# --------------------------------------------------------------------------

def handle_user_prompt_submit(payload: dict, rules: dict) -> None:
    cwd = get_cwd(payload)
    state = load_state(cwd, rules)
    prompt = get_prompt(payload)
    state["last_prompt_summary"] = prompt[:200]
    save_state(cwd, rules, state)

    if state["mode"] != "unknown":
        allow_silently()
        return

    hints = rules.get("mode_hint_keywords", {})
    audit_hit = match_any(prompt, hints.get("audit_read_only", []))
    remediation_hit = match_any(prompt, hints.get("remediation", []))

    if audit_hit:
        emit_context(
            "UserPromptSubmit",
            "Reminder (Architecture Due Diligence Runtime Guard): this looks like "
            "an audit request. If you are starting an audit, run "
            "`python3 scripts/runtime_guard.py set-mode audit_read_only` so the "
            "guard can keep this session read-only while you work. This is a "
            "reminder only -- it does not change or block your request.",
        )
        return
    if remediation_hit:
        emit_context(
            "UserPromptSubmit",
            "Reminder (Architecture Due Diligence Runtime Guard): this looks like "
            "a remediation request. If the user explicitly asked you to fix "
            "audit findings, run "
            "`python3 scripts/runtime_guard.py set-mode remediation` so risky "
            "edits get surfaced before they happen. This is a reminder only.",
        )
        return
    allow_silently()


def handle_pre_tool_use(payload: dict, rules: dict) -> None:
    cwd = get_cwd(payload)
    state = load_state(cwd, rules)
    mode = state["mode"]
    tool_name = get_tool_name(payload)
    tool_input = get_tool_input(payload)

    if mode == "audit_read_only":
        mode_rules = rules.get("modes", {}).get("audit_read_only", {})
        if tool_name in mode_rules.get("deny_tools", list(MUTATING_TOOLS)):
            emit_pretool_decision(
                "PreToolUse",
                "deny",
                "Architecture Due Diligence Runtime Guard: session is in "
                "audit_read_only mode. File-mutating tools are blocked during "
                "an audit. Finish the audit, then explicitly ask for "
                "remediation if changes are needed.",
            )
            return
        if tool_name == "Bash":
            command = get_bash_command(tool_input)
            hit = match_any(command, mode_rules.get("deny_bash_patterns", []))
            if hit:
                emit_pretool_decision(
                    "PreToolUse",
                    "deny",
                    f"Architecture Due Diligence Runtime Guard: command matches "
                    f"a blocked pattern ('{hit}') while in audit_read_only mode. "
                    "Audits should not install dependencies, mutate git state, "
                    "or write files.",
                )
                return
        allow_silently()
        return

    if mode == "remediation":
        mode_rules = rules.get("modes", {}).get("remediation", {})
        if tool_name in MUTATING_TOOLS:
            path = get_file_path(tool_input)
            hit = path_matches(path, mode_rules.get("risky_paths", []))
            if hit:
                emit_pretool_decision(
                    "PreToolUse",
                    "ask",
                    f"Architecture Due Diligence Runtime Guard: '{path}' matches "
                    f"a high-risk path ('{hit}'). This can affect dependencies, "
                    "deployment, auth, or schema. Confirm this edit is intended "
                    "before proceeding.",
                )
                return
        if tool_name == "Bash":
            command = get_bash_command(tool_input)
            hit = match_any(command, mode_rules.get("risky_bash_patterns", []))
            if hit:
                emit_pretool_decision(
                    "PreToolUse",
                    "ask",
                    f"Architecture Due Diligence Runtime Guard: command matches "
                    f"a high-risk pattern ('{hit}') during remediation. This can "
                    "add dependencies, rewrite history, or push changes. Confirm "
                    "before proceeding.",
                )
                return
        allow_silently()
        return

    # feature_build / unknown: guard stays invisible.
    allow_silently()


def handle_post_tool_use(payload: dict, rules: dict) -> None:
    cwd = get_cwd(payload)
    state = load_state(cwd, rules)
    mode = state["mode"]
    if mode not in ("audit_read_only", "remediation"):
        allow_silently()
        return

    tool_name = get_tool_name(payload)
    tool_input = get_tool_input(payload)
    changed = False

    if tool_name in MUTATING_TOOLS:
        path = get_file_path(tool_input)
        if path and path not in state["changed_files"]:
            state["changed_files"].append(path)
            changed = True

    if tool_name == "Bash":
        command = get_bash_command(tool_input)
        if match_any(command, rules.get("verification_command_markers", [])):
            if command not in state["verification_commands"]:
                state["verification_commands"].append(command)
                changed = True

    reminder = ""
    path = get_file_path(tool_input) if tool_name in MUTATING_TOOLS else ""
    if path:
        for category, info in rules.get("reminder_categories", {}).items():
            hit = path_matches(path, info.get("paths", []))
            if hit:
                action_key = f"{category}:{path}"
                if action_key not in state["risky_actions"]:
                    state["risky_actions"].append(action_key)
                    reminder = info.get("message", "")
                    changed = True
                break

    if changed:
        save_state(cwd, rules, state)

    if reminder:
        emit_context("PostToolUse", f"Architecture Due Diligence Runtime Guard: {reminder}")
    else:
        allow_silently()


def extract_last_assistant_text(transcript_path: str) -> str:
    if not transcript_path:
        return ""
    try:
        path = Path(transcript_path)
        if not path.exists():
            return ""
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return ""

    for line in reversed(lines[-50:]):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("type") != "assistant":
            continue
        text_parts = []
        message = entry.get("message", {})
        content = message.get("content", [])
        if isinstance(content, str):
            text_parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
        if text_parts:
            return "\n".join(text_parts)
    return ""


def looks_like_completion_summary(text: str, mode: str) -> bool:
    lowered = text.lower()
    has_verified = "verified" in lowered or "verification" in lowered
    has_next = "next" in lowered or "risk" in lowered
    if mode == "remediation":
        return ("changed" in lowered or "modified" in lowered) and has_verified
    return has_verified and has_next


def handle_stop(payload: dict, rules: dict) -> None:
    cwd = get_cwd(payload)
    state = load_state(cwd, rules)
    mode = state["mode"]

    if mode not in ("audit_read_only", "remediation"):
        allow_silently()
        return

    if not state["changed_files"]:
        allow_silently()
        return

    if state["verification_commands"]:
        allow_silently()
        return

    transcript_text = extract_last_assistant_text(get_transcript_path(payload))
    if transcript_text and looks_like_completion_summary(transcript_text, mode):
        allow_silently()
        return

    limit = rules.get("stop_block_limit", 1)
    if state["stop_block_count"] >= limit:
        # Cap reached: fail open so the session can never hang here.
        allow_silently()
        return

    state["stop_block_count"] += 1
    save_state(cwd, rules, state)
    emit_stop_block(
        "Architecture Due Diligence Runtime Guard: files changed in this "
        "session but no verification command was recorded and the final "
        "answer does not clearly state what was verified, what was not, and "
        "the residual risk. Run a relevant verification command, or state "
        "explicitly why none applies, then finish with what changed, what "
        "was verified, what was not, and the recommended next action."
    )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main() -> None:
    argv = sys.argv
    rules = load_rules()

    if len(argv) > 1 and argv[1] == "set-mode":
        cmd_set_mode(argv, rules)
        return
    if len(argv) > 1 and argv[1] == "status":
        cmd_status(rules)
        return
    if len(argv) > 1 and argv[1] == "reset":
        cmd_reset(rules)
        return

    payload = read_stdin_json()
    event = get_event_name(argv, payload)

    handlers = {
        "user-prompt-submit": handle_user_prompt_submit,
        "pre-tool-use": handle_pre_tool_use,
        "post-tool-use": handle_post_tool_use,
        "stop": handle_stop,
    }
    handler = handlers.get(event)
    if handler is None:
        # Unknown event: do nothing rather than guess.
        sys.exit(0)
    handler(payload, rules)


if __name__ == "__main__":
    main()
