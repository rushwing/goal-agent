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
- **Each queue state has exactly one actor and an unambiguous set of valid next states** — no agent should need to read comment history to decide what to do next
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

Use **exactly one** queue state at a time. The label alone must identify who acts next.

```text
  queue:blocked ──── blocker resolved ───► queue:ready-impl
  (waiting on dep)                          (unowned)
                                               │
                                    implementer claims
                                               │
                                               ▼
                                      queue:impl-active
                                       (implementing)
                                          │       │
                               PR opened │       │ blocked on
                                         │       │ decision/dep
                                         ▼       ▼
                                    queue:in-pr  queue:needs-human
                                  (awaiting      (human decides)
                                   reviewer)        │        │
                                      │             │        │
                           reviewer   │    back to  │        │ back to
                           claims     │    impl     ▼        ▼ review
                                      │       queue:ready-impl
                                      ▼       queue:in-pr
                               queue:review-active
                                (reviewing)
                               /      |       \
                    approved /        |        \ changes
                            /         |         \ requested
                           ▼          │          ▼
                    queue:approved  releases   queue:ready-impl
                    (human merges;  without     (re-opens for
                     LLM closes)    result      implementation)
                         │             │
                  human  │             ▼
                  merges;│         queue:in-pr
                  LLM    ▼        (back to awaiting
                  closes queue:done    reviewer)
                         (resolved)
```

### Transition table

| From | To | Who acts |
|---|---|---|
| `queue:ready-impl` | `queue:impl-active` | LLM implementer claims |
| `queue:impl-active` | `queue:in-pr` | LLM implementer opens PR |
| `queue:impl-active` | `queue:needs-human` | LLM implementer hits decision blocker |
| `queue:impl-active` | `queue:blocked` | LLM implementer hits dependency blocker |
| `queue:in-pr` | `queue:review-active` | LLM reviewer claims |
| `queue:review-active` | `queue:approved` | LLM reviewer: review passed |
| `queue:review-active` | `queue:ready-impl` | LLM reviewer: changes requested |
| `queue:review-active` | `queue:in-pr` | LLM reviewer: releases claim without result |
| `queue:review-active` | `queue:needs-human` | LLM reviewer: hits decision blocker |
| `queue:approved` | `queue:done` | **Human** merges PR → **LLM** sets done + closes issue |
| `queue:needs-human` | `queue:ready-impl` | **Human: resolved implementation blocker** |
| `queue:needs-human` | `queue:in-pr` | **Human: resolved review-stage blocker** |
| `queue:blocked` | `queue:ready-impl` | **Human: upstream dependency resolved** |

> **Merge policy:** LLM workers share the same GitHub account as the repo owner and cannot self-merge. `queue:approved` is the signal for the human to merge. After the human merges, the LLM handles post-merge housekeeping (`queue:approved` → `queue:done` + close issue), ideally triggered by the `pull_request: closed+merged` event.

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
- An issue with `queue:impl-active` or `queue:review-active` should not be re-claimed until the lease expires (unless human overrides)
- Reviewers should review first, not rewrite immediately
- If implementation and review disagree on design semantics, move to `queue:needs-human`

## Human Decisions That Should Not Be Auto-Delegated

- **All PR merges** — LLM workers share the same GitHub account; merging must always be done by the human
- Security tradeoffs and trust boundaries
- Schema migration rollout and data backfill strategy
- Breaking API changes
- Priority overrides across issues

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
