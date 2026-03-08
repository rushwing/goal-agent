# goal-agent × LangGraph 迁移专题 — 00 重构前基线

> **用途**：本文件在 LangGraph 迁移开始前冻结，作为"Before"侧的参照。
> **快照日期**：2026-03-09
> **代码基线**：`main` @ 7d87f88（PR #55 合并后）

---

## 1. 项目简介

goal-agent 是一款面向中小学生的 AI 学习规划助手。

```
家长 (BestPal) ─Telegram─► OpenClaw LLM ─MCP─► goal-agent API ─► MariaDB
学生 (GoGetter)                                        │
                                                       └─► Kimi LLM (计划生成 / 可行性分析 / 网络研究)
```

核心能力：
- **Wizard 引导流程**：多步对话式创建 GoalGroup（学习计划窗口）
- **AI 计划生成**：Kimi 生成带周里程碑 + 每日任务的结构化计划
- **网络研究**：Jina Search + Reader 抓取小红书教学素材，注入计划 prompt
- **可行性评估**：7 条规则 + LLM 解释，阻断不合理计划
- **Human Gate**：家长必须主动 confirm 才能激活草稿计划

---

## 2. 当前架构（重构前）

```
BestPal (Telegram / 家长)
       │ 自然语言指令
       ▼
┌─────────────────────────────┐
│   OpenClaw LLM              │  决定调哪个 MCP tool
└────────────┬────────────────┘
             │ MCP tool call (JSON-RPC / HTTP /mcp)
┌────────────▼────────────────────────────────────────────────────┐
│                  TOOL ROUTER  (app/mcp/tools/)                  │
│  wizard_tools  plan_tools  checkin_tools                        │
│  report_tools  tracks_tools  admin_tools                        │
│  9 wizard tools + HMAC 签名验证 + 角色鉴权                      │
└────────────────────────┬────────────────────────────────────────┘
                         │ 直接调 DB / 服务层（同进程）
┌────────────────────────▼────────────────────────────────────────┐
│           PLANNER / STATE MACHINE  (wizard_service.py)          │
│                                                                 │
│  collecting_scope                                               │
│       ↓ set_scope()                                             │
│  collecting_targets                                             │
│       ↓ set_targets()                                           │
│  collecting_constraints                                         │
│       ↓ set_constraints()  ◄────────────────────────┐          │
│  generating_plans                              adjust() 重试    │
│       ├──► [PLANNER]  web_research_service              │       │
│       │      Jina Search → Jina Reader → Kimi           │       │
│       │      并发 asyncio.gather，best-effort            │       │
│       │                                                 │       │
│       └──► [EXECUTOR]  plan_generator                   │       │
│               Kimi LLM (32k output)                     │       │
│               → Plan + WeeklyMilestone + Task → DB      │       │
│                     ↓                                   │       │
│  feasibility_check                                      │       │
│       └──► [EVALUATOR]  feasibility_service             │       │
│               7 条规则（error=blocker / warning）        │       │
│               + Kimi LLM 生成友好解释（best-effort）    │       │
│                     ↓                                   │       │
│             has_blockers? ──YES──────────────────────────┘      │
│                   NO                                            │
│                    ↓                                            │
│  ╔═════════════════════════════════════════╗                    │
│  ║  HUMAN GATE — wizard_service.confirm() ║                    │
│  ║  BestPal 主动调用才继续                 ║                    │
│  ║  • 创建 GoalGroup                       ║                    │
│  ║  • draft Plan → active                  ║                    │
│  ║  • 标记被取代的旧 Plan = completed       ║                    │
│  ╚══════════════════════════╤══════════════╝                    │
│                             ↓                                   │
│  confirmed  (terminal)                                          │
└─────────────────────────────────────────────────────────────────┘
                         │ SQLAlchemy AsyncSession
┌────────────────────────▼────────────────────────────────────────┐
│                  MEMORY  (MariaDB / SQLite in tests)            │
│                                                                 │
│  GoalGroupWizard  ← 完整 wizard 状态快照，跨 Telegram session   │
│  │  status / target_specs / constraints / draft_plan_ids        │
│  │  feasibility_risks / feasibility_passed                      │
│  │  reference_materials / search_errors                         │
│  │  expires_at (24h TTL)                                        │
│  │                                                              │
│  GoalGroup → Target → Plan → WeeklyMilestone → Task → CheckIn  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 Wizard 状态机（完整）

```
collecting_scope
    │ set_scope (≥7 天)
collecting_targets
    │ set_targets (target_id 归属验证)
collecting_constraints
    │ set_constraints → 触发 _generate_and_check()
generating_plans  ──►  web_research (并发)
                  ──►  plan_generator × N targets (串行)
                  ──►  feasibility_service
feasibility_check
    ├── blockers 存在 → adjusting ──► generating_plans (重新执行)
    └── no blockers → 等待 BestPal 主动 confirm
confirmed  ◄── Human Gate 通过
cancelled  ◄── 任意阶段可取消
failed     ◄── go_getter 不存在等不可恢复错误
```

---

## 3. 基线代码量化指标

### 3.1 Wizard 核心文件 LOC

| 文件 | 职责 | LOC |
|------|------|-----|
| `app/services/wizard_service.py` | 状态机 + 编排 | 517 |
| `app/api/v1/wizards.py` | HTTP 路由层 | 288 |
| `app/mcp/tools/wizard_tools.py` | MCP tool 层 | 444 |
| `app/services/plan_generator.py` | LLM 计划生成 | 228 |
| `app/services/feasibility_service.py` | 可行性评估 | 281 |
| `app/services/web_research_service.py` | 网络研究 | 163 |
| `app/services/llm_service.py` | LLM 客户端封装 | 107 |
| `app/crud/wizards.py` | DB CRUD | 77 |
| `app/models/goal_group_wizard.py` | ORM 模型 | 63 |
| **合计** | | **2168** |

### 3.2 复杂度指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 手写状态跳转次数 | **10** | `status=WizardStatus.*` in wizard_service.py |
| if/elif 分支数 | **43** | wizard_service.py 内 |
| Wizard MCP tools | **9** | start / get_status / get_sources / set_scope / set_targets / set_constraints / adjust / confirm / cancel |
| 新增一个 wizard 步骤需改文件数 | **5–7** | model + migration + service + api + mcp_tool + plugin.json (± schema) |
| wizard_service.py 中 `await db.*` 调用 | **11** | 手动管理每步 flush/refresh |
| Wizard 流程中 LLM call sites | **3** | plan_generator + feasibility_enrichment + web_research_extraction |
| 总测试数 | **94** | 全部使用 SQLite in-memory |
| Wizard 相关测试文件 LOC | **922** | test_wizard_service.py (519) + test_feasibility_service.py (403) |
| 项目总 Python 文件 | **82** | app/ 目录 |
| 项目总 Python LOC | **7622** | app/ 目录 |

### 3.3 多层重复问题（DRY 违反）

Wizard 每个 step 在三层分别实现，结构基本一致，但互相独立维护：

```
同一个 "set_scope" 动作分散在：
  wizard_service.set_scope()        ← 业务逻辑
  wizards.py:set_scope endpoint     ← HTTP 参数解析 + 错误映射
  wizard_tools.set_wizard_scope()   ← MCP 参数解析 + 错误映射
```

每层都有：参数验证 → 调服务 → 捕获 ValueError → 返回响应，三份近似代码。

---

## 4. 当前设计的痛点

### P1 — 状态路由手写，不可视

`_generate_and_check()` 里的控制流靠 Python `if` 和手动 `await crud_wizard.update_wizard(... status=...)` 驱动。
没有任何工具可以渲染这个状态机，新人 onboard 只能读代码。

### P2 — Checkpoint 自己实现

跨 Telegram session 的状态恢复靠 `GoalGroupWizard` 表手工 flush。
如果服务在 `generating_plans` 中途崩溃，wizard 停在中间状态，只能等 TTL 过期或手动 cancel。
没有中间节点级别的 checkpoint：`web_research` 完成了，但 `plan_generator` 崩溃，整个步骤重来。

### P3 — Human Gate 隐式

"BestPal 必须 confirm" 这个约束散落在：
- `confirm()` 函数的 guard clause
- MCP tool 的文档字符串
- OpenClaw 的 prompt 指令

没有协议级别的"暂停-等待-恢复"机制。如果 OpenClaw 跳过 confirm 直接调别的 tool，系统无法阻止。

### P4 — 并发计划生成是串行的

```python
for spec in target_specs:          # 串行！
    new_plan = await plan_generator.generate_plan(...)
```

每个 target 的计划生成等上一个完成。3 个 target × 30s/plan = 90s。
Web research 用了 `asyncio.gather`，但计划生成没有。

### P5 — 三层架构重复，扩展成本高

新增一个 wizard 步骤（例如"选择偏好风格"）需要改 5–7 个文件，
且三层（service / API route / MCP tool）的逻辑几乎相同，容易出现不一致。

### P6 — 无内置 Observability

LLM 调用没有 trace ID 贯穿整个 wizard run。
排查"为什么这个计划生成失败"需要跨 wizard_service + plan_generator + llm_service 三个模块查日志，
没有单一的 run-level 可观测入口。

---

## 5. LangGraph 概念预映射

| goal-agent 当前实现 | 对应 LangGraph 概念 |
|---|---|
| `WizardStatus` 枚举 (9 个状态值) | `StateGraph` nodes |
| `wizard_service.*()` 各函数 | node 的 `action` 函数 |
| `has_blockers` if/else | `add_conditional_edges` + route function |
| `GoalGroupWizard` DB 行 (手动 flush) | `SqliteSaver` / `AsyncPostgresSaver` Checkpointer |
| `crud_wizard.update_wizard(status=...)` | graph state 自动持久化 |
| `wizard_service.confirm()` 暂停等待 | `interrupt_before=["confirm_node"]` |
| `asyncio.gather(web_research)` | `Send` API fan-out |
| `for spec in target_specs` (串行生成) | 并行 `Send` → plan_generator subgraph |
| `llm_service.chat_complete()` | `ChatAnthropic` / LangChain model node |
| MCP tool call (OpenClaw → goal-agent) | LangGraph agent `tool_node` |
| `expires_at` TTL + `expire_stale()` | LangGraph thread TTL (Checkpointer 管理) |

---

## 6. 基线快照清单

重构开始前，以下内容已冻结在 `main` @ 7d87f88：

- [x] 当前架构图（本文 §2）
- [x] 量化基线指标（本文 §3）
- [x] 痛点清单（本文 §4）
- [x] LangGraph 概念预映射（本文 §5）
- [x] 94 条测试全绿（作为重构后回归基准）
- [ ] 迁移计划 → 见 `01-migration-plan.md`
- [ ] 对比维度定义 → 见 `01-migration-plan.md`
