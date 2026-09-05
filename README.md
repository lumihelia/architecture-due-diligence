# Architecture Due Diligence

中文 · [English](./README.en.md)

一个面向代码库的技术尽调 Agent Skill。它用实际文件、关键路径和验证结果判断一个项目是否适合继续往上搭，并把最值得先处理的结构性风险排成可验证的修复顺序。

**当前版本：** `1.1.0`

这个仓库不提供独立应用。核心能力来自 [`SKILL.md`](./SKILL.md)，`scripts/project_inventory.py` 用于建立仓库地图，Claude Code 还可以选装 Runtime Guard，把“审计默认只读”从文字规则增加一层运行时约束。

## 它回答什么问题

Architecture Due Diligence 主要处理：

- 这个代码库现在健康吗？
- 继续加功能之前，最该先补什么？
- 哪些结构性问题会随着项目变大持续放大？
- 当前实现的技术上限在哪里？
- 从 prototype 走向 MVP、beta 或 public product 前，还缺哪些验证与基础设施？

它关注的是 **technical health**。

产品方向属于另一层判断：代码可能写得很健康，产品方向仍然值得重想；产品方向很清楚，代码也可能已经不适合继续往上搭。公开 Skill 保留这条边界，具体交给哪个 product-shaping / UI / security workflow，由宿主和项目自己的 instructions 决定。

## 核心原则

每个重要判断都要能回到证据：

- 文件、函数、模块、配置、manifest 或 schema；
- test / build / typecheck / lint / smoke 等命令输出；
- 实际 runtime、浏览器、console、log、API 或 deployment 行为；
- 应该存在却明确缺失的结构。

无法验证的部分标为 unknown，并写清下一步怎么验证。

## 三种深度

| 深度 | 适合什么情况 | 主要动作 |
| --- | --- | --- |
| Quick Scan | 小仓库、早期项目、需要快速判断 | repo map + 高信号文件 + 代表性路径 + top 3 risks |
| Focused Audit | 默认 | Quick Scan + 1–3 条关键路径 + 外部边界 + 关键测试 + 最小验证 |
| Deep Due Diligence | 上线、交接、重大重构、投资前等 | Focused Audit + security/privacy + persistence + deployment + operability + stage readiness |

默认使用 **Focused Audit**。审计深度跟实际决策走，小项目不需要把所有检查面机械填满。

## 审计流程

1. 判断项目阶段、审计深度与当前真正关心的问题。
2. 运行 `scripts/project_inventory.py` 或手动建立 repo map。
3. 读取项目 instructions、README、manifest、entrypoint、核心模块和关键 tests。
4. 沿 1–3 条真实关键路径追踪输入、业务逻辑、状态、外部服务、失败行为与验证面。
5. 按证据选择 architecture、complexity、reliability、security/privacy、testability、operability、frontend、AI integration 等检查面。
6. 运行最小且相关的验证命令。
7. 给出技术状态、technical ceiling、Top Findings 与有 verification gate 的修复顺序。

## 技术状态

报告使用五档判断：

`Healthy` → `Usable With Gaps` → `Fragile` → `Structurally Risky` → `Not Ready To Build On`

同时给出当前 technical ceiling：

`personal tool` → `prototype` → `MVP` → `beta` → `public product` → `SaaS-ready`

这两个维度用途不同：前者描述当前风险，后者描述现在这套技术形态最多能可靠支撑到哪里。

## 默认只读

审计默认不修改仓库，也不安装依赖、创建 migration 或顺手修问题。

真正进入 remediation 后，再把修复作为独立实现任务执行，并重新建立 verification gate。

这条边界能避免“只是想知道哪里有问题”最后变成 Agent 一边审一边重构，原始证据也随修改一起消失。

## Project Inventory

[`scripts/project_inventory.py`](./scripts/project_inventory.py) 是一个轻量只读 helper，用于快速看到目录、manifest、测试面、环境文件和 Git 状态。

它只负责建立地图。最终架构判断仍然需要直接检查相关文件和关键路径。

## Runtime Guard（可选，仅 Claude Code）

[`scripts/runtime_guard.py`](./scripts/runtime_guard.py) 可以接入 Claude Code hooks：

- `audit_read_only`：阻止主要文件写入工具，并对一组高风险 Bash 命令做拦截；
- `remediation`：允许修改，同时把高风险路径/命令升级为人工确认；
- `feature_build`：普通开发模式，guard 不介入审计约束。

mode 需要显式设置，Runtime Guard 不会根据 prompt 文本自行决定当前是不是审计。

它是 **backstop，不是 sandbox**。脚本的 Bash 匹配无法提供完整安全边界；Claude Code hooks 的字段与行为也可能随宿主版本变化。安装前请读 [`docs/runtime-guard.md`](./docs/runtime-guard.md)，并按当前 Claude Code 文档验证 hooks 是否仍按预期触发。Anthropic 当前仍把 `PreToolUse` hooks 放在权限判断前，并允许 hook 参与工具调用的许可判断。 

## 安装

推荐安装整个仓库目录，而不是只复制 `SKILL.md`，这样 inventory script、Runtime Guard、docs 与 agent metadata 都能保留。

常见 Agent Skill 目录包括：

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

部分宿主也支持 `.agents/skills/` 或项目级 skill root。实际路径以当前宿主文档为准。

BotLearn / SkillHunt 可以继续分发同一个 Skill；平台 taxonomy 更适合留在发布层，不写进 portable `SKILL.md` 顶层。

## 仓库结构

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

## 和个人 Agent 环境的关系

公开仓库保存可迁移的判断函数。什么时候自动提醒做 audit、项目自己的 memory checkpoint、使用哪套 product-shaping / UI quality Skill，都更适合由宿主的 `AGENTS.md`、`CLAUDE.md` 或 project instructions 决定。

这样，同一份 Architecture Due Diligence 可以保持可移植；个人环境仍然可以在它上面叠加自己的节奏、taste 与协作协议。

## License

[MIT](LICENSE)
