# Issue Flow (Human Guide)

This document describes the issue lifecycle and assignment strategy for multi-LLM collaboration.

It is intended for human developers and maintainers.

## Goals

- Reduce collisions when multiple LLMs work in parallel
- Make issue state transitions predictable
- Assign implementation/review based on capability fit, not model brand
- Keep humans as final decision-makers for risky changes

## Core Principles

- One issue should have one primary implementer at a time
- Reviews should be assigned by risk type (security, data integrity, DX, UX)
- Use queue states to control flow
- Prefer capability-based routing over ad hoc assignment
- Human maintainers own prioritization and merge decisions

## Capability-Based Assignment Strategy

Do not assign by model name in this document. Assign by capability profile.

### Implementation assignment (who should modify code)

- **Architecture / cross-file backend refactor specialist**
  - Best for: auth, permissions, schema changes, migrations, service-layer invariants
  - Typical issue types: security, data model redesign, object-level authorization

- **Tooling / CI / integration / scaffolding specialist**
  - Best for: CI workflows, scripts, build config, bot adapters, glue code
  - Typical issue types: DX, automation setup, infra-ish app integration

- **Product UX / prompt / conversation design specialist**
  - Best for: bot conversation flow, user-facing copy, prompts, reporting tone/spec wording
  - Typical issue types: Telegram UX, prompt tuning, report content standards

### Review assignment (who should review)

- **Security / adversarial reviewer**
  - Best for: auth, role checks, spoofing risks, privilege escalation, unsafe defaults

- **Data integrity / invariants reviewer**
  - Best for: idempotency, duplicate prevention, aggregation correctness, state machine bugs

- **DX / tooling reviewer**
  - Best for: CI reliability, scripts, local-dev ergonomics, config compatibility

- **UX / wording reviewer**
  - Best for: human-facing messages, bot commands, prompt clarity, user friction reduction

## Issue Lifecycle (Queue Flow)

Use one queue state at a time.

```text
                  +----------------------+
                  |  queue:blocked       |
                  |  Waiting on decision |
                  |  or dependency       |
                  +----------+-----------+
                             |
                             | (blocker resolved)
                             v
+----------------------+   +----------------------+   claim   +----------------------+
| New / Triaged Issue  |-->| queue:ready-impl     |---------> | queue:claimed        |
| (priority + labels)  |   | Ready to implement   |           | Lease active         |
+----------------------+   +----------------------+           +----------+-----------+
                                                                          |
                                                                          | PR opened
                                                                          v
                                                               +----------------------+
                                                               | queue:in-pr          |
                                                               | Implementation in PR |
                                                               +----------+-----------+
                                                                          |
                                                                          | impl complete,
                                                                          | reviewer requested
                                                                          v
                                                               +----------------------+
                                                               | queue:ready-review   |
                                                               | Ready for review      |
                                                               +----------+-----------+
                                                                          |
                                         +--------------------------------+------------------------------+
                                         |                                                               |
                                         | review finds blocker / decision needed                         | review passes + merged
                                         v                                                               v
                              +----------------------+                                      +----------------------+
                              | queue:needs-human    |------------------------------------->| queue:done           |
                              | Human decision needed|  (decision applied / follow-up done)| Resolved / merged    |
                              +----------+-----------+                                      +----------------------+
                                         |
                                         | back to implementation
                                         v
                              +----------------------+
                              | queue:ready-impl     |
                              +----------------------+
```

## Recommended Triage Steps (Human Maintainer)

1. Add issue type labels (`bug`, `enhancement`, `security`, `backend`, `data-integrity`, etc.)
2. Add priority label (`priority:P0`, `priority:P1`, ...)
3. Decide queue state:
   - `queue:ready-impl` if actionable now
   - `queue:blocked` if dependency or open decision exists
4. Assign capability-fit implementer/reviewer labels (machine-readable routing labels)
5. Add a short blocker note if blocked (what issue/decision is missing)

## How to Choose an Implementer (Quick Matrix)

```text
If issue is mostly...

Security / auth / permissions / DB invariants
  -> assign to "architecture / backend refactor specialist"

CI / scripts / config / automation / integration glue
  -> assign to "tooling / integration specialist"

Conversation design / prompts / user-facing wording
  -> assign to "UX / prompt specialist"

Mixed (backend + UX)
  -> assign implementation to backend specialist
  -> assign UX specialist as reviewer
```

## How to Choose a Reviewer (Quick Matrix)

```text
Primary risk                        Recommended reviewer capability
----------------------------------  -------------------------------------------
Privilege escalation / auth bypass  Security / adversarial reviewer
Duplicate rows / wrong stats        Data integrity / invariants reviewer
Broken local setup / flaky CI       DX / tooling reviewer
Confusing bot flow / wording        UX / wording reviewer
```

## Conflict Avoidance Rules

- Do not let two implementers modify the same issue at the same time
- A claimed issue should not be re-claimed until lease expires (unless human overrides)
- Reviewers should review first, not rewrite immediately
- If implementation and review disagree on design semantics, move to `queue:needs-human`

## Human Decisions That Should Not Be Auto-Delegated

- Security tradeoffs and trust boundaries
- Schema migration rollout and data backfill strategy
- Breaking API changes
- Priority overrides across issues
- Merge approval for high-risk changes

## Practical Examples (Capability Mapping Only)

- **Auth header spoofing fix**
  - Implementer: architecture/backend specialist
  - Reviewer: security/adversarial reviewer

- **Report double-counting bug**
  - Implementer: backend/data logic specialist
  - Reviewer: data integrity reviewer

- **Telegram bot MVP inbound adapter**
  - Implementer: tooling/integration specialist
  - Reviewer: backend specialist + UX/prompt reviewer

- **CI workflow and local test reproducibility**
  - Implementer: tooling/DX specialist
  - Reviewer: DX/tooling or backend reviewer

## Notes

- This document is intentionally capability-based and tool-agnostic.
- Concrete model mapping (which LLM plays which role) should live in machine-readable routing configs and labels, not here.
