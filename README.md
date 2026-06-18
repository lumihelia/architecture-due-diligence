# Architecture Due Diligence

**Technical due diligence for codebases — assess architecture health, identify the highest-leverage structural risks, and produce an ordered fix sequence with verification gates.**

---

## Who it is for

Engineers, founders, and technical leads who need to answer one of these questions:

- Is this codebase safe to keep building on, or are we accumulating structural debt?
- What should we fix first before adding the next feature?
- What would a senior engineer or CTO flag after reviewing this repo?
- We are about to refactor / hand off / invest — what are the real risks?

## What it does

Three things, in a fixed order:

**1. Build a project map** — using a bundled inventory script (`scripts/project_inventory.py`) that scans the repo structure, manifests, test surface, environment files, and git state without modifying anything.

**2. Audit by surface** — architecture integrity, product-engineering fit, complexity budget, reliability, security/privacy, testability, operability, frontend quality, and AI integration. Surfaces are covered in proportion to evidence — thin areas are noted, not padded.

**3. Produce a judgment and fix sequence** — one direct paragraph on the overall technical state, top findings ordered by severity, and a recommended fix sequence with verification gates.

Every finding is grounded in at least one of: file paths, command output, observed runtime behavior, or explicit absence of expected structure. Claims without evidence are flagged as unknowns, not presented as findings.

## Depth levels

| Level | What it covers |
|-------|---------------|
| Quick Scan | Repo map, README, manifests, entrypoints — top 3 risks, next 3 fixes |
| Focused Audit | Quick Scan plus critical path traces, external boundaries, key tests, verification commands |
| Deep Due Diligence | Focused Audit plus security/privacy, deployment, data persistence, test strategy, operability |

Default depth is **Focused Audit**. Specify "quick scan" or "deep audit" to change it.

## What output it produces

**Compact report** (Quick Scan / small repos):

- Technical judgment — overall state and technical ceiling in one paragraph
- Top 3 risks with evidence, impact, and recommended fix
- Next 3 fixes with verification gates
- What was verified / not verified

**Full report** (Focused Audit / Deep Due Diligence):

- Technical judgment
- Architecture read — what the system appears to be from the actual files
- Top findings (P0/P1/P2) with evidence, impact, fix, and verification gate
- What not to do — tempting fixes that would add debt
- Recommended fix sequence
- Verification plan
- Residual risk — unknowns and skipped surfaces

## What it will not do

- Modify files, install dependencies, or remediate findings unless you explicitly ask it to after the audit
- Make claims without evidence — weak surfaces are reported as unknowns
- Run expensive commands without checking project manifests first
- Generate a list of style issues when no system-level risk is present

## Technical ceiling classification

Every report includes a technical ceiling judgment:

`personal tool` → `prototype` → `MVP` → `beta` → `public product` → `SaaS-ready`

The report states what currently prevents the next stage.

## How to install

### Via BotLearn

If your agent is connected to the BotLearn platform:

```
botlearn skillhunt architecture-due-diligence
```

Note: this command only works inside agents that run on BotLearn. It does not work in standalone agents (Claude Code, Codex, Cursor, Windsurf) running outside the platform.

### Direct installation

Download [SKILL.md](./SKILL.md) from this repository and place it where your agent reads instruction files:

**Claude Code** — copy to `.claude/skills/` in your project:
```bash
mkdir -p .claude/skills
curl -o .claude/skills/architecture-due-diligence.md \
  https://raw.githubusercontent.com/lumihelia/architecture-due-diligence/main/SKILL.md
```

**Codex** — add the SKILL.md content to your project's `AGENTS.md`.

**Cursor** — add as a rule in `.cursor/rules/architecture-due-diligence.mdc`, or paste into `.cursorrules`.

**Windsurf** — paste the SKILL.md content into `.windsurfrules`.

Then invoke through your agent:

```
Use Architecture Due Diligence on [path to repo or paste repo URL]
```

Or with a specific depth:

```
Use Architecture Due Diligence for a quick scan of this repo
```

## About

This skill was built around one constraint: every judgment must be traceable to evidence. The depth ladder, the inventory script, and the fix sequence rules all exist to prevent confident-sounding architectural opinions that cannot be verified — a common failure mode of code review agents.
