"""Add Deep Dive into Hermes Source sections to s13-s24 READMEs."""
from pathlib import Path

sections = {
    's13_cron_scheduler': """
<details>
<summary>深入 Hermes 源码</summary>

生产版 cron 系统位于以下源文件:

| 文件 | 职责 |
|------|------|
| `cron/scheduler.py` | tick() 调度器、run_job() 执行器、文件锁防并发 |
| `cron/jobs.py` | jobs.json 读写、任务 CRUD、原子替换 |
| `gateway/run.py`(:19756) | gateway 启动时自动拉起 cron ticker 线程 |
| `hermes_cli/cron.py` | CLI 命令: list/create/edit/pause/run/remove/status/tick |

教学版简化了什么:
- 生产版 gateway ticker 是 daemon 线程每 60s 触发，教学版用 threading.Event 模拟
- 生产版用 fcntl/msvcrt 文件锁防并发 tick，教学版省略
- 生产版支持 no_agent 模式 (纯脚本定时执行，不走 LLM)
- 生产版的 delivery 路由支持 E2EE 加密适配器

</details>
""",
    's14_gateway': """
<details>
<summary>深入 Hermes 源码</summary>

生产版 gateway 位于以下源文件:

| 文件 | 职责 |
|------|------|
| `gateway/run.py` | Gateway 主运行器、平台注册、cron ticker 启动 |
| `gateway/session.py` | 跨平台 session 管理、重置策略 |
| `gateway/delivery.py` | DeliveryRouter — 结果投递回正确平台/频道 |
| `gateway/platforms/` | 20+ 平台适配器 (Telegram/Discord/Slack/微信/飞书...) |
| `hermes_cli/gateway.py` | 安装/启动/停止 CLI、systemd/launchd 集成 |
| `hermes_cli/gateway_windows.py` | Windows schtasks + Startup 文件夹 fallback |

教学版简化了什么:
- 生产版有 20+ 平台适配器，教学版只演示 CLI + Cron + Telegram
- 生产版的 E2EE 加密通道 (Signal/Matrix) 需要 live adapter 实例
- 生产版 session 管理支持 daily / per_message 等多种重置策略
- 生产版 delivery 路由根据 job 的输出 channel 配置精准投递

</details>
""",
    's15_profiles': """
<details>
<summary>深入 Hermes 源码</summary>

生产版 profile 系统位于以下源文件:

| 文件 | 职责 |
|------|------|
| `hermes_cli/profiles.py` | Profile 创建/切换/删除、继承链解析 |
| `hermes_cli/config.py` | 全局配置加载、env var 展开 |
| `hermes_cli/service_manager.py` | 服务管理器接口: s6/systemd/launchd/windows |
| `cron/scheduler.py` | Cron 任务绑定特定 profile 执行 |

教学版简化了什么:
- 生产版支持 `hermes --profile work` 命令行切换
- 生产版每个 profile 可以启动独立的 gateway 实例监听不同平台
- 生产版 s6 backend 支持运行时注册/注销 profile gateway
- 生产版 cron 任务可以指定 `profile` 字段用特定配置执行

</details>
""",
    's16_agent_teams': """
<details>
<summary>深入 Hermes 源码</summary>

生产版 agent 团队系统位于以下源文件:

| 文件 | 职责 |
|------|------|
| `agent/background_review.py` | 子 agent fork + 受限权限执行 |
| `run_agent.py` | AIAgent 主类、spawn_subagent 方法 |
| `tools/delegate_tool.py` | delegate 工具 — 把任务委派给子 agent |

教学版简化了什么:
- 生产版子 agent 通过 forkSubagent 创建，拥有独立的 maxTurns 和工具权限
- 生产版的 JSONL mailbox 是生产级实现，支持跨进程通信
- 生产版 TaskBoard 支持 blockedBy 依赖关系和自动解锁
- 生产版支持 agent 团队的权限冒泡 (permission bubbling)

</details>
""",
    's17_mcp_plugin': """
<details>
<summary>深入 Hermes 源码</summary>

生产版 MCP 系统位于以下源文件:

| 文件 | 职责 |
|------|------|
| `tools/mcp_tool.py` | MCP 工具发现、工具池组装、JSON-RPC 调用 |
| `tools/mcp_oauth_manager.py` | MCP 服务器的 OAuth 认证管理 |
| `gateway/run.py` | gateway 启动时的异步 MCP 工具发现 |

教学版简化了什么:
- 生产版支持三种传输: stdio (子进程)、SSE (长连接)、Streamable HTTP
- 生产版 MCP 工具发现是异步的，不阻塞 gateway 启动
- 生产版支持 OAuth 认证流程的 MCP 服务器
- 生产版 MCP 工具和内置工具在同一个 tools 数组里对 LLM 完全透明

</details>
""",
    's18_full_hermes': """
<details>
<summary>深入 Hermes 源码</summary>

完整 Hermes 系统核心文件索引:

| 层级 | 核心文件 |
|------|---------|
| 入口 | `cli.py`, `hermes_cli/main.py` |
| Gateway | `gateway/run.py`, `gateway/session.py` |
| Agent Loop | `run_agent.py`, `agent/conversation_loop.py` |
| 记忆系统 | `agent/memory_manager.py`, `agent/memory_provider.py` |
| 技能系统 | `tools/skill_usage.py`, `tools/skill_manage.py` |
| Curator | `agent/curator.py` (scheduling + Phase 1 + Phase 2) |
| Cron | `cron/scheduler.py`, `cron/jobs.py` |
| MCP | `tools/mcp_tool.py`, `tools/mcp_oauth_manager.py` |
| Profiles | `hermes_cli/profiles.py`, `hermes_cli/config.py` |
| 上下文 | `agent/conversation_compression.py`, `agent/context_compressor.py` |
| 错误恢复 | `agent/conversation_loop.py` (recovery paths) |

</details>
""",
    's19_permission': """
<details>
<summary>深入 Hermes 源码</summary>

生产版权限系统位于以下源文件:

| 文件 | 职责 |
|------|------|
| `tools/approval.py` | 审批管线、YOLO 模式分类器 |
| `tools/path_security.py` | 文件路径安全检查、沙箱边界 |
| `tools/skills_guard.py` | 技能级别的权限控制 |
| `agent/file_safety.py` | 文件操作安全层、跨 profile 防护 |
| `agent/tool_guardrails.py` | 工具调用前的通用护栏检查 |

教学版简化了什么:
- 生产版有完整的 YOLO 分类器自动判断操作风险等级
- 生产版权限规则支持 glob 模式匹配文件路径
- 生产版 sandbox 模式可以限制网络访问、文件系统范围
- 生产版支持 hardline_blocklist: 即使在 YOLO 模式下也不能绕过的规则

</details>
""",
    's20_hooks': """
<details>
<summary>深入 Hermes 源码</summary>

生产版 hook 系统位于以下源文件:

| 文件 | 职责 |
|------|------|
| `agent/conversation_loop.py` | hook 触发点 (PreToolUse/PostToolUse/Stop/...) |
| `agent/background_review.py` | stop hook 触发后台审查 |
| `gateway/run.py` | gateway 生命周期 hook (SessionStart/End) |

教学版简化了什么:
- 生产版 hook event 包含完整的 session context 和 metadata
- 生产版 Stop hook 可以阻塞 agent 停止 (blocking=True)
- 生产版支持 conditional hooks: 按文件路径 glob 条件激活
- 生产版 hook 系统与 skill 系统联动 (skill 可以注册自己的 hook)

</details>
""",
    's21_worktree': """
<details>
<summary>深入 Hermes 源码</summary>

生产版 worktree 系统位于以下源文件:

| 文件 | 职责 |
|------|------|
| `agent/conversation_loop.py` | EnterWorktree/ExitWorktree 工具实现 |
| `agent/agent_runtime_helpers.py` | worktree 生命周期管理 |

教学版简化了什么:
- 生产版 worktree 基于 git worktree add 创建隔离分支
- 生产版支持 worktree.baseRef 配置 (fresh=从远程拉, head=从本地)
- 生产版 agent 可以在 worktree 中自由切换，通过 EnterWorktree 工具
- 生产版 worktree 清理支持 keep/remove 两种模式

</details>
""",
    's22_planning': """
<details>
<summary>深入 Hermes 源码</summary>

生产版任务规划系统位于以下源文件:

| 文件 | 职责 |
|------|------|
| `agent/task_manager.py` | TaskRecord 定义、blockedBy 依赖图、文件持久化 |
| `tools/task_tools.py` | TaskCreate/TaskUpdate/TaskList 工具实现 |

教学版简化了什么:
- 生产版 TaskRecord 包含 blockedBy/blocks 双向依赖和自动状态传播
- 生产版任务文件落盘为 JSON，支持跨 session 和跨 agent 共享
- 生产版 task agent 可以独立运行: 从任务板认领、执行、报告结果
- 生产版 activeForm 字段让进行中的任务显示当前正在做什么

</details>
""",
    's23_autonomous': """
<details>
<summary>深入 Hermes 源码</summary>

生产版自主 agent 系统位于以下源文件:

| 文件 | 职责 |
|------|------|
| `agent/background_review.py` | idle loop 实现、任务认领逻辑 |
| `cron/scheduler.py` | cron ticker 的自主调度 |
| `gateway/run.py` | gateway 心跳 + 空闲检测 |

教学版简化了什么:
- 生产版自主 agent 通过 heartbeat 机制 (每 30s) 检查待处理任务
- 生产版 agent 可以给自己注册 cron 任务: "每 5 分钟检查一次队列"
- 生产版支持 auto_claim: agent 根据 skill 自动匹配并认领任务
- 生产版有心跳监控和超时自动释放任务机制

</details>
""",
    's24_system_prompt': """
<details>
<summary>深入 Hermes 源码</summary>

生产版 system prompt 组装位于以下源文件:

| 文件 | 职责 |
|------|------|
| `agent/system_prompt.py` | 主 system prompt 构建器 |
| `agent/prompt_builder.py` | 分段 prompt 组装、条件注入 |
| `agent/memory_provider.py` | memory context 注入 |
| `gateway/session_context.py` | gateway 平台上下文注入 |

教学版简化了什么:
- 生产版 system prompt 有 20+ 个分段，按 priority 排序拼接
- 生产版每段的注入条件包括: profile、platform、has_memories 等
- 生产版 prompt cache TTL 感知: 记忆注入时机考虑 cache 有效性
- 生产版不同平台 (CLI/Telegram/Cron) 的 prompt 有很大差异

</details>
""",
}

for ch_dir_name, section in sections.items():
    readme = Path(ch_dir_name) / 'README.md'
    if readme.exists():
        content = readme.read_text(encoding='utf-8')
        marker = '<!-- translation-sync'
        if marker in content:
            content = content.replace(marker, section.strip() + '\n\n' + marker)
        else:
            content = content.rstrip() + '\n' + section.strip() + '\n'
        readme.write_text(content, encoding='utf-8')
        print('OK:', ch_dir_name)
