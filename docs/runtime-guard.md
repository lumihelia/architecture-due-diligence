# Runtime Guard（可选，仅 Claude Code）

中文 · [English](./runtime-guard.en.md)

Runtime Guard 是 Architecture Due Diligence 的可选运行时补充。Skill 本体负责告诉 Agent“审计默认只读”；Runtime Guard 通过 Claude Code hooks 再加一层执行约束。

它依赖 Claude Code 的 hooks 与权限机制，因此不属于跨宿主 Skill 的核心能力。

## 它做什么

`scripts/runtime_guard.py` 是一个只依赖 Python 标准库的脚本，围绕四类 hook 事件工作：

- `UserPromptSubmit`：发现像 audit / remediation 的请求时，只提醒显式设置 mode，不自动判断；
- `PreToolUse`：工具运行前读取当前 mode，并决定允许、询问或阻止；
- `PostToolUse`：记录变更与验证活动；
- `Stop`：存在修改但缺少验证时，最多阻止结束一次，要求运行验证或明确报告未验证项。

Claude Code 的 hook schema 会迭代。脚本对若干历史字段名做了兼容处理，安装时仍应对照当前官方文档检查 payload 与 response 字段。

## Mode 必须显式设置

```bash
python3 scripts/runtime_guard.py set-mode audit_read_only
python3 scripts/runtime_guard.py set-mode remediation
python3 scripts/runtime_guard.py set-mode feature_build
python3 scripts/runtime_guard.py status
python3 scripts/runtime_guard.py reset
```

未设置时 mode 为 `unknown`，guard 不主动介入。

prompt 文本只用于提醒，不用于决定 mode。这样可以避免一句普通的 “review this” 把整个项目错误锁成只读。

## `audit_read_only`

这一模式用于真正的审计阶段。

主要行为：

- `Write`、`Edit`、`MultiEdit`、`NotebookEdit` 等主要写入工具直接拒绝；
- 对依赖安装、危险 Git 操作、migration 等一组 Bash 字符串做 denylist 检查；
- Read、搜索、`git status`、`git diff`、测试、lint、build 等默认允许。

工具名拦截比字符串匹配更可靠；Bash denylist 只是 speed bump。

## `remediation`

用户明确要求实现修复后再切换到这一模式。

编辑可以进行，同时两类动作会要求人工确认：

- 高风险路径，例如 dependency manifest / lockfile、`.env*`、Docker / deploy / CI、schema / migrations、auth 相关文件；
- 高风险 Bash，例如依赖安装、`git push`、`git reset --hard`、migration。

## `feature_build`

普通开发使用。Runtime Guard 不把 architecture-audit 规则扩张到无关任务。

## Stop 检查

如果本轮发生文件修改，却没有记录到验证命令，也没有在最终报告中清楚说明 verified / not verified，Stop hook 会阻止结束一次。

同一 mode-session 只阻止一次，避免误判导致会话卡死。

这只能证明“验证动作被运行或被报告”，不能证明代码正确。

## 安装

1. 查看 `examples/claude-code/settings.example.json`。
2. 把其中的 `hooks` 配置合并进项目 `.claude/settings.json`，不要覆盖已有设置。
3. 根据 Skill 实际安装位置调整 `runtime_guard.py` 路径。
4. 在 audit / remediation 开始时显式运行对应的 `set-mode`。
5. 用当前 Claude Code 官方 hooks 文档核对事件名、matcher、输入字段与 hook 输出格式。

Anthropic 当前仍支持通过 `PreToolUse` hook 在权限系统运行前参与工具权限判断，但具体字段与 hook 能力应以安装版本的官方文档为准。

## 禁用

从 `.claude/settings.json` 删除相关 hooks，或执行：

```bash
python3 scripts/runtime_guard.py reset
```

`unknown` mode 下，即使 hook 仍然配置，脚本也按 no-op 处理。

## 限制

### 它不是 sandbox

Bash 检查是 substring matching，可以被不同命令形式绕过。Runtime Guard 的目标是减少 Agent 在“只读审计”里顺手修改项目的常见失误，不提供完整安全隔离。

### 它不能证明审计质量

通过 Stop gate 只说明验证动作存在。架构判断仍需要真实文件、runtime、测试与人工判断支持。

### 一个 repo 共用一个 state file

默认 state 位于项目的 `.architecture-due-diligence/`。多个 session / worktree 同时操作同一 repo 时可能发生竞争；当前设计适合单一活跃会话。

### Mode 可能忘记设置

`unknown` 时 guard 不工作。它是 opt-in backstop，不是自动安全层。

### Hooks 是宿主接口

Claude Code 持续迭代。出现 hook 没触发、权限判断无效或字段不兼容时，先对照当前安装版本的 hooks 文档，再判断是 Runtime Guard 逻辑问题还是宿主 API 已变化。
