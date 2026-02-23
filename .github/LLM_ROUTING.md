# LLM Issue Routing Protocol

This repository uses GitHub labels (not assignees) to route implementation and review work to different LLM workers.

This document is the shared contract for human contributors, Codex, Claude Code, Gemini CLI, Kimi, MiniMax, and automations.

## Goal

- Make issue ownership and review responsibility machine-readable
- Allow multiple LLMs to work in parallel safely
- Reduce collisions via a simple queue state machine

## LLM Identities

Supported worker IDs (use exact values):

- `claude`
- `gemini`
- `kimi`
- `minimax`

## Labels

### Owner Labels (exactly one expected)

- `llm-owner:claude`
- `llm-owner:gemini`
- `llm-owner:kimi`
- `llm-owner:minimax`

### Reviewer Labels (one or more allowed)

- `llm-reviewer:claude`
- `llm-reviewer:gemini`
- `llm-reviewer:kimi`
- `llm-reviewer:minimax`

### Queue Labels (exactly one expected)

- `queue:ready-impl` : ready for implementation
- `queue:claimed` : claimed by a worker (lease active)
- `queue:in-pr` : PR opened / implementation in progress
- `queue:ready-review` : implementation complete, ready for reviewer
- `queue:blocked` : waiting on dependency/decision
- `queue:needs-human` : requires human judgment/approval
- `queue:done` : merged/resolved

Rule: keep exactly one `queue:*` label on each issue.

## Claim Protocol (Implementation or Review)

Before claiming:

1. Read current labels and recent comments.
2. Do not claim if issue already has `queue:claimed` or `queue:in-pr`, unless lease is expired.
3. If blocked, do not claim unless blocker is resolved.

To claim:

1. Move queue label to `queue:claimed`
2. Add a claim comment using the machine-readable template below

Claim comment template:

```text
[bot-claim]
worker=<claude|gemini|kimi|minimax>
role=<implementer|reviewer>
claimed_at=<ISO8601 UTC>
lease_hours=24
branch=<optional-branch-name>
```

## Lease / Reclaim Rules

- Default lease: `24` hours
- A claim is considered active if:
  - issue has `queue:claimed` or `queue:in-pr`, and
  - there is a recent claim/progress comment within lease window
- Another worker may reclaim only if lease expired and there is no active progress

## Queue Transitions

Common transitions:

- `queue:ready-impl` -> `queue:claimed` (worker claims implementation)
- `queue:claimed` -> `queue:in-pr` (PR opened)
- `queue:in-pr` -> `queue:ready-review` (implementation complete, reviewer requested)
- `queue:ready-review` -> `queue:claimed` (reviewer claims review)
- `queue:claimed` -> `queue:needs-human` (review blocked by product/security decision)
- `queue:needs-human` -> `queue:ready-impl` (human resolved question)
- `queue:ready-review` -> `queue:done` (merged/resolved)

## Recommended Routing (Project Default)

These are defaults, not hard rules.

### Implementers

- `security` or complex backend/data-model changes -> `claude`
- CI / DX / scripts / scaffolding / integration glue -> `gemini`
- UX copy / prompt wording / conversation design -> `kimi`

### Reviewers

- auth / security / permissions -> `minimax`
- data integrity / reports / idempotency -> `minimax`
- CI / tooling / scripts -> `claude`
- UX copy / Telegram conversation flow -> `kimi`

## Priority and Dependency Handling

Suggested execution order:

- `priority:P0` before `priority:P1`
- `queue:blocked` issues should include a comment naming the blocking issue(s)

Recommended blocker comment format:

```text
[bot-blocked]
reason=Depends on issue #2 parent-pupil ownership model
next_check=after blocker merged
```

## GitHub Command Examples

List Claude implementation queue:

```bash
gh issue list --limit 100 --label 'queue:ready-impl' --label 'llm-owner:claude'
```

List MiniMax review queue:

```bash
gh issue list --limit 100 --label 'queue:ready-review' --label 'llm-reviewer:minimax'
```

Claim issue #12:

```bash
gh issue edit 12 --remove-label 'queue:ready-impl' --add-label 'queue:claimed'
gh issue comment 12 --body "[bot-claim]
worker=claude
role=implementer
claimed_at=2026-02-23T17:30:00Z
lease_hours=24
branch=codex/issue-12-short-name"
```

## Human Role

Humans remain the final decision-makers for:

- security tradeoffs
- schema/migration rollout
- merge approval
- priority overrides

LLM labels describe routing, not organizational accountability.
