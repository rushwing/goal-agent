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

- `queue:ready-impl` : ready to implement
- `queue:claimed` : a worker is currently working on it
- `queue:in-pr` : implementation is in a PR
- `queue:ready-review` : implementation is complete and ready for review
- `queue:blocked` : cannot proceed yet
- `queue:needs-human` : a human decision is required
- `queue:done` : resolved / merged

Rule: never leave multiple `queue:*` labels on the same issue.

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

## Common Mistakes to Avoid

- Assigning two implementers to the same issue
- Forgetting to remove the old `queue:*` label
- Marking `queue:ready-review` before implementation is actually stable
- Using reviewer labels as if they were implementers
- Keeping blocked issues without a blocker note

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
