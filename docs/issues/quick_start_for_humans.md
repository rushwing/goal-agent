# Quick Start for Humans (Issue Routing)

This is the 3-minute guide for maintainers using multi-LLM issue routing in this repo.

For the full lifecycle and rationale, see [`docs/issues/issue_flow.md`](issue_flow.md).

## What You Need to Do (Most of the Time)

When a new issue is created:

1. Add type labels (e.g. `bug`, `enhancement`, `security`, `backend`, `data-integrity`)
2. Add priority (`priority:P0`, `priority:P1`, ...)
3. Set one queue label:
   - `queue:ready-impl` if actionable now
   - `queue:blocked` if waiting on another issue or a decision
4. Assign one implementer capability via `llm-owner:*`
5. Assign one or more reviewer capabilities via `llm-reviewer:*`

## Queue Labels (Use Exactly One)

| Label | Meaning | Who acts next |
|---|---|---|
| `queue:ready-impl` | Unowned; waiting for implementer | LLM implementer |
| `queue:impl-active` | Implementer claimed; work in progress | LLM implementer |
| `queue:in-pr` | PR open; waiting for reviewer | LLM reviewer |
| `queue:review-active` | Reviewer claimed; review in progress | LLM reviewer |
| `queue:approved` | Review passed; awaiting merge | **Human** merges PR → LLM closes |
| `queue:needs-human` | Blocked on a human judgment/approval | **Human maintainer** |
| `queue:blocked` | Blocked on an upstream issue or dependency | Human or upstream worker |
| `queue:done` | Resolved / merged | — |

Rule: never leave multiple `queue:*` labels on the same issue.

**Merge policy:** LLM workers share the same GitHub account as the repo owner and cannot self-merge. When you see `queue:approved`, your only job is to merge the PR. The LLM handles the rest (label update + close) automatically after detecting the merge.

**Note:** `queue:impl-active` and `queue:review-active` replaced the old `queue:claimed` label. The role is now encoded in the label itself — no need to read comment history to know who should act.

## How to Choose an Implementer (Capability-Based)

Pick based on the **kind of work**, not the model name.

- **Architecture / backend refactor specialist**
  - Use for: auth, permissions, schema changes, migrations, invariants

- **Tooling / integration specialist**
  - Use for: CI, scripts, config fixes, automation, bot adapters, glue code

- **UX / prompt specialist**
  - Use for: bot flows, prompts, user-facing copy, reporting wording

## How to Choose a Reviewer

- **Security / adversarial reviewer**
  - For auth, role checks, trust boundaries, abuse paths

- **Data integrity reviewer**
  - For idempotency, duplicates, aggregation correctness, state transitions

- **DX / tooling reviewer**
  - For CI, scripts, setup, build config

- **UX / wording reviewer**
  - For prompts, bot conversations, user-facing messaging

## Fast Decision Rules

```text
Security / auth / permission issue?
  -> backend/architecture implementer + security reviewer

Report math / duplicate data / idempotency issue?
  -> backend/data implementer + data integrity reviewer

CI / scripts / pyproject / setup issue?
  -> tooling/integration implementer + DX/tooling reviewer

Telegram UX / prompt / wording issue?
  -> UX/prompt implementer (or reviewer if backend-heavy)
```

## When to Mark `queue:blocked`

Use `queue:blocked` when:

- the issue depends on another issue/PR
- a product decision is missing
- a security boundary/trust model is not decided
- schema/migration rollout needs human approval

Add a short comment so others know why.

Recommended format:

```text
[bot-blocked]
reason=Depends on issue #2
next_check=after issue #2 merged
```

## When to Move to `queue:needs-human`

Use `queue:needs-human` when the worker/reviewer is blocked by a decision, not by coding work.

Examples:

- choosing between two auth models
- deciding whether a migration can be breaking
- approving a tradeoff between speed and safety

After you resolve it, move to:
- `queue:ready-impl` if the implementation hasn't started yet
- `queue:in-pr` if the implementation was already in a PR and only the review was blocked

## What to Do When You See `queue:approved`

Your only action as the human maintainer:

1. Read the `[bot-review]` comment to confirm the reviewer's notes
2. Merge the PR: `gh pr merge <n> --squash` (or via GitHub UI)

That's it. The LLM detects the merge event and automatically sets `queue:done` and closes the issue. You do not need to touch the labels or close the issue manually.

## Common Mistakes to Avoid

- Assigning two implementers to the same issue
- Forgetting to remove the old `queue:*` label when transitioning
- Using `queue:impl-active` or `queue:review-active` on an issue nobody has actually claimed
- Using reviewer labels as if they were implementers
- Keeping blocked issues without a blocker note
- Letting an LLM merge a PR — always merge yourself after seeing `queue:approved`
- Manually setting `queue:done` or closing the issue — let the LLM do it after merge
- ~~Marking `queue:ready-review`~~ — this label no longer exists; `queue:in-pr` is the signal for reviewers to pick up work

## Minimal Triage Checklist (Copy/Paste)

```text
[ ] Type labels added
[ ] Priority label added
[ ] Exactly one queue label set
[ ] One llm-owner:* label set
[ ] One or more llm-reviewer:* labels set
[ ] Blocker note added (if queue:blocked)
```

## Related Docs

- Full lifecycle and assignment strategy: [`docs/issues/issue_flow.md`](issue_flow.md)
- LLM routing protocol (machine-readable contract): [`.github/LLM_ROUTING.md`](../../.github/LLM_ROUTING.md)
