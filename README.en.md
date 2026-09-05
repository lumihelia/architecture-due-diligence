# Architecture Due Diligence

[中文](./README.md) · English

A technical due-diligence Agent Skill for codebases. It uses repository evidence, critical-path tracing, and verification results to judge whether a project is safe to keep building on, then orders the highest-leverage structural risks into a verifiable fix sequence.

**Current version:** `1.1.0`

This repository is not a standalone app. [`SKILL.md`](./SKILL.md) defines the audit protocol, `scripts/project_inventory.py` builds a lightweight repository map, and Claude Code can optionally add Runtime Guard as an execution-time backstop for the read-only audit boundary.

## Questions it answers

Architecture Due Diligence is designed for questions such as:

- Is this codebase technically healthy?
- What needs to be fixed before the next feature?
- Which structural risks will compound as the project grows?
- What is the current technical ceiling?
- What is missing before moving from prototype to MVP, beta, or a public product?

The skill judges **technical health**.

Product direction is a separate judgment layer. Healthy code can still support the wrong product direction, and a strong product direction can sit on a fragile codebase. The public skill preserves this boundary; host/project instructions decide which product-shaping, UI, security, or code-review workflow owns adjacent judgments.

## Core rule

Every material judgment should trace back to evidence:

- files, functions, modules, config, manifests, or schemas;
- test/build/typecheck/lint/smoke command output;
- observed runtime, browser, console, log, API, or deployment behavior;
- explicit absence of expected structure.

Unverified areas remain unknown and include a verification path.

## Audit depth

| Depth | Best for | Main work |
| --- | --- | --- |
| Quick Scan | Small/early repositories, fast decisions | repo map + high-signal files + representative path + top 3 risks |
| Focused Audit | Default | Quick Scan + 1–3 critical paths + external boundaries + key tests + minimal verification |
| Deep Due Diligence | Release, handoff, major refactor, investment, stage transition | Focused Audit + security/privacy + persistence + deployment + operability + stage readiness |

The default is **Focused Audit**. Depth follows the decision rather than forcing every surface into every report.

## Workflow

1. Establish project stage, audit depth, and the decision that needs support.
2. Run `scripts/project_inventory.py` or build a repository map manually.
3. Read project instructions, README, manifests, entrypoints, core modules, and high-signal tests.
4. Trace 1–3 real critical paths across input, domain logic, state, external services, failure behavior, and verification surfaces.
5. Select evidence-backed audit surfaces: architecture, complexity, reliability, security/privacy, testability, operability, frontend, AI integration, and others when material.
6. Run the smallest relevant verification commands.
7. Produce a technical state, technical ceiling, top findings, and a fix sequence with verification gates.

## Technical state

Reports use five states:

`Healthy` → `Usable With Gaps` → `Fragile` → `Structurally Risky` → `Not Ready To Build On`

They also state a technical ceiling:

`personal tool` → `prototype` → `MVP` → `beta` → `public product` → `SaaS-ready`

The first describes present risk. The second describes how far the current technical shape can reliably support the product.

## Read-only by default

Audits do not modify the target repository, install dependencies, create migrations, or remediate findings by default.

Remediation becomes a separate implementation task after explicit approval, with its own verification gate.

This keeps the evidence surface stable while the audit is being formed.

## Project Inventory

[`scripts/project_inventory.py`](./scripts/project_inventory.py) is a lightweight read-only helper for repository structure, manifests, test surface, environment files, and Git state.

It creates a map; it does not replace direct inspection or critical-path tracing.

## Runtime Guard (optional, Claude Code only)

[`scripts/runtime_guard.py`](./scripts/runtime_guard.py) can be wired into Claude Code hooks:

- `audit_read_only` blocks major file-writing tools and a short list of risky Bash commands;
- `remediation` allows edits while escalating high-risk paths/commands for human confirmation;
- `feature_build` leaves ordinary feature work outside the audit guard.

Mode is explicit. Runtime Guard never decides from prompt text that a session is an audit.

It is a **backstop, not a sandbox**. Bash matching cannot provide a complete security boundary, and Claude Code hook schemas can change. Read [`docs/runtime-guard.en.md`](./docs/runtime-guard.en.md) before installing it and verify the configuration against the current Claude Code hook documentation.

## Installation

Install the whole repository directory when possible so the inventory script, Runtime Guard, docs, and agent metadata remain available.

Common Agent Skill locations include:

```text
# Codex
~/.codex/skills/architecture-due-diligence/

# Claude Code
~/.claude/skills/architecture-due-diligence/

# Cursor
~/.cursor/skills/architecture-due-diligence/

# Windsurf
~/.codeium/windsurf/skills/architecture-due-diligence/
```

Some hosts also support `.agents/skills/` or project-level skill roots. Follow current host documentation for exact discovery paths.

BotLearn / SkillHunt can distribute the same package; platform taxonomy belongs more naturally in the publishing layer than in portable top-level `SKILL.md` fields.

## Repository map

```text
SKILL.md
agents/openai.yaml
scripts/
  project_inventory.py
  runtime_guard.py
guard/
docs/
  runtime-guard.md
  runtime-guard.en.md
examples/claude-code/
tests/test_runtime_guard.py
README.md
README.en.md
LICENSE
```

## Personal host integration

The public repository should preserve portable judgment functions. Audit reminders, project-memory checkpoints, and routing to local product-shaping or UI-quality skills belong in the host's `AGENTS.md`, `CLAUDE.md`, or project instructions.

That keeps the skill reusable while allowing a personal agent environment to layer its own cadence, taste, and collaboration protocol on top.

## License

[MIT](LICENSE)
