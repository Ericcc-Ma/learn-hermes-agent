# s23: Autonomous Agents — Watch The Board, Claim Work

[中文](README.md) · [English](README.en.md)

s01 → ... → s22 → `s23` → [s24](../s24_system_prompt/)
> *"Teammates watch the board and claim work themselves"* — idle loop + skill matching + autonomous claiming.
>
> **Harness Foundation**: Autonomous Agents — self-organizing multi-agent execution.

---

## Problem

In s16, a leader assigns work to workers. The leader becomes a bottleneck: it must know each worker's skills, who is busy, and which task is ready.

Can workers claim tasks themselves?

---

## Solution

![Autonomous Agents](images/autonomous-agents.svg)

Each agent runs an idle loop:

1. Scan the shared task board.
2. Check whether any open task matches its skills.
3. Claim one task.
4. Execute it.
5. Update status and heartbeat.

This creates a self-organizing team where workers pull work instead of waiting for assignment.

---

## Core Mechanisms

### Idle Loop

Agents periodically inspect the board when they are not busy.

### Skill Matching

Agents claim only tasks they believe they can handle.

### Heartbeats

If an agent disappears, its task can be released back to the board.

---

## Try It

```sh
python s23_autonomous/autonomous.py
```

Start multiple mock agents and watch them scan, claim, execute, and release work.

---

## What The Teaching Version Simplifies

- Production autonomous agents can run as background processes.
- Production heartbeats need robust timeout handling.
- Production skill matching can use semantic descriptions and loaded skill context.
- Production autonomous behavior must integrate with permissions and worktrees.

<!-- translation-sync: en@v1 -->
