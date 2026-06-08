"""
s15: Multi-Profile System — 一套代码，多套配置

Hermes 的 profile 系统让一个 agent 实例跑多套完全独立的配置:
不同模型、不同 skill 集合、不同权限、不同平台绑定。

Usage:
    python s15_profiles/code.py
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
from llm import get_client

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

HERMES_DIR = Path(".hermes")
PROFILES_DIR = HERMES_DIR / "profiles"

# ── Profile Schema ─────────────────────────────────────

@dataclass
class ProfileConfig:
    """一个 profile 的完整配置"""
    name: str                          # profile 名称 (default, work, personal, ...)
    model: str = ""                    # 覆盖全局 model
    system_prompt: str = ""            # 自定义 system prompt
    skills: list[str] = field(default_factory=list)     # 启用的技能
    disabled_toolsets: list[str] = field(default_factory=list)  # 禁用的工具集
    platforms: list[str] = field(default_factory=list)  # 绑定的平台
    gateway_enabled: bool = True       # 是否启动独立 gateway
    parent: str = ""                   # 继承自哪个 profile
    env_overrides: dict = field(default_factory=dict)   # 环境变量覆盖

    def to_dict(self) -> dict:
        return {
            "name": self.name, "model": self.model,
            "system_prompt": self.system_prompt, "skills": self.skills,
            "disabled_toolsets": self.disabled_toolsets,
            "platforms": self.platforms,
            "gateway_enabled": self.gateway_enabled,
            "parent": self.parent, "env_overrides": self.env_overrides,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProfileConfig":
        return cls(**{k: d.get(k, "" if k not in ("skills", "disabled_toolsets", "platforms", "env_overrides") else [])
                       for k in ["name", "model", "system_prompt", "skills", "disabled_toolsets",
                                  "platforms", "gateway_enabled", "parent", "env_overrides"]})


# ── Profile Manager ────────────────────────────────────

class ProfileManager:
    """Profile 管理器 — 创建、切换、继承"""

    def __init__(self, profiles_dir: Path = PROFILES_DIR):
        self.profiles_dir = profiles_dir
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._profiles: dict[str, ProfileConfig] = {}
        self.active_profile: str = "default"
        self._load_all()

    def _load_all(self):
        """加载所有 profile"""
        self._profiles.clear()
        for d in sorted(self.profiles_dir.iterdir()):
            if d.is_dir():
                config_file = d / "config.json"
                if config_file.exists():
                    profile = ProfileConfig.from_dict(json.loads(config_file.read_text()))
                    self._profiles[profile.name] = profile
        # 确保 default 存在
        if "default" not in self._profiles:
            self._profiles["default"] = ProfileConfig(name="default", model=MODEL)

    def create(self, name: str, **kwargs) -> ProfileConfig:
        """创建新 profile"""
        profile = ProfileConfig(name=name, **kwargs)
        profile_dir = self.profiles_dir / name
        profile_dir.mkdir(exist_ok=True)
        (profile_dir / "config.json").write_text(
            json.dumps(profile.to_dict(), indent=2, ensure_ascii=False))
        self._profiles[name] = profile
        print(f"  [Profile] created '{name}'")
        return profile

    def resolve(self, name: str) -> ProfileConfig:
        """解析 profile（含继承链）"""
        if name not in self._profiles:
            print(f"  [Profile] '{name}' not found, using default")
            name = "default"

        profile = self._profiles[name]

        # 继承: 如果指定了 parent，先解析 parent 的配置
        if profile.parent and profile.parent in self._profiles:
            parent = self.resolve(profile.parent)
            # 合并: 子 profile 的字段覆盖父 profile
            if not profile.model:
                profile.model = parent.model
            if not profile.system_prompt:
                profile.system_prompt = parent.system_prompt
            profile.skills = list(set(parent.skills + profile.skills))
            profile.disabled_toolsets = list(set(parent.disabled_toolsets + profile.disabled_toolsets))

        return profile

    def switch(self, name: str):
        """切换到指定 profile"""
        profile = self.resolve(name)
        self.active_profile = name
        # 生产环境: 这里会更新环境变量、重新加载 MCP 连接等
        os.environ["HERMES_PROFILE"] = name
        print(f"  [Profile] switched to '{name}'")
        print(f"    Model: {profile.model or '(default)'}")
        print(f"    Skills: {profile.skills or '(all)'}")
        print(f"    Platforms: {profile.platforms or '(all)'}")

    def list_all(self) -> list[ProfileConfig]:
        return list(self._profiles.values())

    def get_active(self) -> ProfileConfig:
        return self.resolve(self.active_profile)


# ── Per-Profile Gateway ────────────────────────────────

class ProfileGateway:
    """每个 profile 可以启动独立的 gateway 实例"""

    def __init__(self, profile: ProfileConfig):
        self.profile = profile
        self._running = False

    def start(self):
        if not self.profile.gateway_enabled:
            print(f"  [ProfileGateway] '{self.profile.name}' gateway disabled")
            return False
        self._running = True
        print(f"  [ProfileGateway] '{self.profile.name}' started")
        print(f"    Platforms: {self.profile.platforms or 'all'}")
        print(f"    Skills: {self.profile.skills or 'all'}")
        return True

    def stop(self):
        self._running = False


# ── Use Cases ──────────────────────────────────────────

def demo_profiles():
    """演示多 profile 的使用场景"""
    manager = ProfileManager()

    # 场景 1: 工作 profile — 用公司模型, 限制工具
    manager.create(
        "work",
        model="claude-opus-4-8",
        skills=["code-review", "deploy-checklist"],
        disabled_toolsets=["social_media", "entertainment"],
        platforms=["slack", "api_server"],
    )

    # 场景 2: 个人 profile — 继承 work, 添加个人 skill
    manager.create(
        "personal",
        model="deepseek-chat",
        skills=["personal-notes", "home-automation"],
        parent="work",  # 继承 work 的限制
        platforms=["telegram", "discord"],
    )

    # 场景 3: cron 专用 profile — 轻量模型, 仅 cron 工具
    manager.create(
        "cron-worker",
        model="claude-haiku-4-5",
        disabled_toolsets=["messaging", "clarify", "cronjob"],
        gateway_enabled=False,
    )

    print("\n所有 profiles:")
    for p in manager.list_all():
        parent_info = f" (extends '{p.parent}')" if p.parent else ""
        print(f"  📁 {p.name}{parent_info}: model={p.model or '(default)'}, "
              f"platforms={p.platforms or '(all)'}")

    return manager


# ── Main ──────────────────────────────────────────────

def main():
    manager = demo_profiles()

    print("\n" + "=" * 60)
    print("s15: Multi-Profile System — 一套代码，多套配置")
    print("=" * 60)
    print()
    print("Profile 设计原则:")
    print("  1. 每个 profile 独立配置（模型、技能、平台、工具）")
    print("  2. 继承链: profile A extends B → A 覆盖 B 的字段")
    print("  3. 每个 profile 可启动独立 gateway 实例")
    print("  4. Cron 任务可以绑定特定 profile")
    print()
    print("/switch <name>   — 切换 profile")
    print("/active          — 查看当前 profile")
    print("/list            — 列出所有 profile")
    print("/create <name>   — 创建新 profile")
    print("/exit            — 退出")
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
            break
        if query == "/list":
            for p in manager.list_all():
                active = " ← current" if p.name == manager.active_profile else ""
                print(f"  [{p.name}]{active}: model={p.model or '(default)'}")
            print()
        elif query.startswith("/switch "):
            manager.switch(query.split()[-1])
            print()
        elif query == "/active":
            p = manager.get_active()
            print(json.dumps(p.to_dict(), indent=2, ensure_ascii=False))
            print()
        elif query.startswith("/create "):
            manager.create(query.split()[-1])
            print()
        else:
            print(f"  Unknown: {query}")
            print()


if __name__ == "__main__":
    main()
