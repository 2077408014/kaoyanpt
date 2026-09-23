# Superpowers — Project Integration

## IMPORTANT: Read skills/using-superpowers/SKILL.md FIRST

Before doing ANYTHING in this project, you MUST read and follow the `using-superpowers` skill. It establishes the mandatory rule: **invoke relevant skills BEFORE any response or action**.

## Core Rule

**You MUST check for applicable skills before responding.** If even a 1% chance exists that a skill applies, you MUST invoke it. This is non-negotiable.

## How to Use Superpowers in This Project

### When Starting a Conversation
1. Read `skills/using-superpowers/SKILL.md`
2. Follow its rules — invoke skills before any action

### When Building Something
- "Let's build X" → Invoke `superpowers:brainstorming` first
- After design approved → Invoke `superpowers:writing-plans`
- When executing plan → Use `superpowers:subagent-driven-development` or `superpowers:executing-plans`
- During implementation → `superpowers:test-driven-development` is MANDATORY
- After tasks → `superpowers:requesting-code-review` between tasks
- When complete → `superpowers:finishing-a-development-branch`

### When Fixing Bugs
- "Fix this bug" → Invoke `superpowers:systematic-debugging` first
- Before claiming fixed → `superpowers:verification-before-completion`

### When Receiving Feedback
- "Review comments:" → Invoke `superpowers:receiving-code-review`

## Available Skills

| Skill | Description |
|-------|-------------|
| `using-superpowers` | Mandatory startup skill — establishes skill invocation rules |
| `brainstorming` | Must use before any creative work — explores requirements and design |
| `writing-plans` | Creates detailed implementation plans from specs |
| `test-driven-development` | Enforces RED-GREEN-REFACTOR — NO CODE WITHOUT FAILING TEST FIRST |
| `using-git-worktrees` | Sets up isolated workspace for feature development |
| `subagent-driven-development` | Executes plans via fresh subagent per task |
| `executing-plans` | Executes plans with review checkpoints |
| `requesting-code-review` | Dispatches code reviewer subagent |
| `finishing-a-development-branch` | Guides completion: merge/PR/keep/discard |
| `systematic-debugging` | 4-phase root cause investigation — NO FIXES WITHOUT INVESTIGATION |
| `verification-before-completion` | Evidence before claims — run verification commands first |
| `receiving-code-review` | Technical evaluation of feedback — no performative agreement |
| `dispatching-parallel-agents` | Parallel investigation of independent issues |
| `writing-skills` | TDD for creating/editing skills |

## Workflow Summary

```
User request → Check skills → Invoke appropriate skill
                                      ↓
                    brainstorming → writing-plans → implementation
                                            ↓
                               subagent-driven-development / executing-plans
                                            ↓
                                    test-driven-development (mandatory)
                                            ↓
                              requesting-code-review → finishing-a-development-branch
```

## Non-Negotiable Rules

1. **NO CODE BEFORE DESIGN:** Always brainstorm and get approval first
2. **NO CODE BEFORE TEST:** TDD is mandatory — write failing test first
3. **NO COMPLETION BEFORE VERIFICATION:** Always run tests and verify before claiming success
4. **NO FIXES BEFORE INVESTIGATION:** Use systematic-debugging for all bugs

## File Structure

```
KaoYanXT/
├── skills/                # Superpowers skills library
│   ├── using-superpowers/
│   ├── brainstorming/
│   ├── writing-plans/
│   ├── test-driven-development/
│   ├── using-git-worktrees/
│   ├── subagent-driven-development/
│   ├── executing-plans/
│   ├── requesting-code-review/
│   ├── finishing-a-development-branch/
│   ├── systematic-debugging/
│   ├── verification-before-completion/
│   ├── receiving-code-review/
│   ├── dispatching-parallel-agents/
│   └── writing-skills/
├── docs/superpowers/      # Generated documentation
│   ├── specs/             # Design documents
│   └── plans/             # Implementation plans
└── .gitignore
```

## Final Note

This is a **project-level integration** of Superpowers. The skills are designed to be read and followed by AI agents during development. When you (as the AI agent) start working on this project, you MUST follow the `using-superpowers` skill's rules — invoke skills before taking any action.