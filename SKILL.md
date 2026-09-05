---
name: architecture-due-diligence
description: Assess project-level codebase health, architecture quality, maintainability, reliability, security posture, technical debt, operability, and technical ceiling. Use for architecture review, technical audit, pre-refactor or pre-investment assessment, stage-transition readiness, or when deciding whether a codebase is safe to keep building on. Not for routine line-by-line PR review or product-direction judgment.
license: MIT
compatibility: Requires repository/file inspection and command execution for meaningful verification. Browser access is useful for frontend/runtime checks. The optional Runtime Guard requires Claude Code hooks.
metadata:
  author: Helia
  version: "1.1.0"
---

# Architecture Due Diligence

## Purpose

Assess whether a codebase is technically healthy enough to continue building on, identify the highest-leverage structural risks, and recommend a small ordered fix sequence with verification gates.

This is a system-health review. Focus on architecture boundaries, critical paths, data flow, operability, reliability, security/privacy, testability, complexity, AI integration, and product-stage fit.

## Scope boundary

Keep three review types distinct:

- **Architecture due diligence:** Is the current codebase safe to keep building on?
- **Product-direction review:** Should the product still be built this way at all?
- **Routine code review:** Is this specific diff or implementation correct?

This skill owns the first question. If host/project instructions provide dedicated product-shaping, UI-review, security, or code-review workflows, route those judgments to the appropriate layer instead of duplicating them here.

## Core rule: evidence before judgment

Every load-bearing claim must be grounded in at least one of:

- file paths, functions, modules, configuration, manifests, or schemas;
- command output from tests, builds, type checks, linters, dependency checks, or smoke tests;
- observed runtime behavior, console output, logs, screenshots, API responses, or deployment output;
- explicit absence of expected structure, such as no tests, no setup path, no env example, or no error boundary.

If evidence is incomplete, mark the claim unknown and state how to verify it. Do not convert an unrun check into a passed check.

## Read-only default

Audit mode is read-only.

Do not modify files, install dependencies, create migrations, change configuration, rewrite architecture, or remediate findings unless the user explicitly asks for implementation after the audit.

The default deliverable is judgment, evidence, risk order, and next actions. Remediation is a separate implementation task with its own verification loop.

### Optional Claude Code Runtime Guard

If this skill directory contains `scripts/runtime_guard.py` and the host is Claude Code with hooks configured, the guard can enforce part of the read-only boundary at runtime.

Set mode explicitly:

```bash
python3 scripts/runtime_guard.py set-mode audit_read_only
python3 scripts/runtime_guard.py set-mode remediation
python3 scripts/runtime_guard.py set-mode feature_build
```

The guard is optional. It is not a sandbox and must not replace audit judgment, permissions, or verification. Read `docs/runtime-guard.md` before relying on it.

## Review stance

Act like a senior technical owner deciding what should happen next.

Prioritize:

- structural problems that compound;
- risks blocking reliability, security, maintainability, operability, or product evolution;
- mismatch between technical complexity and project stage;
- unverified critical paths;
- unclear ownership of core logic or state;
- fixes that reduce future ambiguity.

Deprioritize:

- cosmetic style unless it reveals systemic inconsistency;
- local bugs unless they expose a repeated structural failure;
- elegant refactors with no risk-reduction target;
- generic best practices unsupported by this project's evidence.

## Workflow

### 1. Establish scope

Infer scope from the repository and request:

- project stage: personal tool, prototype, MVP, beta, public product, internal tool, or SaaS;
- review depth: Quick Scan, Focused Audit, or Deep Due Diligence;
- primary concern: maintainability, reliability, security/privacy, deployment, frontend, AI integration, data model, cost, or broad health;
- success condition: decision support, fix sequence, implementation plan, or later remediation.

Ask at most one clarifying question only when the missing answer materially changes the audit path. Otherwise infer the likely stage and proceed.

Default to **Focused Audit**.

### 2. Choose depth

**Quick Scan**

- Build a repository map.
- Read project instructions, README, manifests, and entrypoints.
- Identify test/build commands.
- Trace one representative path when possible.
- Report the top 3 risks and next 3 fixes.

**Focused Audit**

- Do the Quick Scan.
- Trace 1–3 critical paths end to end.
- Inspect external boundaries and key tests.
- Run the smallest relevant verification commands.
- Judge technical ceiling and compounding risk.

**Deep Due Diligence**

- Do the Focused Audit.
- Expand into security/privacy, deployment, persistence/migrations, test strategy, operability, dependency exposure, recovery, and stage-readiness.
- Verify high-risk claims across multiple surfaces when feasible.

Keep audit depth proportional to the decision. A small repository does not need every surface padded with generic commentary.

### 3. Build a project map first

Locate this skill directory. If `scripts/project_inventory.py` exists, run it against the target repository:

```bash
python3 "$SKILL_DIR/scripts/project_inventory.py" /path/to/repo
```

If `$SKILL_DIR` is unavailable, infer the directory containing this `SKILL.md`. If the helper script cannot run, build the inventory manually with repository inspection tools.

Treat inventory output as a map, not final evidence.

Identify:

- entrypoints and routing surfaces;
- core domain/business logic;
- state management and data flow;
- external service/provider boundaries;
- persistence, schema, migration, cache, and queue surfaces;
- auth, authorization, secrets, and privacy boundaries when present;
- test, build, lint, typecheck, and deployment commands;
- runtime configuration and environment expectations.

### 4. Read the highest-signal files

Prefer this order unless project structure suggests otherwise:

1. Project instructions (`AGENTS.md`, `CLAUDE.md`, equivalent host/project rules), README, contributing docs, small project docs.
2. Manifests and configuration.
3. Entrypoints.
4. Core domain/service/data/provider modules.
5. Tests and fixtures.
6. Recent change surface when reviewing an active branch or worktree.

Avoid generated files, dependency directories, build outputs, large assets, private environment files, and lockfiles unless they are directly relevant.

### 5. Trace critical paths

Focused and deep audits should trace 1–3 paths that represent actual product value or operational risk: signup, ingestion, upload, checkout, AI generation, webhook processing, background jobs, deployment startup, or the main workflow.

For each path, inspect:

- user/CLI/job/API entrypoint;
- handler/router/controller;
- validation and transformation;
- domain/service boundary;
- state/storage/cache/queue/migration boundary;
- external calls and failure behavior;
- loading, error, retry, timeout, cancellation, and partial-success handling;
- test, fixture, replay, eval, or smoke surface.

Critical-path evidence should drive system-level findings. Broad scans are candidate generators, not conclusions.

### 6. Audit by surface

Use only the surfaces supported by evidence.

#### Architecture integrity

- Are boundaries understandable and enforceable?
- Is domain logic separated from UI, transport, persistence, and provider code?
- Are there competing sources of truth?
- Do abstractions carry real complexity or create it?

#### Product-engineering fit

- Does the technical shape match the current stage?
- Is the project optimized for the next real milestone?
- Are important choices reversible while product direction is still fluid?

#### Complexity budget

- Which dependencies, services, queues, caches, state layers, build tools, or agents are essential?
- Which create maintenance or lock-in without enough benefit?
- Are multiple mechanisms solving the same problem?

#### Reliability

- Are failure, empty, loading, timeout, retry, cancellation, and partial-success paths explicit?
- Can critical async flows be observed and recovered?
- Are failures surfaced or swallowed?

#### Security and privacy

- Are secrets separated from code and logs?
- Is sensitive data minimized across external boundaries?
- Are auth, authorization, upload, webhook, file-processing, and administrative surfaces defensible?
- Are dangerous actions constrained and reversible where possible?

#### Testability

- Can core logic be tested without full end-to-end setup?
- Do tests cover high-risk behavior?
- Are fixtures realistic enough to catch regressions?
- Are startup/main-flow/integration smoke tests present where needed?

#### Operability

- Can a new maintainer run, verify, debug, and deploy without private knowledge?
- Are environment expectations documented?
- Are migrations, jobs, queues, scheduled tasks, and external accounts understandable?
- Are logs useful without leaking data?

#### Frontend quality

- Does the UI support the real workflow?
- Are responsive, focus, loading, empty, error, and important interaction states handled?
- Are console/runtime errors absent?
- Does implementation respect the project's own design system and local UI-quality instructions?

Use project-specific design guidance when it exists. Generic UI heuristics are a fallback, not a replacement for local product language.

#### AI integration

- Are prompts, tool permissions, provider calls, response parsing, retries, limits, and cost boundaries explicit?
- Is model output treated as untrusted input where appropriate?
- Are prompt-injection and untrusted-context boundaries explicit?
- Are outputs schema-validated or strictly parsed before consequential action?
- Are refusal, parse failure, timeout, rate limit, fallback, and degradation paths intentional?
- Are replay fixtures, evals, golden traces, or regression cases present for critical AI behavior?
- Is user data minimized and retention understood before provider calls?

### 7. Verify claims

Read project manifests and documentation before choosing commands. Prefer existing scripts over invented checks.

Examples only when the repository exposes matching conventions:

```bash
# JavaScript / TypeScript
npm run lint
npm run typecheck
npm test
npm run build

# Python
python3 -m pytest
python3 -m compileall .
```

For frontend/runtime claims, use browser verification when available. Check at least one desktop and one mobile viewport before making responsiveness claims.

If a command is expensive, destructive, missing, or blocked by setup, do not force it. Record the limitation.

### 8. Classify technical state

Choose one project-level state:

- **Healthy** — coherent architecture, meaningful verification, low compounding risk.
- **Usable With Gaps** — safe to continue with specific areas requiring tightening.
- **Fragile** — works, but defects or changes are likely to compound.
- **Structurally Risky** — architecture or operational shape blocks safe growth.
- **Not Ready To Build On** — major unknowns or defects make more feature work irresponsible.

Also state the current technical ceiling: personal tool, prototype, MVP, beta, public product, or SaaS-ready. Name the evidence-backed constraint preventing the next stage.

### 9. Produce the report

Use a compact report for Quick Scan and small repositories:

```text
Technical Judgment
Top 3 Risks
Next 3 Fixes
Verified / Not Verified
```

Use the full report when Focused or Deep evidence justifies it:

```text
Technical Judgment
Architecture Read
Top Findings
What Not To Do
Recommended Fix Sequence
Verification Plan
Residual Risk
```

For each top finding include:

- severity;
- problem;
- evidence;
- impact;
- recommended fix;
- verification gate.

Omit thin sections instead of filling them with generic advice.

## Severity

- **P0** — data loss, security/privacy exposure, broken deploy/startup, or architecture that blocks the stated goal.
- **P1** — high compounding risk, brittle critical path, missing verification for important behavior, unclear ownership of core logic.
- **P2** — maintainability, operability, or UX issues worth fixing without blocking near-term progress.
- **P3** — minor cleanup; include only when useful.

## Fix-sequence rules

- Put risk reduction before feature work.
- Clarify boundaries before broad refactors.
- Put tests/smoke checks around critical paths before changing them.
- Put provider, storage, and deployment changes behind explicit interfaces where useful.
- Avoid migrations, new dependencies, service splits, or rewrites unless evidence requires them.
- Give each step a verification gate and, where relevant, a rollback/containment path.

## Anti-patterns

Call out when evidenced:

- UI, transport, persistence, and business rules mixed together;
- prompts/provider parsing hidden in unrelated UI/utilities;
- multiple competing state sources;
- feature growth on untested critical paths;
- broad refactors with no failing test, metric, or risk target;
- setup that depends on undocumented private knowledge;
- placeholder/mock flows presented as production behavior;
- logs/analytics leaking sensitive data;
- dependencies that replace a small local need with long-term maintenance burden.

## Remediation handoff

When the user explicitly asks to implement fixes after the audit:

1. preserve the audit evidence and risk order;
2. choose the smallest fix that reduces the highest material risk;
3. check repository status and local instructions before editing;
4. define the verification gate before implementation;
5. keep unrelated cleanup out of scope;
6. report exact files changed, verification run, result, and remaining risk.

If Runtime Guard is installed in Claude Code, switch to `remediation` mode only after remediation is explicitly requested.

## Final answer requirements

Finish every audit with:

- what was reviewed;
- what was verified, including exact commands/results;
- what was not verified;
- the recommended next action.

Never call a project healthy, broken, scalable, secure, production-ready, or SaaS-ready without evidence.
