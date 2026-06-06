# s04: Memory System — 可插拔记忆架构

[中文](README.md) · [English](README.en.md)

s01 → s02 → s03 → `s04` → [s05](../s05_skill_lifecycle/) → ... → s12
> *"记忆不该只有一个文件"* — 双层架构 + FTS5 全文搜索 + 可插拔提供者 + 生命周期钩子。
>
> **自进化层**: 记忆系统 — 跨会话知识积累的持久化底座。

---

## 问题

s01-s03 的记忆系统是单文件 `MEMORY.md`，简单但脆弱：
- 搜索只能靠文件名和描述，没有全文搜索
- 没有结构化的查询接口
- 没有扩展性——想换向量数据库？得全改

生产环境需要：全文搜索、可替换的存储后端、丰富的生命周期事件。

---

## 解决方案

**双层架构**：

```
MemoryManager (编排器)
    ├── BuiltinProvider (始终可用)
    │   ├── SQLite + FTS5 全文搜索
    │   ├── MEMORY.md (向后兼容)
    │   └── USER.md (用户画像)
    └── ExternalProvider (可选，一次注册一个)
        ├── Honcho (辩证式用户建模)
        ├── Mem0 (向量化记忆)
        └── ... (其他提供者)
```

---

## 核心组件

### 提供者接口（16 个生命周期钩子）

```python
class MemoryProvider(ABC):
    initialize()            # 连接、创建资源
    system_prompt_block()   # 静态 system prompt 文本
    prefetch(query)         # 每轮前背景召回
    sync_turn(user, asst)   # 每轮后异步写入
    on_session_end()        # 会话结束事实提取
    on_session_switch()     # 会话 ID 切换
    on_pre_compress()       # 上下文压缩前提取洞察
    on_memory_write()       # 镜像内置记忆写入
    get_tool_schemas()      # 暴露给模型的工具
    handle_tool_call()      # 分发工具调用
    shutdown()              # 清理退出
```

### FTS5 全文搜索

```python
# 搜索 "prefers tabs indentation"
SELECT name, description FROM memories
JOIN memories_fts ON memories.id = memories_fts.rowid
WHERE memories_fts MATCH 'prefers tabs indentation'
ORDER BY rank LIMIT 5;
```

### 上下文注入格式

记忆上下文通过 fenced block 注入 system prompt：

```xml
<memory-context>
[System note: The following is recalled memory context, NOT new user input.
Treat as authoritative reference data.]

- [user-prefers-tabs](user-prefers-tabs.md) — User prefers tabs (type: user)
- [project-auth-rewrite](project-auth-rewrite.md) — Auth module under rewrite (type: project)

</memory-context>
```

---

## 相对 s03 的变更

| 组件 | s03 | s04 |
|------|-----|-----|
| 存储引擎 | 单文件 MEMORY.md | SQLite + FTS5 + MEMORY.md 兼容 |
| 搜索 | 无 | FTS5 全文搜索 + LIKE 降级 |
| 提供者模型 | 无 | 抽象基类 + 内置 + 外部可插拔 |
| 生命周期 | 简单读写 | 16 个钩子方法 |
| 工具 | bash, load_skill | bash, load_skill, memory_search, memory_write |

---

## 试一下

```sh
python s04_memory_system/code.py
```

1. `Save this: the staging API is at https://api.staging.example.com`
2. `Remember that I use pytest with --cov and --tb=short`
3. `Search memory for API`
4. `/memories` 查看所有

---

## 接下来

记忆系统已经就绪。但技能只是 `.skills/` 目录下的文件，没有生命周期管理。技能会越积越多——需要 stale/archive 机制。

s05 Skill Lifecycle → active → stale → archived 状态机 + Umbrella 结构。

<details>
<summary>深入 Hermes 源码</summary>

本节对应 Hermes 生产源码中的以下文件：

- **`agent/memory_manager.py`** — 记忆提供者编排器。生产版的 `MemoryManager` 负责协调内置提供者和外部提供者，管理 16 个生命周期钩子的调用顺序。它确保内置 `BuiltinProvider`（`MEMORY.md` + `USER.md` + SQLite FTS5）始终可用，同时只允许注册一个外部提供者（防止工具 schema 膨胀）。
- **`agent/memory_provider.py`** — 记忆提供者抽象基类。定义了完整的接口契约：`initialize()`（连接/创建资源）、`system_prompt_block()`（静态系统提示）、`prefetch(query)`（每轮前背景召回）、`sync_turn(user, asst)`（每轮后异步写入）、`on_session_end()`（会话结束事实提取）、`on_pre_compress()`（压缩前提取洞察）、`get_tool_schemas()` / `handle_tool_call()`（工具暴露与分发）、`shutdown()`（清理退出）等。
- **`plugins/memory/`** — 外部提供者目录，包含 8 个可插拔实现：**Honcho**（辩证式用户建模）、**Holographic**（全息记忆存储）、**Mem0**（向量化记忆）、**Hindsight**（事后洞察）、**RetainDB**、**Supermemory**、**ByteRover**、**OpenViking**。

**教学版简化了什么**：
- 生产版有完整的抽象基类 + 16 个生命周期钩子，教学版简化为 `read()`/`write()`/`search()` 三个方法
- 生产版使用 SQLite + FTS5 做全文搜索（支持 BM25 排序），教学版使用简单字符串匹配
- 生产版支持多种记忆类型（user/feedback/project/reference）的结构化查询，教学版是扁平文本存储
- 生产版的上下文注入使用 `<memory-context>` fenced block 格式严格区分"系统参考数据"和"用户输入"，教学版使用简化格式

</details>

<!-- translation-sync: zh@v1 -->
