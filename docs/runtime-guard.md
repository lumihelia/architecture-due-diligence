# Runtime Guard (optional, Claude Code only)

Runtime Guard is an optional companion to the Architecture Due Diligence
skill. The skill itself works in any agent (Claude Code, Cursor, Windsurf,
Codex) because it is just instructions. Runtime Guard adds an execution-time
layer that only Claude Code can run, because it relies on Claude Code's
hooks system.

## What it is

A small, dependency-free Python script (`scripts/runtime_guard.py`) wired
into four Claude Code hooks:

- `UserPromptSubmit` — reminds you (and the agent) to set a mode explicitly when a prompt looks like an audit or remediation request. It never blocks or changes your prompt.
- `PreToolUse` — checks the active mode before a tool runs.
- `PostToolUse` — records what changed and adds short reminders for high-risk areas (auth, dependencies, deployment, migrations).
- `Stop` — before the agent ends its turn, checks that changes were verified or that the final answer says clearly what was and wasn't verified.

## How it differs from the skill itself

The skill's "Read-Only Default" rule (in `SKILL.md`) is a written instruction
the agent is expected to follow. Runtime Guard makes one part of that
instruction enforced rather than self-reported: while the guard is in
`audit_read_only` mode, Claude Code's own permission system — not the
agent's judgment — blocks file-writing tools.

## Mode is explicit, not guessed

Earlier drafts of this idea tried to infer "are we auditing right now" from
the wording of every prompt. That was rejected: a keyword match on any
message (e.g. the word "review") would lock the whole project read-only,
even for unrelated work. Instead:

```bash
python3 scripts/runtime_guard.py set-mode audit_read_only   # before an audit
python3 scripts/runtime_guard.py set-mode remediation        # only after you explicitly ask for fixes
python3 scripts/runtime_guard.py set-mode feature_build       # normal work -- guard stays out of the way
python3 scripts/runtime_guard.py status                       # see current mode and recorded activity
python3 scripts/runtime_guard.py reset                        # clear state back to "unknown"
```

If mode is never set, it stays `unknown` and the guard does nothing. The
`UserPromptSubmit` hook only ever sends a reminder to set the mode — it
cannot set it for you and cannot block your message.

## What it blocks in `audit_read_only` mode

- `Write`, `Edit`, `MultiEdit`, `NotebookEdit` — denied outright. This is a
  hard rule, not a pattern match, so it cannot be bypassed by phrasing.
- Bash commands matching a short denylist (`npm install`, `pip install`,
  `rm -rf`, `git push`, `git reset --hard`, migration commands, etc.).
  This list is a speed bump, not a sandbox — see Limitations.
- Everything else (reading files, `git status`, `git diff`, running tests,
  lint, build) is allowed by default.

## What it warns about in `remediation` mode

Edits are allowed, but two categories get escalated to an explicit
confirmation prompt for the human in the loop, rather than the agent
deciding alone:

- Editing a high-risk path: `package.json`, lockfiles, `.env*`, Dockerfiles,
  deploy config, CI workflows, migrations/schema, or anything under an
  `auth/` directory.
- Running a high-risk Bash command: dependency installs, `git push`,
  `git reset --hard`, migrations.

## Before the agent finishes (`Stop`)

If files changed during the session and no verification command was
recorded, and the final answer doesn't clearly state what was verified, the
guard blocks completion once and asks for a verification command or an
explicit "what was/wasn't verified" statement. It will not block a second
time in the same mode-session — this is intentional, so a misclassified
case can never hang the session indefinitely. Outside `audit_read_only` /
`remediation` mode, the Stop hook does nothing.

## How to install it

1. Copy `examples/claude-code/settings.example.json`'s `hooks` block into
   your project's `.claude/settings.json` (merge, don't overwrite).
2. Adjust the `python3 scripts/runtime_guard.py ...` paths if this skill
   lives somewhere other than your project root.
3. Tell the agent (or have `SKILL.md` remind it) to run `set-mode` when it
   starts an audit or starts remediation.

Claude Code's hook payload and response field names have changed across
versions. The script extracts fields defensively and degrades to "do
nothing" if a field it expects is missing — but if a hook doesn't seem to
fire or block as described, check your installed Claude Code version's hook
documentation against the field names in `scripts/runtime_guard.py`.

## How to disable it

Remove the `hooks` entries that call `runtime_guard.py` from
`.claude/settings.json`, or run `python3 scripts/runtime_guard.py reset` to
drop the mode back to `unknown` (in which the guard is a no-op even if the
hooks stay wired).

## Limitations — read this before trusting it

- **Not a sandbox.** Bash pattern matching is a substring check. An agent
  (or a confused one) can phrase around it — a script that installs a
  package without the literal string `npm install`, for example. The hard
  guarantee is only the tool-name block on `Write`/`Edit`/`MultiEdit`/
  `NotebookEdit` in audit mode.
- **Does not prove code quality.** Passing the Stop check means a
  verification command ran or was reported — it does not mean the code is
  correct. Final quality still requires real audit evidence and human
  judgment.
- **Single state file per repo.** Concurrent sessions/worktrees auditing the
  same repo at the same time will read/write the same state file and can
  race each other. Fine for one active session at a time; not designed for
  more.
- **Mode can be forgotten.** If nobody runs `set-mode`, the guard does
  nothing. It is a backstop for the common failure mode (agent edits while
  "just auditing"), not a guarantee that auditing happened correctly.
