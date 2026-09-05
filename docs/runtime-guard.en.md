# Runtime Guard (optional, Claude Code only)

[中文](./runtime-guard.md) · English

Runtime Guard is an optional execution-time companion to Architecture Due Diligence. The skill tells the agent that audits are read-only by default; Runtime Guard adds a second layer through Claude Code hooks and permissions.

It depends on Claude Code-specific host capabilities and is not part of the portable core of the skill.

## What it does

`scripts/runtime_guard.py` is a standard-library-only Python script built around four hook event families:

- `UserPromptSubmit` only reminds the session to set a mode when a prompt resembles audit/remediation work;
- `PreToolUse` reads the explicit mode before a tool call and can allow, ask, or deny;
- `PostToolUse` records changes and verification activity;
- `Stop` can block completion once when files changed without a recorded verification command or a clear verified/not-verified report.

Claude Code hook schemas evolve. The script extracts several legacy/current field names defensively, but every installation should still be checked against current hook payload and response documentation.

## Mode is explicit

```bash
python3 scripts/runtime_guard.py set-mode audit_read_only
python3 scripts/runtime_guard.py set-mode remediation
python3 scripts/runtime_guard.py set-mode feature_build
python3 scripts/runtime_guard.py status
python3 scripts/runtime_guard.py reset
```

Without an explicit mode the state remains `unknown` and the guard is a no-op.

Prompt text can trigger a reminder; it never selects the mode. This avoids locking ordinary work read-only because a prompt happened to contain a word such as “review.”

## `audit_read_only`

This mode is for the audit itself.

Main behavior:

- major file-writing tools such as `Write`, `Edit`, `MultiEdit`, and `NotebookEdit` are denied;
- a short Bash denylist catches dependency installs, dangerous Git operations, migrations, and similar commands;
- reads, search, `git status`, `git diff`, tests, lint, and builds are allowed by default.

Tool-name blocking is stronger than command-string matching. The Bash denylist is only a speed bump.

## `remediation`

Switch only after the user explicitly asks to implement fixes.

Edits are allowed, while two categories can be escalated to human confirmation:

- high-risk paths such as dependency manifests/lockfiles, `.env*`, Docker/deploy/CI config, schema/migrations, and auth-related files;
- high-risk Bash commands such as dependency installs, `git push`, `git reset --hard`, and migrations.

## `feature_build`

Ordinary development mode. Runtime Guard does not extend architecture-audit constraints into unrelated work.

## Stop check

When files changed but no verification command was recorded and the final report does not clearly state verified/not verified, the Stop hook blocks completion once.

It can block only once per mode-session so a misclassification cannot hang the session indefinitely.

This proves only that verification was run or reported. It does not prove the code is correct.

## Installation

1. Open `examples/claude-code/settings.example.json`.
2. Merge its `hooks` block into the project's `.claude/settings.json`; do not overwrite existing settings.
3. Adjust `runtime_guard.py` paths for the actual skill location.
4. Run the appropriate `set-mode` explicitly when an audit/remediation phase starts.
5. Compare the event names, matchers, input fields, and hook output schema with the current Claude Code hooks documentation.

Anthropic currently supports `PreToolUse` hooks that participate in permission evaluation before tool execution, but exact fields and available hook behavior should be verified against the installed Claude Code version.

## Disable

Remove the corresponding hooks from `.claude/settings.json`, or run:

```bash
python3 scripts/runtime_guard.py reset
```

In `unknown` mode the script behaves as a no-op even if the hooks remain configured.

## Limitations

### Not a sandbox

Bash checks use substring matching and can be bypassed by alternate command forms. Runtime Guard reduces a common failure mode—editing while “just auditing”—rather than providing complete isolation.

### Does not prove audit quality

Passing the Stop gate only shows that a verification action exists. Architectural claims still require real repository/runtime evidence and judgment.

### One state file per repository

State defaults to `.architecture-due-diligence/`. Concurrent sessions or worktrees operating on the same repository can race. The current design targets one active session at a time.

### Mode can be forgotten

`unknown` means no enforcement. Runtime Guard is an opt-in backstop, not an automatic security layer.

### Hooks are a host interface

Claude Code evolves continuously. If a hook stops firing, permission decisions stop applying, or payload fields change, compare the configuration against the installed version's documentation before treating it as a Runtime Guard logic bug.
