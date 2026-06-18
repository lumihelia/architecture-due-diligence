---
name: architecture-due-diligence
displayName: Architecture Due Diligence
description: Technical due diligence for codebases — assess architecture health, identify the highest-leverage structural risks, and produce an ordered fix sequence with verification gates.
categories: [engineering, research]
roles: [engineer, founder, lead]
outputs: [report, analysis]
scenarios: [code-review, technical-audit]
runtimes: [chat]
platforms: [claude-code, cursor, windsurf, codex]
tags: [architecture, codebase-audit, due-diligence]
version: 1.0.0
author: Helia
---

# Architecture Due Diligence

## Purpose

Assess whether a codebase is technically healthy enough to continue building on, identify the highest-leverage structural risks, and recommend a small, ordered fix sequence with verification gates.

This is not a normal code review. Focus on system health: architecture boundaries, data flow, operability, reliability, security posture, testability, complexity, and product-stage fit.

## Core Rule

Do not make senior-sounding claims without evidence. Every important judgment must be grounded in at least one of:

- File paths, functions, modules, configuration, or dependency manifests.
- Command output from tests, builds, type checks, linters, or smoke tests.
- Observed runtime behavior, console output, logs, screenshots, or API responses.
- Explicit absence of expected structure, such as no tests, no setup path, no env example, or no error boundary.

If evidence is incomplete, say what is unknown and how to verify it.

## Read-Only Default

Treat this skill as read-only by default. Do not modify files, install dependencies, rewrite architecture, create migrations, change configuration, or remediate findings unless the user explicitly asks for implementation.

The default deliverable is judgment, evidence, risk order, and next actions. If remediation is requested after the audit, treat it as a separate implementation task with its own verification loop.

## Review Stance

Adopt the perspective of a senior technical owner deciding what should happen next, not a reviewer collecting small style issues.

Prioritize:

- Structural problems that will compound.
- Risks that block product evolution, reliability, security, or maintainability.
- Misalignment between technical complexity and project stage.
- Missing verification surfaces for critical behavior.
- Fixes that reduce future ambiguity.

Deprioritize:

- Cosmetic code style unless it signals systemic inconsistency.
- Small local bugs unless they reveal a repeated architectural failure.
- Refactors that are elegant but not tied to risk reduction.
- Generic best practices that do not fit the project.

## Workflow

### 1. Establish Scope

Infer scope from the repository and user request before deep work:

- Project stage: personal tool, prototype, MVP, beta, public product, internal tool, or SaaS.
- Review depth: quick scan, focused audit, or deep due diligence.
- Primary concern: maintainability, reliability, security/privacy, deployment, frontend quality, AI integration, data model, or cost.
- Success condition: decision support, fix roadmap, implementation plan, or concrete remediation.

Ask at most one clarifying question only if the missing answer materially changes the audit path. Otherwise infer the likely stage and proceed.

If the user does not specify depth, default to **Focused Audit**.

Use this depth ladder:

- **Quick Scan**: Build a repo map, read README/instructions/manifests/entrypoints, identify test/build commands, and report 3-5 top risks.
- **Focused Audit**: Do Quick Scan plus trace critical paths, inspect external boundaries, read key tests, and run the smallest relevant verification commands.
- **Deep Due Diligence**: Do Focused Audit plus security/privacy, deployment, data persistence, test strategy, operability, and stage-ceiling analysis.

### 2. Compress Execution When Appropriate

If the repository is small, early-stage, unfamiliar to the user, or the user asks for a quick judgment, use the lightweight path:

- Build a repo map.
- Read instructions, README, manifests, entrypoints, and one critical path.
- Derive one relevant verification command from project scripts or documentation.
- Report the top 3 risks and next 3 fixes.

Do not expand into every audit surface unless evidence shows that surface is material. Keep the audit proportional to the decision the user needs to make.

### 3. Build A Project Map First

Before giving judgments, inspect the repository structure and actual execution surface.

Locate this skill directory first. If `scripts/project_inventory.py` exists beside this `SKILL.md`, run it against the target repo:

```bash
python3 "$SKILL_DIR/scripts/project_inventory.py" /path/to/repo
```

If `$SKILL_DIR` is not already set by the runtime, infer it from the directory containing this `SKILL.md`.

If the helper script is unavailable, manually build the inventory with repository inspection commands such as `rg --files`, `find`, `ls`, `tree`, or language-specific manifest reads.

Use the output as a starting map, not as final evidence. Then inspect the relevant files directly.

Always identify:

- Entry points and routing surfaces.
- Core domain/business logic.
- State management and data flow.
- External service boundaries.
- Persistence and schema/migration surfaces.
- Authentication, authorization, secrets, and privacy surfaces when present.
- Test, build, lint, typecheck, and deployment commands.
- Runtime configuration and environment variable expectations.

### 4. Read The Highest-Signal Files

Read files in this order unless the project suggests a better path:

1. Project instructions: `AGENTS.md`, `README*`, `CONTRIBUTING*`, `docs/*` if small.
2. Manifests and config: `package.json`, `pyproject.toml`, `requirements*.txt`, `Cargo.toml`, `go.mod`, `Dockerfile`, CI files, deployment config.
3. Entrypoints: app routers, server startup, CLI entry, worker entry, main scripts.
4. Core modules: services, models, domain logic, data access, state stores, provider integrations.
5. Tests and fixtures.
6. Recent change surface when reviewing an active worktree or branch.

Avoid reading generated files, dependency directories, lockfiles, large assets, build outputs, and private environment files unless specifically needed.

### 5. Trace Critical Paths

For Focused Audit and Deep Due Diligence, trace 1-3 critical paths end to end before making architecture claims.

Choose paths that represent real product value or operational risk, such as signup, ingestion, upload, checkout, AI generation, webhook processing, background job execution, deployment startup, or the main user workflow.

For each path, identify:

- User action, CLI command, scheduled job, webhook, or API entrypoint.
- Router/controller/handler surface.
- Data transformation and validation.
- Domain/service boundary.
- State, storage, cache, queue, or migration boundary.
- External provider calls and failure behavior.
- Loading, error, retry, timeout, cancellation, and partial-success handling.
- Test, fixture, replay, eval, or smoke verification surface.

Use these traces as the main evidence for system-level findings. A broad file scan can reveal candidates, but critical-path evidence should drive the final judgment.

### 6. Inspect By Audit Surface

Use these surfaces as the due diligence frame. Do not force every section into the final answer if evidence is thin.

**Architecture Integrity**

- Are module boundaries clear and enforceable?
- Is domain logic separated from UI, transport, storage, and provider code?
- Is there a single understandable data flow?
- Are abstractions carrying real complexity or hiding accidental complexity?

**Product-Engineering Fit**

- Does the technical shape match the current product stage?
- Is the project optimized for the next real milestone or for a demo that will become debt?
- Is the implementation reversible if the product direction changes?

**Complexity Budget**

- Which dependencies, services, state layers, queues, agents, caches, or build tools are essential?
- Which ones create ongoing operational cost or lock-in without enough benefit?
- Are there multiple ways to do the same thing?

**Reliability Surface**

- Are loading, error, empty, timeout, retry, cancellation, and partial-failure paths handled?
- Are critical async flows observable and recoverable?
- Are failures explicit or swallowed?

**Security And Privacy**

- Are secrets read from environment variables and kept out of logs?
- Is user data minimized across providers and external services?
- Are auth, authorization, upload, webhook, and file-processing boundaries defensible?
- Are dangerous operations reversible or guarded?

**Testability**

- Can core logic be tested without full end-to-end setup?
- Do tests cover the highest-risk behavior?
- Are fixtures realistic enough to catch regressions?
- Are there smoke tests for startup, main flows, or critical integrations?

**Operability**

- Can a new maintainer run, verify, debug, and deploy the project without guessing?
- Are environment variables documented?
- Are logs useful without leaking sensitive data?
- Are migrations, background jobs, cron tasks, queues, or external accounts understandable?

**Frontend Quality**

- Is the interface responsive across relevant breakpoints?
- Are hover, focus, loading, empty, and error states present?
- Are console errors absent?
- Does the UI hierarchy support the workflow, or is it decorative structure?

**AI Integration**

- Are prompts, provider calls, response parsing, retries, and cost limits explicit?
- Is model output treated as untrusted input where appropriate?
- Is sensitive data minimized before provider calls?
- Is provider-specific logic isolated enough to replace or test?
- Are tool permissions and irreversible actions constrained?
- Are prompt-injection and untrusted-input boundaries explicit?
- Are model outputs validated with schemas or strict parsers before action?
- Are parse failures, refusal paths, rate limits, timeouts, retries, and cost runaway controlled?
- Are provider fallback and degradation behavior intentional?
- Are golden traces, evals, replay fixtures, or regression examples present for critical AI behavior?
- Is user data retention documented and minimized before provider calls?

### 7. Verify Claims

Run the smallest relevant checks available. Prefer existing scripts over inventing new checks.

Derive verification commands from project manifests and documentation first. For JavaScript/TypeScript, inspect `package.json` scripts before running commands. For Python, inspect `pyproject.toml`, `pytest.ini`, `tox.ini`, `noxfile.py`, `requirements*.txt`, and README instructions. Use the examples below only when the repo exposes matching scripts or clear conventions.

For JavaScript/TypeScript projects, consider:

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

For Python projects, consider:

```bash
python3 -m pytest
python3 -m compileall .
python3 path/to/smoke_test.py
```

For frontend projects, use browser verification when the task concerns UI quality or runtime behavior. Check at least one desktop and one mobile viewport when making frontend claims.

If a command is too expensive, missing, or blocked by setup, report that as a finding or limitation. Do not treat unrun checks as passed.

### 8. Classify Technical State

Give one concise project-level judgment:

- **Healthy**: coherent architecture, clear verification, low compounding risk.
- **Usable With Gaps**: product can continue, but specific areas need tightening.
- **Fragile**: works now, but defects or changes are likely to compound.
- **Structurally Risky**: architecture or operational shape blocks safe growth.
- **Not Ready To Build On**: major unknowns or defects make further feature work irresponsible.

Also state the current technical ceiling: personal tool, prototype, MVP, beta, public product, or SaaS-ready. Explain what prevents the next stage.

### 9. Produce The Report

Use the compact report for Quick Scan, small projects, early-stage repos, or when the user needs a fast decision:

```text
Technical Judgment
One direct paragraph with state, technical ceiling, and biggest constraint.

Top 3 Risks
Each risk includes evidence, impact, and recommended fix.

Next 3 Fixes
Ordered actions with verification gates.

Verified / Not Verified
Commands run, results, blocked checks, and unknowns.
```

Use the full report for Focused Audit or Deep Due Diligence when the evidence justifies the length:

```text
Technical Judgment
One direct paragraph with the overall state, technical ceiling, and biggest constraint.

Architecture Read
What the system appears to be, based on the actual files and runtime surface.

Top Findings
P0/P1/P2 findings ordered by severity. Each finding includes:
- Problem
- Evidence
- Impact
- Recommended fix
- Verification gate

What Not To Do
Specific tempting fixes that would add debt or obscure the real issue.

Recommended Fix Sequence
3-7 ordered steps. Each step must be small enough to verify and should reduce risk before adding capability.

Verification Plan
Commands or manual checks that prove the remediation worked.

Residual Risk
Unknowns, skipped surfaces, blocked checks, and decisions that need the owner.
```

Every report section must help the user make a decision. Omit or merge sections with thin evidence instead of filling them with generic commentary.

## Severity

Use severity for system risk, not personal preference.

- **P0**: Data loss, security/privacy exposure, broken deploy/startup, or architecture that blocks the stated goal.
- **P1**: High compounding risk, brittle critical path, missing verification for important behavior, unclear ownership of core logic.
- **P2**: Maintainability, operability, or UX quality issues that should be fixed but do not block near-term progress.
- **P3**: Minor cleanup. Include only when useful, and keep it out of the top findings unless the user asked for exhaustive review.

## Fix Sequence Rules

Recommend the smallest sequence that changes the project's trajectory.

- Put risk reduction before feature work.
- Put boundary clarification before broad refactors.
- Put tests or smoke checks around critical paths before changing them.
- Put provider, storage, and deployment changes behind explicit interfaces when possible.
- Avoid migrations, new dependencies, service splits, or rewrites unless the evidence shows they are necessary.
- For each step, state how to verify and how to roll back or contain the change.

## Anti-Patterns

Call out these patterns when present:

- UI, transport, persistence, and business rules mixed in the same files.
- Prompts or provider response parsing hidden inside UI or unrelated utilities.
- Multiple competing state sources.
- New features added on top of untested critical paths.
- Broad refactors without a failing test, metric, or explicit risk target.
- Environment setup that relies on undocumented private knowledge.
- Mock data or placeholder flows presented as production behavior.
- Logging or analytics that could leak sensitive user data.
- Dependency additions that replace a small local need with long-term maintenance burden.

## Final Answer Requirements

When using this skill, finish with:

- What was reviewed.
- What was verified, including exact commands and results.
- What was not verified.
- The recommended next action.

Never claim the project is healthy, broken, scalable, secure, or production-ready without evidence.
