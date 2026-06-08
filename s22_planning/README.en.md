# s22: Planning System — Without A Plan, The Agent Wanders

[中文](README.md) · [English](README.en.md)

s01 → ... → s21 → `s22` → [s23](../s23_autonomous/) → s24
> *"An agent without a plan wanders"* — TodoWrite + dependency graph + status tracking improves completion.
>
> **Harness Foundation**: Planning — structure complex work before execution.

---

## Problem

When the agent receives a task like "implement user authentication", starting immediately often misses steps, dependencies, tests, or deployment requirements.

Complex tasks need a visible plan.

---

## Solution

![Planning DAG](images/planning-dag.svg)

The planning system represents work as tasks with status and dependencies. A task can be blocked by earlier tasks. When dependencies finish, the next task becomes claimable.

This turns a vague goal into a graph the agent and user can inspect.

---

## Core Mechanisms

### TodoWrite

The agent writes and updates explicit tasks before and during execution.

### Dependency Graph

`blocked_by` encodes ordering constraints such as "tests depend on implementation".

### Status Tracking

Tasks move through pending, in progress, blocked, and completed states.

---

## Try It

```sh
python s22_planning/planning.py
```

Create a task DAG, complete prerequisites, and observe how blocked tasks unlock.

---

## What The Teaching Version Simplifies

- Production tasks persist across sessions and agents.
- Production records both `blockedBy` and `blocks`.
- Production active form describes what a task is doing right now.
- Production task agents can claim and execute tasks independently.

<!-- translation-sync: en@v1 -->
