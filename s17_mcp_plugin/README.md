# s17: MCP Plugin — 把外部能力接入工具池

[中文](README.md) · [English](README.en.md)

s01 → ... → s16 → `s17` → [s18](../s18_full_hermes/)
> *"能力不够？接上 MCP"* — 多传输 + 通道路由 + 工具池统一组装。
>
> **Hermes 特性**: MCP 协议 — 标准化的外部工具接入。

---

## 问题

Agent 的内置工具有限——bash、文件读写、搜索。但用户可能需要：
- 数据库查询（PostgreSQL / MySQL）
- 文件系统操作（远程服务器）
- Web 搜索
- 第三方 API（GitHub、Jira、Slack）

每个工具都自己写 adapter？工作量大且不标准。

---

## 解决方案

**MCP (Model Context Protocol)** — 标准化协议，让任何服务以统一接口暴露工具给 agent。

### 三种传输方式

| 传输 | 场景 | 原理 |
|------|------|------|
| **stdio** | 本地工具 | 启动子进程，通过 stdin/stdout 通信 |
| **SSE** | 远程服务 | HTTP Server-Sent Events 推送 |
| **Streamable HTTP** | 云服务 | HTTP 双向流 |

### 工具池统一

```
内置工具 (bash, read, write, ...)
    +
MCP 工具 (fs_read, db_query, web_search, ...)
    =
统一的 TOOLS 数组 → 全部发给 LLM
```

Agent 不关心工具来自哪里——是内置的还是 MCP 的，对 LLM 来说都是同一个 `tools` 数组里的条目。

### JSON-RPC 通信

```
Agent: {"method": "tools/call", "params": {"name": "db_query", "arguments": {"sql": "SELECT ..."}}}
    ↓
MCP Server (database): 执行 SQL, 返回结果
    ↓
Agent: 收到 {"result": "[{'id': 1, 'name': 'Alice'}, ...]"}
```

---

## 配置示例

```json
{
  "servers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-filesystem"],
      "transport": "stdio"
    },
    {
      "name": "web_search",
      "url": "https://search-mcp.example.com/sse",
      "transport": "sse"
    }
  ]
}
```

---

## 试一下

```sh
python s17_mcp_plugin/code.py
```

观察：MCP 服务器注册 → 工具发现 → 统一工具池 → 模拟调用。

---

## 接下来

最后一章——把 18 章的所有机制整合到一个完整的 Hermes agent 里。

s18 Full Hermes → Agent Loop + Memory + Background Review + Skill Lifecycle + Curator + Context + Insights + Error Recovery + Cron + Gateway + Profiles + Teams + MCP。

<!-- translation-sync: zh@v1 -->
