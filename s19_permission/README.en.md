# s19: Permission System — Set Boundaries Before Freedom

[中文](README.md) · [English](README.en.md)

s01 → ... → s18 → `s19` → [s20](../s20_hooks/) → ... → s24
> *"Set boundaries first, then grant freedom"* — a four-layer permission pipeline decides whether a tool call can run.
>
> **Harness Foundation**: Permission — the first safety boundary for an agent with real tools.

---

## Problem

An agent with shell access can run dangerous commands: delete files, escalate privileges, force-push history, or transmit secrets.

The model should decide what it wants to do, but the harness must decide whether that action is allowed.

---

## Solution

![Permission Pipeline](images/permission-pipeline.svg)

The permission pipeline checks each operation in order:

1. **DENY**: hard block dangerous operations.
2. **ASK_USER**: require confirmation for risky operations.
3. **SANDBOX**: run in a restricted environment.
4. **ALLOW**: execute safe operations directly.

Rules are ordered. The first matching rule wins.

---

## Core Mechanisms

### Rule Priority

Specific denies must appear before broad allows.

### Session Memory

Approved commands can be remembered for the session so the user is not asked repeatedly.

### Trust Boundary

The model proposes actions. The harness enforces the boundary.

---

## Try It

```sh
python s19_permission/permission.py
```

Try safe commands, denied commands, sandboxed commands, and commands that require user approval.

---

## What The Teaching Version Simplifies

- Production permission rules consider files, networks, credentials, and platform state.
- Production approvals integrate with UI flows.
- Production sandboxing may use process, filesystem, or container boundaries.
- Production tracks trust decisions across more contexts.

<!-- translation-sync: en@v1 -->
