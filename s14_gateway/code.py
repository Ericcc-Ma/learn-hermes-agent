"""
s14: Gateway — 多平台消息网关

Hermes gateway 是多平台消息路由 + delivery 分发 + session 管理的统一入口。
原理: 平台 adapter → 消息标准化 → agent 处理 → delivery 路由返回。

Usage:
    python s14_gateway/code.py
"""

import json
import os
import subprocess
import threading
import time
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
from llm import get_client

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

HERMES_DIR = Path(".hermes")
GATEWAY_DIR = HERMES_DIR / "gateway"


# ── Platform Types ─────────────────────────────────────

class Platform(Enum):
    CLI = "cli"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    API = "api_server"
    CRON = "cron"


# ── Message Model ──────────────────────────────────────

@dataclass
class GatewayMessage:
    """网关统一消息格式 — 所有平台的消息都标准化为此格式"""
    platform: Platform
    channel_id: str        # 来源频道/会话 ID
    user_id: str           # 发送者 ID
    text: str              # 消息文本
    message_id: str = ""   # 平台消息 ID
    reply_to: str = ""     # 回复目标
    attachments: list = field(default_factory=list)
    timestamp: str = ""


# ── Session Store ──────────────────────────────────────

@dataclass
class SessionRecord:
    session_id: str
    platform: Platform
    channel_id: str
    user_id: str
    messages: list = field(default_factory=list)
    created_at: str = ""
    last_active: str = ""
    reset_policy: str = "manual"  # manual | daily | per_message


class SessionStore:
    """会话管理 — 跨平台保持对话连续性"""

    def __init__(self, store_dir: Path = GATEWAY_DIR / "sessions"):
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, SessionRecord] = {}

    def get_or_create(self, platform: Platform, channel_id: str, user_id: str) -> SessionRecord:
        key = f"{platform.value}:{channel_id}:{user_id}"
        if key not in self._sessions:
            now = datetime.now().isoformat()
            self._sessions[key] = SessionRecord(
                session_id=str(uuid.uuid4())[:8],
                platform=platform,
                channel_id=channel_id,
                user_id=user_id,
                created_at=now,
                last_active=now,
            )
        return self._sessions[key]

    def touch(self, session: SessionRecord):
        session.last_active = datetime.now().isoformat()

    def reset(self, session: SessionRecord):
        """重置会话上下文"""
        session.messages = []
        session.last_active = datetime.now().isoformat()


# ── Delivery Router ────────────────────────────────────

class DeliveryRouter:
    """消息投递路由 — 把 agent 回复送回正确的平台和频道"""

    def __init__(self):
        self._adapters: dict[Platform, "BaseAdapter"] = {}

    def register(self, platform: Platform, adapter: "BaseAdapter"):
        self._adapters[platform] = adapter
        print(f"  [Gateway] registered adapter: {platform.value}")

    def deliver(self, platform: Platform, channel_id: str, text: str, reply_to: str = "") -> bool:
        adapter = self._adapters.get(platform)
        if adapter:
            return adapter.send(channel_id, text, reply_to)
        print(f"  [Gateway] no adapter for {platform.value}")
        return False


# ── Platform Adapter (Base) ────────────────────────────

class BaseAdapter:
    """平台适配器基类 — 每个平台实现自己的收发逻辑"""

    def __init__(self, platform: Platform):
        self.platform = platform

    def send(self, channel_id: str, text: str, reply_to: str = "") -> bool:
        """发送消息到平台"""
        raise NotImplementedError

    def receive(self) -> list[GatewayMessage]:
        """从平台拉取新消息"""
        raise NotImplementedError


class CLIAdapter(BaseAdapter):
    """CLI 适配器 — 终端输入输出"""

    def __init__(self):
        super().__init__(Platform.CLI)

    def send(self, channel_id: str, text: str, reply_to: str = "") -> bool:
        print(f"\n[Agent]: {text}")
        return True

    def receive(self) -> list[GatewayMessage]:
        return []  # CLI 是同步的，由主循环直接处理


class CronAdapter(BaseAdapter):
    """Cron 适配器 — 定时任务结果投递"""

    def __init__(self):
        super().__init__(Platform.CRON)

    def send(self, channel_id: str, text: str, reply_to: str = "") -> bool:
        # Cron 结果写入 output 目录
        output_dir = HERMES_DIR / "cron" / "output" / channel_id
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        (output_dir / f"{ts}.md").write_text(f"# Cron Result\n\n{text}", encoding="utf-8")
        print(f"  [Gateway:Cron] result saved for {channel_id}")
        return True


class TelegramAdapter(BaseAdapter):
    """Telegram 适配器（模拟）"""

    def __init__(self, bot_token: str = ""):
        super().__init__(Platform.TELEGRAM)
        self.bot_token = bot_token

    def send(self, channel_id: str, text: str, reply_to: str = "") -> bool:
        print(f"  [Telegram → {channel_id}]: {text[:100]}...")
        # 生产环境: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", ...)
        return True

    def receive(self) -> list[GatewayMessage]:
        # 生产环境: 长轮询 getUpdates
        return []


# ── Gateway Runner ─────────────────────────────────────

class GatewayRunner:
    """Gateway 主运行器 — 协调所有平台的消息收发"""

    def __init__(self):
        self.router = DeliveryRouter()
        self.sessions = SessionStore()
        self.adapters: dict[Platform, BaseAdapter] = {}
        self._running = False

    def register_platform(self, adapter: BaseAdapter):
        self.adapters[adapter.platform] = adapter
        self.router.register(adapter.platform, adapter)

    def start(self):
        """启动 gateway"""
        print("\n  ═══ Gateway Started ═══")
        self._running = True

        # 至少注册 CLI + Cron
        self.register_platform(CLIAdapter())
        self.register_platform(CronAdapter())

    def process_message(self, msg: GatewayMessage) -> str:
        """处理一条消息: 路由到 agent，返回回复"""
        session = self.sessions.get_or_create(msg.platform, msg.channel_id, msg.user_id)
        self.sessions.touch(session)

        # 组装上下文提示
        context = f"[Platform: {msg.platform.value}] [Channel: {msg.channel_id}]"
        full_prompt = f"{context}\n\n{msg.text}"

        try:
            response = CLIENT.messages.create(
                model=MODEL,
                system="You are Hermes agent. Respond helpfully.",
                messages=[{"role": "user", "content": full_prompt}],
                max_tokens=1000,
            )
            text = response.content[0].get("text", "") if response.content else ""
        except Exception as e:
            text = f"Error: {e}"

        # Delivery 分发
        self.router.deliver(msg.platform, msg.channel_id, text, msg.message_id)
        return text

    def stop(self):
        self._running = False
        print("  ═══ Gateway Stopped ═══")


# ── Context Injection ──────────────────────────────────

def build_session_context(session: SessionRecord) -> str:
    """构建注入 agent 的会话上下文"""
    return f"""<gateway-context>
Platform: {session.platform.value}
Channel: {session.channel_id}
User: {session.user_id}
Session: {session.session_id}
</gateway-context>"""


# ── Main ──────────────────────────────────────────────

def main():
    # 初始化 gateway
    gateway = GatewayRunner()
    gateway.start()

    print("=" * 60)
    print("s14: Gateway — 多平台消息网关")
    print("=" * 60)
    print("已注册平台:")
    for p, a in gateway.adapters.items():
        print(f"  ✅ {p.value} ({type(a).__name__})")
    print()
    print("Gateway 原理:")
    print("  1. 各平台 adapter 接收消息")
    print("  2. 标准化为 GatewayMessage")
    print("  3. Session 管理（跨平台会话连续性）")
    print("  4. Agent 处理并生成回复")
    print("  5. Delivery router 投递回复到正确平台")
    print()
    print("/telegram — 注册 Telegram adapter")
    print("/send <msg> — 模拟发送一条消息")
    print("/status  — 查看 gateway 状态")
    print("/exit    — 退出")
    print()

    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue
        if query == "/exit":
            gateway.stop()
            break
        if query == "/telegram":
            gateway.register_platform(TelegramAdapter(bot_token="demo"))
            continue
        if query == "/status":
            print(f"  Running: {gateway._running}")
            print(f"  Platforms: {list(gateway.adapters.keys())}")
            print(f"  Sessions: {len(gateway.sessions._sessions)}")
            print()
            continue
        if query.startswith("/send "):
            text = query[6:]
            msg = GatewayMessage(
                platform=Platform.CLI,
                channel_id="demo-channel",
                user_id="demo-user",
                text=text,
                timestamp=datetime.now().isoformat(),
            )
            reply = gateway.process_message(msg)
            print()
            continue

        # 默认: 通过 CLI adapter 处理
        msg = GatewayMessage(
            platform=Platform.CLI,
            channel_id="terminal",
            user_id="user",
            text=query,
            timestamp=datetime.now().isoformat(),
        )
        gateway.process_message(msg)
        print()


if __name__ == "__main__":
    main()
