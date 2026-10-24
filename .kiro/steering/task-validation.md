---
title: Task validation
inclusion: always
---

# Task validation

Execute spec tasks only through the tracked `PreTaskExec` and `PostTaskExec` hooks. Supply the exact leaf-task identity from `tasks.md`; validation fails closed for malformed tasks, missing spec files, unknown or completed tasks, and incomplete prior waves.

Before finishing a task, add its narrow existing local test command to `.kiro/hooks/task-checks.json`. Do not invent commands: an absent mapping blocks completion. Post-task validation runs that target followed by the existing strict type and package checks, with bounded commands and no shell, network, secrets, telemetry, or interactive input.
