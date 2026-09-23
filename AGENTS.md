# Superpowers for AI Agents

## Core Instruction

You MUST read and follow `skills/using-superpowers/SKILL.md` before taking any action.

## Rule Zero

**Invoke relevant skills BEFORE any response or action.** This includes clarifying questions, code exploration, or any other task.

## Available Skills

- `superpowers:using-superpowers` — Startup skill, mandatory
- `superpowers:brainstorming` — Design before coding
- `superpowers:writing-plans` — Implementation planning
- `superpowers:test-driven-development` — TDD mandatory
- `superpowers:using-git-worktrees` — Isolated workspaces
- `superpowers:subagent-driven-development` — Subagent execution
- `superpowers:executing-plans` — Plan execution
- `superpowers:requesting-code-review` — Code review
- `superpowers:finishing-a-development-branch` — Completion workflow
- `superpowers:systematic-debugging` — Root cause debugging
- `superpowers:verification-before-completion` — Evidence-based claims
- `superpowers:receiving-code-review` — Technical feedback handling
- `superpowers:dispatching-parallel-agents` — Parallel investigation
- `superpowers:writing-skills` — Skill creation

## Quick Reference

| Task | Skill to Use |
|------|--------------|
| "Let's build X" | brainstorming → writing-plans → TDD |
| "Fix this bug" | systematic-debugging → TDD |
| "Implement feature" | test-driven-development |
| "Code review" | requesting-code-review |
| "Done with task" | finishing-a-development-branch |
| "Claim success" | verification-before-completion |