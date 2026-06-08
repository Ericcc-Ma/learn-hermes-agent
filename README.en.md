# Learn Hermes Agent — Self-Evolving Agent Harness Engineering

[中文](README.md) · [English](README.en.md)

<p align="center">
  <img src="assets/social-preview.svg" alt="Learn Hermes Agent" width="800">
</p>

<p align="center">
  <a href="https://github.com/hongye/learn-hermes-agent/actions"><img src="https://img.shields.io/github/actions/workflow/status/hongye/learn-hermes-agent/test.yml?style=flat-square" alt="CI"></a>
  <a href="https://github.com/hongye/learn-hermes-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/chapters-24-brightgreen?style=flat-square" alt="Chapters"></a>
  <a href="#"><img src="https://img.shields.io/badge/llm-anthropic%20%7C%20deepseek%20%7C%20openai%20%7C%20qwen%20%7C%20glm-7C4DFF?style=flat-square" alt="LLM"></a>
  <a href="#"><img src="https://img.shields.io/badge/languages-中文%20%7C%20English-blue?style=flat-square" alt="Languages"></a>
</p>

## Agency Comes from the Model. Self-Evolution Comes from the Harness.

An agent that perceives, reasons, and acts — that comes from model training. But an agent that **learns from every conversation, automatically distills knowledge, and improves itself over time** — that comes from the harness.

`learn-claude-code` taught you how to build the vehicle — the environment where an agent can act. This repository teaches you to build **a vehicle that evolves itself** — an agent that automatically accumulates knowledge during operation, creates skills, organizes its skill library, and gets smarter with every use.

> Rebuild the self-learning system behind Hermes Agent: make an agent remember you, learn from you, and improve with use.

## 30-Second Demo

Start with the final chapter to see the full loop:

```sh
python s12_comprehensive/code.py
```

Try this input:

```text
Stop using camelCase in Python files — I always use snake_case.
```

Continue for a few turns, then run `/insights` and `/curator`. You should see the correction distilled into memory/skills, relevant knowledge injected into later context, and the Curator previewing skill-library cleanup.

---

## What is a Self-Evolving Agent?

A regular agent starts from zero every session. Close and reopen — it remembers nothing. Mistakes you corrected last time? It makes them again. Good solutions you discovered? Lost forever.

A self-evolving agent is different:

```
Every conversation → Background Review → Extract memories/skills → Persist
                                                ↓
Next conversation → Load memories → Match skills → Agent is smarter
                     ↓
            Periodic Curator → Skill library stays clean
```

**Core idea**: Conversations aren't just about completing tasks — they're learning opportunities. Every lesson learned, every preference expressed, every pattern discovered is automatically converted into reusable knowledge assets.

---

## Hermes Self-Evolution Architecture: Six Layers

Hermes is the self-evolution subsystem. Its architecture has six layers:

```
Layer 1: Real-time Learning    — Background Review
Layer 2: Skill Management      — Skill Lifecycle
Layer 3: Long-term Maintenance — Curator System
Layer 4: Memory System         — Persistent Knowledge
Layer 5: Context Management    — Compression & Injection
Layer 6: Data Analytics        — Insights Engine
```

Each layer solves one problem. Each layer builds on the previous one.

---

## Supported LLM Providers

All chapters use a unified `llm.py` module. Switch providers by setting `LLM_PROVIDER`:

| Provider | Example Models | Env Vars |
|----------|---------------|----------|
| **Anthropic** | claude-sonnet-4-6, claude-opus-4-8 | `ANTHROPIC_API_KEY` |
| **DeepSeek** | deepseek-chat, deepseek-reasoner | `DEEPSEEK_API_KEY` |
| **OpenAI** | gpt-4o, gpt-4o-mini | `OPENAI_API_KEY` |
| **Qwen / Tongyi** | qwen-plus, qwen-max | `LLM_API_KEY` + `LLM_BASE_URL` |
| **GLM / Zhipu** | glm-4-flash, glm-4-plus | `LLM_API_KEY` + `LLM_BASE_URL` |
| **Moonshot** | moonshot-v1-8k | `LLM_API_KEY` + `LLM_BASE_URL` |
| **Ollama (local)** | llama3, qwen2.5, etc. | `LLM_BASE_URL` |

```bash
# Use DeepSeek
LLM_PROVIDER=deepseek DEEPSEEK_API_KEY=sk-... MODEL_ID=deepseek-chat python s01_agent_loop/code.py

# Use Qwen
LLM_PROVIDER=openai_compat LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 LLM_API_KEY=sk-... python s01_agent_loop/code.py
```

Any OpenAI-compatible endpoint works via `LLM_PROVIDER=openai_compat` + custom `LLM_BASE_URL`.

---

## 24 Progressive Lessons

**Each lesson adds one self-evolution mechanism. Each mechanism has a motto.**

> **s01** &nbsp; *"One loop + one memory file = the simplest learning agent"* — Agent loop + MEMORY.md, remembering user preferences
>
> **s02** &nbsp; *"After every conversation, ask 'what did I learn?'"* — Background memory review, auto-extracting memories
>
> **s03** &nbsp; *"Good solutions aren't one-offs — distill them into skills"* — Background skill review, auto-creating skills from corrections
>
> **s04** &nbsp; *"Memory shouldn't be just one file"* — Dual-layer architecture, FTS5 search, pluggable providers
>
> **s05** &nbsp; *"Skills have a lifecycle"* — active → stale → archived, pin exemption, umbrella structure
>
> **s06** &nbsp; *"What to learn, what not to learn — rules exist"* — Signal priorities, forbidden capture list, safety guardrails
>
> **s07** &nbsp; *"30 days unused → mark stale, 90 days → archive, rules decide"* — Pure-rule auto state transitions, zero LLM cost
>
> **s08** &nbsp; *"Too many skills get messy — merge them periodically"* — LLM review & merging, prefix clustering, umbrella building
>
> **s09** &nbsp; *"Context fills up — compress it, but keep the important stuff out"* — Conversation compression, trajectory compression, memory prefetch
>
> **s10** &nbsp; *"You don't know how many tokens you're using? How can you optimize?"* — Token/cost tracking, tool usage patterns
>
> **s11** &nbsp; *"Errors aren't endpoints — they're learning starting points"* — Error detection, model fallback, self-healing
>
> **s12** &nbsp; *"Six layers in place, one self-evolving agent"* — All mechanisms integrated into one complete agent

---

## Core Pattern

```python
def agent_loop(messages):
    while True:
        # 1. Pre-turn: inject relevant memories and skills
        inject_memories(messages)
        inject_skills(messages)

        response = client.messages.create(
            model=MODEL, system=build_system(),
            messages=messages, tools=TOOLS,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            # 2. Post-turn: background review, extract learning
            spawn_background_review(messages)
            return

        # 3. Execute tools
        results = execute_tools(response.content)
        messages.append({"role": "user", "content": results})
```

The loop never changes. Self-evolution mechanisms hang on before and after the loop. The model decides. The harness learns.

---

## All Chapters

| Chapter | Topic | Key Concepts |
|---|---|---|
| [s01](./s01_agent_loop/) | Agent Loop + Memory | `agent_loop` / `MEMORY.md` / persistence |
| [s02](./s02_background_memory_review/) | BG Memory Review | `BackgroundReview` / nudge / snapshot |
| [s03](./s03_background_skill_review/) | BG Skill Review | signal detection / auto-creation / priorities |
| [s04](./s04_memory_system/) | Memory System Deep Dive | FTS5 / pluggable providers / lifecycle hooks |
| [s05](./s05_skill_lifecycle/) | Skill Lifecycle | active/stale/archived / pin / umbrella |
| [s06](./s06_skill_creation/) | Skill Auto-Creation | signal priority / forbidden capture / safety |
| [s07](./s07_curator_state/) | Curator Auto Transitions | pure-rule state machine / idle trigger |
| [s08](./s08_curator_llm/) | Curator LLM Merge | prefix clustering / umbrella merge / reports |
| [s09](./s09_context_management/) | Context Management | compaction / trajectory / prefetch |
| [s10](./s10_insights/) | Insights Engine | token stats / cost analysis / patterns |
| [s11](./s11_error_recovery/) | Error Recovery | retry / fallback / self-healing |
| [s12](./s12_comprehensive/) | Complete Self-Evolving Agent | all six layers integrated |

---

## Hermes Source Map

If you want to read from the teaching code back into production Hermes, start here:

- [Hermes Source Map](docs/hermes-source-map.md) — how the 12 lessons map to the core files in `NousResearch/hermes-agent`
- [FAQ](docs/faq.md) — positioning, reading order, API keys, and why the teaching version simplifies production mechanisms

Shortest path: run `s12_comprehensive/code.py` first, then use the source map to read `run_agent.py`, `agent/background_review.py`, `agent/curator.py`, and `agent/memory_manager.py`.

---

## Learning Path

Main line: remember → learn → manage knowledge → curate → analyze → self-heal → complete evolution

```mermaid
flowchart TD
    classDef stage1 fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#0D47A1,rx:12,ry:12,text-align:left
    classDef stage2 fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#1B5E20,rx:12,ry:12,text-align:left
    classDef stage3 fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#E65100,rx:12,ry:12,text-align:left
    classDef stage4 fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px,color:#4A148C,rx:12,ry:12,text-align:left

    subgraph Phase1 ["🌱 Phase 1: Foundation (Memory + Learning)"]
        direction LR
        S1["<b>1. Let Agent Remember</b><br/>━━━━━━━━━━━━━<br/><b>s01 Agent Loop + Memory</b><br/>└─ loop + MEMORY.md<br/><br/><b>s02 BG Memory Review</b><br/>└─ auto-extract memories"]:::stage1
        S2["<b>2. Let Agent Learn</b><br/>━━━━━━━━━━━━━<br/><b>s03 BG Skill Review</b><br/>└─ create skills from corrections<br/><br/><b>s04 Memory System</b><br/>└─ FTS5 + pluggable providers"]:::stage2
        S1 ==> S2
    end

    subgraph Phase2 ["🚀 Phase 2: Advanced Evolution (Manage + Curate + Analyze + Heal)"]
        direction LR
        S3["<b>3. Manage Knowledge</b><br/>━━━━━━━━━━━━━<br/><b>s05 Skill Lifecycle</b><br/>└─ state machine + umbrella<br/><br/><b>s06 Skill Creation Rules</b><br/>└─ priorities + safety"]:::stage3
        S4["<b>4. Curate + Integrate</b><br/>━━━━━━━━━━━━━<br/><b>s07-s08 Curator</b><br/>└─ auto transitions + LLM merge<br/><br/><b>s09 Context Mgmt</b><br/>└─ compact + prefetch<br/><br/><b>s10-11 Insights + Recovery</b><br/>└─ analytics + self-healing<br/><br/><b>s12 Complete Agent</b><br/>└─ all six layers integrated"]:::stage4
        S3 ==> S4
    end
    Phase1 ==> Phase2
```

---

## How to Read

Each chapter is a folder containing:

```
s04_memory_system/
  README.md              # Chinese source (complete narrative)
  README.en.md           # English translation
  code.py                # standalone runnable implementation
  images/                # SVG diagrams
```

Read from s01 through s12 in order. Each chapter assumes previous chapters and ends with a hook to the next.

---

## Quick Start

```sh
git clone <learn-hermes-agent-repo>
cd learn-hermes-agent
pip install -r requirements.txt
cp .env.example .env   # Edit: choose LLM_PROVIDER and fill API key

# Use Anthropic (default)
python s01_agent_loop/code.py

# Use DeepSeek
LLM_PROVIDER=deepseek DEEPSEEK_API_KEY=sk-... MODEL_ID=deepseek-chat python s01_agent_loop/code.py

# Use Qwen
LLM_PROVIDER=openai_compat LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 LLM_API_KEY=sk-... python s01_agent_loop/code.py
```

---

## Relationship with learn-claude-code

`learn-claude-code` teaches harness fundamentals — loops, tools, permissions, sub-agents, task systems. This repository assumes you understand those basics and focuses on the **self-evolution layer**.

```
learn-claude-code                   learn-hermes-agent
(agent harness basics:              (self-evolving harness:
 loop, tools, permissions,           background review, skill lifecycle,
 sub-agents, task system,            curator, memory system, insights)
 worktree isolation)
```

The two repositories are complementary. Together they cover the full harness engineering spectrum from "can act" to "can evolve."

---

## Project Structure

```
learn-hermes-agent/
  llm.py                        # Unified LLM provider (Anthropic/DeepSeek/OpenAI/etc.)
  s01_agent_loop/               # Agent Loop + Basic Memory
  s02_background_memory_review/ # Background Memory Review
  s03_background_skill_review/  # Background Skill Review
  s04_memory_system/            # Memory System Deep Dive
  s05_skill_lifecycle/          # Skill Lifecycle Management
  s06_skill_creation/           # Skill Auto-Creation Rules
  s07_curator_state/            # Curator Auto State Transitions
  s08_curator_llm/              # Curator LLM Review & Merge
  s09_context_management/       # Context Management
  s10_insights/                 # Insights Analytics Engine
  s11_error_recovery/           # Error Recovery & Self-Healing
  s12_comprehensive/            # Complete Self-Evolving Agent
  skills/                       # Example skill files
  tests/                        # Tests
```

---

## License

MIT

---

**Agency comes from the model. Self-evolution comes from the harness. Every conversation is a learning opportunity. Knowledge learned is automatically distilled into reusable skills and memories.**

**Build the harness that learns. The model will do the rest.**
