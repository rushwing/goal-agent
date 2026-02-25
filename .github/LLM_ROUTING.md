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

| Label | Meaning | Who acts next |
|---|---|---|
| `queue:ready-impl` | Unowned; waiting for an implementer to claim | LLM implementer |
| `queue:impl-active` | Implementer claimed; work in progress | LLM implementer |
| `queue:in-pr` | PR opened; waiting for a reviewer to claim | LLM reviewer |
| `queue:review-active` | Reviewer claimed; review in progress | LLM reviewer |
| `queue:approved` | Review passed; awaiting human merge | **Human** merges PR → **LLM** closes |
| `queue:needs-human` | Blocked on human judgment or approval | **Human only** |
| `queue:blocked` | Blocked on an upstream issue or dependency | Human or upstream worker |
| `queue:done` | Merged / resolved | — |

Rule: keep **exactly one** `queue:*` label on each issue at all times.

**Design principle:** the queue label alone must identify which role acts next and what valid transitions exist. No agent should need to read comment history to make a routing decision — comments are audit trail only.

**Merge policy:** All PRs must be merged by the human maintainer. LLM workers share the same GitHub account as the repo owner and cannot self-merge. Reviewers signal approval by transitioning to `queue:approved`. The human performs the actual GitHub merge; the LLM then handles post-merge housekeeping (`queue:approved` → `queue:done` + close issue), ideally triggered by the `pull_request: closed+merged` event.

## State Machine

```
                    ┌─────────────────────────────────────────────┐
                    │              queue:needs-human               │
                    │      (blocked on human judgment)             │
                    └──────┬──────────────────────┬───────────────┘
           resolved impl   │                      │  resolved review
           blocker         ▼                      ▼  blocker
                    queue:ready-impl         queue:in-pr
                          │                      │
              implementer │ claims               │ reviewer claims
                          ▼                      ▼
                   queue:impl-active      queue:review-active
                          │                /     |     \
                   PR     │          done /      |      \ changes
                   opened │              /  releases    \ requested
                          ▼             ▼   without      ▼
                    queue:in-pr    queue:done  result  queue:ready-impl
                                          queue:in-pr
```

Canonical transition table (also in `llm-routing.json`):

| From | To | Who | Trigger |
|---|---|---|---|
| `queue:ready-impl` | `queue:impl-active` | LLM | Implementer claims |
| `queue:impl-active` | `queue:in-pr` | LLM | PR opened |
| `queue:impl-active` | `queue:needs-human` | LLM | Blocked on decision during impl |
| `queue:impl-active` | `queue:blocked` | LLM | Blocked on upstream dependency |
| `queue:in-pr` | `queue:review-active` | LLM | Reviewer claims |
| `queue:review-active` | `queue:approved` | LLM | Review passed |
| `queue:review-active` | `queue:ready-impl` | LLM | Changes requested; re-opens for implementation |
| `queue:review-active` | `queue:in-pr` | LLM | Reviewer releases claim without a result |
| `queue:review-active` | `queue:needs-human` | LLM | Review blocked on human judgment |
| `queue:approved` | `queue:done` | LLM (on merge event) | PR merged by human; LLM closes issue |
| `queue:needs-human` | `queue:ready-impl` | **Human** | Human resolved implementation blocker |
| `queue:needs-human` | `queue:in-pr` | **Human** | Human resolved review-stage blocker |
| `queue:blocked` | `queue:ready-impl` | **Human** | Upstream dependency resolved |

## Comment Protocol (Strict)

Use these headers exactly so scripts can parse them reliably.

### Claim comment (required when claiming implementation or review)

```text
[bot-claim]
worker=<claude|gemini|kimi|minimax>
claimed_at=<ISO8601 UTC>
lease_hours=24
branch=<optional-branch-name>
```

Note: `role` is no longer a required field — it is implicit in the queue label (`queue:impl-active` = implementer, `queue:review-active` = reviewer).

### Review result comment (required when a reviewer finishes review)

```text
[bot-review]
worker=<claude|gemini|kimi|minimax>
reviewed_at=<ISO8601 UTC>
result=<approved|changes_requested|blocked>
pr=<number or url>
notes=<short summary>
```

Rules:

- Do not use `[bot-claim]` for review result summaries
- `worker` in `[bot-review]` should match one of the issue's `llm-reviewer:*` labels
- Prefer GitHub comment `createdAt` as the audit source of truth if timestamps disagree

## Implementation Claim Protocol

Before claiming:

1. Read current queue label from the issue.
2. Do not claim if the label is `queue:impl-active` or `queue:review-active` (another worker holds an active lease).
3. Do not claim if the label is `queue:blocked` unless the blocker is resolved.

To claim implementation (`queue:ready-impl` → `queue:impl-active`):

```bash
gh issue edit <n> --remove-label 'queue:ready-impl' --add-label 'queue:impl-active'
gh issue comment <n> --body "[bot-claim]
worker=<your-id>
claimed_at=<ISO8601 UTC>
lease_hours=24
branch=<branch-name>"
```

When the PR is opened (`queue:impl-active` → `queue:in-pr`):

```bash
gh issue edit <n> --remove-label 'queue:impl-active' --add-label 'queue:in-pr'
gh issue comment <n> --body "PR opened: https://github.com/<owner>/<repo>/pull/<pr>"
```

## Review Claim Protocol

To claim review (`queue:in-pr` → `queue:review-active`):

```bash
gh issue edit <n> --remove-label 'queue:in-pr' --add-label 'queue:review-active'
gh issue comment <n> --body "[bot-claim]
worker=<your-id>
claimed_at=<ISO8601 UTC>
lease_hours=4"
```

After reviewing, post the result and transition:

```bash
# approved — signal human to merge; do NOT merge yourself
gh issue comment <n> --body "[bot-review]
worker=<your-id>
reviewed_at=<ISO8601 UTC>
result=approved
pr=<number>
notes=<summary>"
gh issue edit <n> --remove-label 'queue:review-active' --add-label 'queue:approved'

# changes requested
gh issue comment <n> --body "[bot-review]
worker=<your-id>
reviewed_at=<ISO8601 UTC>
result=changes_requested
pr=<number>
notes=<summary>"
gh issue edit <n> --remove-label 'queue:review-active' --add-label 'queue:ready-impl'

# blocked on human judgment
gh issue edit <n> --remove-label 'queue:review-active' --add-label 'queue:needs-human'
```

Always post a `[bot-review]` comment before changing the label.

**Human merge step** (performed by maintainer after seeing `queue:approved`):

```bash
# Merge the PR on GitHub (via UI or CLI) — this is all the human needs to do
gh pr merge <pr> --squash   # or --merge / --rebase per project convention
```

The LLM then handles post-merge housekeeping automatically (triggered by the `pull_request: closed+merged` event):

```bash
# LLM post-merge cleanup (event-driven, not human)
gh issue edit <n> --remove-label 'queue:approved' --add-label 'queue:done'
gh issue close <n>
```

## Lease / Reclaim Rules

- Default lease: `24` hours (implementer), `4` hours (reviewer)
- A claim is considered active if:
  - issue has `queue:impl-active` or `queue:review-active`, **and**
  - there is a `[bot-claim]` comment within the lease window
- Another worker may reclaim only if the lease has expired and there is no recent progress comment

## Priority and Dependency Handling

Suggested execution order:

- `priority:P0` before `priority:P1`
- `queue:blocked` issues must include a `[bot-blocked]` comment naming the blocking issue(s)

```text
[bot-blocked]
reason=Depends on issue #2 best_pal/go_getter ownership model
next_check=after blocker merged
```

## Recommended Routing (Project Default)

These are defaults, not hard rules.

### Implementers

- `security` or complex backend/data-model changes → `claude`
- CI / DX / scripts / scaffolding / integration glue → `gemini`
- UX copy / prompt wording / conversation design → `kimi`

### Reviewers

- auth / security / permissions → `minimax`
- data integrity / reports / idempotency → `minimax`
- CI / tooling / scripts → `claude`
- UX copy / Telegram conversation flow → `kimi`

## GitHub Command Examples

List Claude's implementation queue:

```bash
gh issue list --limit 100 --label 'queue:ready-impl' --label 'llm-owner:claude'
```

List MiniMax's review queue:

```bash
gh issue list --limit 100 --label 'queue:in-pr' --label 'llm-reviewer:minimax'
```

List issues awaiting human merge:

```bash
gh issue list --limit 100 --label 'queue:approved'
```

Full example — claim, implement, open PR, review, human merges:

```bash
# 1. Claim implementation (LLM)
gh issue edit 12 --remove-label 'queue:ready-impl' --add-label 'queue:impl-active'
gh issue comment 12 --body "[bot-claim]
worker=claude
claimed_at=2026-02-25T09:00:00Z
lease_hours=24
branch=claude/issue-12-short-name"

# 2. Open PR (LLM)
gh issue edit 12 --remove-label 'queue:impl-active' --add-label 'queue:in-pr'
gh issue comment 12 --body "PR opened: https://github.com/<owner>/<repo>/pull/34"

# 3. Claim review (LLM)
gh issue edit 12 --remove-label 'queue:in-pr' --add-label 'queue:review-active'
gh issue comment 12 --body "[bot-claim]
worker=minimax
claimed_at=2026-02-25T14:00:00Z
lease_hours=4"

# 4. Approve and signal human (LLM — do NOT merge)
gh issue comment 12 --body "[bot-review]
worker=minimax
reviewed_at=2026-02-25T14:30:00Z
result=approved
pr=34
notes=No auth regressions found; tests cover negative cases."
gh issue edit 12 --remove-label 'queue:review-active' --add-label 'queue:approved'

# 5. Merge the PR (HUMAN ONLY — do not label or close)
gh pr merge 34 --squash

# 6. Post-merge housekeeping (LLM — triggered by pull_request:closed+merged event)
gh issue edit 12 --remove-label 'queue:approved' --add-label 'queue:done'
gh issue close 12
```

## Human Role

Humans remain the final decision-makers for:

- **merging all PRs** — LLM workers share the same GitHub account as the repo owner and must never self-merge
- security tradeoffs
- schema/migration rollout
- priority overrides

LLM labels describe routing, not organizational accountability.
