"""
s17: MCP Plugin — 把外部能力接入 agent 工具池

MCP (Model Context Protocol) 让外部服务以标准协议暴露工具给 agent。
Hermes 支持多传输 (stdio/SSE/streamable HTTP) + 通道路由 + 工具池统一组装。

Usage:
    python s17_mcp_plugin/code.py
"""

import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
from llm import get_client

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

MCP_DIR = Path(".hermes") / "mcp"


# ── MCP Transport Types ────────────────────────────────

class TransportType:
    STDIO = "stdio"        # 本地子进程
    SSE = "sse"            # Server-Sent Events
    STREAMABLE_HTTP = "streamable_http"


# ── MCP Server Config ──────────────────────────────────

@dataclass
class MCPServerConfig:
    """一个 MCP 服务器的配置"""
    name: str
    command: str = ""           # stdio: 启动命令
    args: list[str] = field(default_factory=list)
    url: str = ""               # sse/http: 服务器 URL
    transport: str = TransportType.STDIO
    env: dict = field(default_factory=dict)
    timeout: int = 120           # 连接超时 (秒)
    disabled: bool = False


# ── MCP Tool Registry ──────────────────────────────────

@dataclass
class MCPTool:
    """MCP 工具 — 统一格式"""
    name: str
    description: str
    input_schema: dict
    server_name: str             # 来源 MCP 服务器

    def to_agent_tool(self) -> dict:
        """转换为 agent 可用的工具定义"""
        return {
            "name": self.name,
            "description": f"[MCP:{self.server_name}] {self.description}",
            "input_schema": self.input_schema,
        }


class MCPToolPool:
    """统一的 MCP 工具池 — 所有 MCP 服务器的工具汇集于此"""

    def __init__(self):
        self._tools: dict[str, MCPTool] = {}
        self._servers: dict[str, MCPServerConfig] = {}

    def register_server(self, config: MCPServerConfig):
        self._servers[config.name] = config
        print(f"  [MCP] registered server: {config.name} ({config.transport})")

    def discover_tools(self) -> list[MCPTool]:
        """
        从所有 MCP 服务器发现工具。
        生产环境中：stdio 启动子进程 → tools/list；
                    SSE/HTTP 发 HTTP GET → 解析 tool 列表。
        这里模拟。
        """
        simulated_tools = {
            "filesystem": [
                MCPTool("fs_read", "Read a file", {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                }, "filesystem"),
                MCPTool("fs_write", "Write a file", {
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["path", "content"],
                }, "filesystem"),
            ],
            "database": [
                MCPTool("db_query", "Execute SQL query", {
                    "type": "object",
                    "properties": {"sql": {"type": "string"}},
                    "required": ["sql"],
                }, "database"),
            ],
            "web_search": [
                MCPTool("web_search", "Search the web", {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                }, "web_search"),
            ],
        }

        discovered = []
        for server_name, tools in simulated_tools.items():
            if server_name in self._servers:
                for tool in tools:
                    self._tools[tool.name] = tool
                    discovered.append(tool)
                    print(f"  [MCP:discover] {tool.name} ← {server_name}")
        return discovered

    def get_all_tools(self) -> list[dict]:
        """获取所有工具（MCP 工具 + 内置工具合并到同一个池子里）"""
        mcp_tools = [t.to_agent_tool() for t in self._tools.values()]
        return mcp_tools

    def execute(self, tool_name: str, args: dict) -> str:
        """执行 MCP 工具调用"""
        tool = self._tools.get(tool_name)
        if not tool:
            return f"Unknown MCP tool: {tool_name}"

        # 生产环境: 根据 transport 类型调用对应的 MCP 服务器
        # stdio → 向子进程的 stdin 发 JSON-RPC
        # sse/http → HTTP POST 到服务器 URL

        print(f"  [MCP:exec] {tool_name}({args}) ← {tool.server_name}")
        return f"[MCP:{tool.server_name}] executed {tool_name} with {json.dumps(args)}"


# ── MCP Manager ────────────────────────────────────────

class MCPManager:
    """MCP 管理器 — 加载配置、发现工具、路由调用"""

    def __init__(self, config_dir: Path = MCP_DIR):
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.pool = MCPToolPool()

    def load_servers_from_config(self):
        """从 ~/.hermes/mcp/servers.json 加载服务器配置"""
        config_file = self.config_dir / "servers.json"
        if not config_file.exists():
            # 写默认配置
            default_servers = [
                {
                    "name": "filesystem",
                    "command": "npx", "args": ["-y", "@anthropic/mcp-filesystem"],
                    "transport": "stdio",
                },
                {
                    "name": "web_search",
                    "url": "https://search-mcp.example.com/sse",
                    "transport": "sse",
                },
            ]
            config_file.write_text(json.dumps({"servers": default_servers}, indent=2))

        data = json.loads(config_file.read_text())
        for s in data.get("servers", []):
            config = MCPServerConfig(
                name=s["name"],
                command=s.get("command", ""),
                args=s.get("args", []),
                url=s.get("url", ""),
                transport=s.get("transport", "stdio"),
                disabled=s.get("disabled", False),
            )
            if not config.disabled:
                self.pool.register_server(config)

    def startup(self):
        """启动时发现所有 MCP 工具"""
        print("  [MCP] Starting tool discovery...")
        tools = self.pool.discover_tools()
        print(f"  [MCP] {len(tools)} tools discovered from {len(self.pool._servers)} servers")
        return tools


# ── Unified Tool Pool ──────────────────────────────────

class UnifiedToolRegistry:
    """统一工具注册表 — 内置工具 + MCP 工具在同一个池子里"""

    def __init__(self, mcp_manager: MCPManager):
        self.mcp = mcp_manager
        self._builtin_handlers = {
            "bash": lambda **kw: "bash executed",
        }

    def get_all_tools(self) -> list[dict]:
        """合并内置 + MCP 工具"""
        builtin = [{
            "name": "bash",
            "description": "Execute shell command",
            "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
        }]
        return builtin + self.mcp.pool.get_all_tools()


# ── Main ──────────────────────────────────────────────

def main():
    manager = MCPManager()
    manager.load_servers_from_config()
    tools = manager.startup()

    print("\n" + "=" * 60)
    print("s17: MCP Plugin — 把外部能力接入工具池")
    print("=" * 60)
    print(f"已注册 {len(manager.pool._servers)} 个 MCP 服务器")
    print(f"已发现 {len(tools)} 个工具")
    print()

    registry = UnifiedToolRegistry(manager)
    all_tools = registry.get_all_tools()
    print(f"统一工具池: {len(all_tools)} 个工具 (内置 + MCP)")
    for t in all_tools:
        print(f"  🔧 {t['name']}: {t['description']}")
    print()

    # 模拟工具调用
    result = manager.pool.execute("fs_read", {"path": "/tmp/test.txt"})
    print(f"  调用结果: {result}")
    result = manager.pool.execute("db_query", {"sql": "SELECT * FROM users"})
    print(f"  调用结果: {result}")
    print()
    print("MCP 设计原则:")
    print("  1. 多传输: stdio / SSE / streamable HTTP")
    print("  2. 工具池统一: 内置工具和 MCP 工具在同一个池子里")
    print("  3. 动态发现: 启动时 tools/list, 无需重启")
    print("  4. JSON-RPC: 标准协议, 语言无关")


if __name__ == "__main__":
    main()
