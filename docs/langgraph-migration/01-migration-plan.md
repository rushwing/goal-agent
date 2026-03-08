# goal-agent × LangGraph 迁移专题 — 01 迁移计划 & 对比维度

> **状态**：Pre-migration（重构尚未开始）
> **基线日期**：2026-03-09

---

## 1. 迁移策略：Strangler Fig（绞杀者模式）

**不做** Big Bang 重写（高风险，测试覆盖难以保证）。
**采用** 渐进式替换：

```
阶段 0 — 环境准备           不改线上逻辑
阶段 1 — Wizard 状态图      替换 wizard_service.py 内核
阶段 2 — Checkpointer       替换手工 DB flush
阶段 3 — Human-in-the-loop  替换 confirm() 暂停模式
阶段 4 — 并行 plan gen      fan-out 替换串行 for loop
阶段 5 — Tool 层打通        MCP / API 层适配 LangGraph
```

每个阶段结束时，94 条测试必须全绿，且行为与 baseline 一致。

---

## 2. 详细迁移步骤

### 阶段 0 — 环境 & 依赖准备

- 安装 `langgraph` + `langchain-anthropic`
- 搭建 LangGraph Checkpointer（`AsyncSqliteSaver`，测试用；生产考虑 Postgres）
- 决定 State Schema（TypedDict vs Pydantic）
- 建立 LangGraph Studio 可视化环境（本地 debug 用）

### 阶段 1 — Wizard StateGraph 替换

**目标**：用 `StateGraph` 重写 `wizard_service.py` 内的控制流。

```
当前：                          目标：
wizard_service.py              wizard_graph.py
├── set_scope()                ├── scope_node
├── set_targets()              ├── targets_node
├── set_constraints()          ├── constraints_node
├── _generate_and_check()      ├── research_node (fan-out)
│   ├── _run_web_research()    ├── plan_gen_node (fan-out)
│   └── plan loop              └── feasibility_node
└── feasibility check
                               conditional_edge:
                               feasibility_node → {
                                 "blocked": "adjusting_node",
                                 "ok":      "await_confirm"
                               }
```

保留：model / crud / plan_generator / feasibility_service（服务层不变）
替换：wizard_service.py 内的状态路由逻辑

### 阶段 2 — Checkpointer 替换手工 flush

**目标**：用 LangGraph Checkpointer 替代 `crud_wizard.update_wizard(status=...)` 的手工持久化。

```
当前：每步手动 await crud_wizard.update_wizard(db, wizard, status=..., ...)
目标：graph.invoke(state, config={"thread_id": wizard_id})
      LangGraph 在每个 node 结束后自动 checkpoint
```

`GoalGroupWizard` 表可保留用于 API 层 backward compat，
或逐步迁移到 LangGraph thread store + 一个简化的 wizard_summary 视图。

崩溃恢复：graph 从最后成功 checkpoint 恢复，不再从 `collecting_scope` 重来。

### 阶段 3 — Human-in-the-loop 替换 confirm()

**目标**：用 `interrupt_before` 替代隐式"等待 confirm"约定。

```
当前：wizard 停在 feasibility_check status，
      BestPal 自己知道要调 confirm_goal_group tool

目标：graph 在 confirm_node 前自动 interrupt，
      OpenClaw 收到 interrupt 信号后，
      向 BestPal 展示计划摘要，等待确认
      BestPal 确认 → graph.invoke(Command(resume=True))
      BestPal 拒绝 → graph.invoke(Command(resume=False))
```

### 阶段 4 — 并行计划生成

**目标**：用 `Send` API 替换串行 for loop。

```python
# 当前 (wizard_service.py)
for spec in target_specs:           # 串行，N targets × ~30s
    await plan_generator.generate_plan(...)

# 目标 (LangGraph Send fan-out)
def dispatch_plans(state):
    return [Send("plan_gen_node", {"spec": s, "research": ...})
            for s in state["target_specs"]]

graph.add_conditional_edges("research_node", dispatch_plans)
# 并行执行，理论耗时 = max(single plan) ≈ 30s，不再 × N
```

### 阶段 5 — Tool 层适配

**目标**：MCP tool 层 / FastAPI 路由层调用方式适配 LangGraph graph。

```
当前：wizard_tools.py 直接调 wizard_service.set_scope()
目标：wizard_tools.py 调 graph.invoke({"action": "set_scope", ...},
                                       config={"thread_id": wizard_id})
```

API 路由层（app/api/v1/wizards.py）同理。
OpenClaw plugin.json 无需改动（tool name 不变）。

---

## 3. 对比维度 & 测量方法

> 重构完成后，对每个维度在相同基线上量化，形成 `02-comparison.md`。

### D1 — 代码可读性（State Flow Clarity）

| | Before | After（目标） |
|---|---|---|
| **状态路由方式** | 手写 if/elif，散落在多个函数 | `StateGraph` 节点 + 边，一图读懂 |
| **状态图可视化** | 无（只能读代码） | LangGraph Studio 自动渲染 |
| **新增步骤改文件数** | 5–7 个文件 | 目标 ≤ 3 个（graph node + state schema） |

**测量**：
- 统计重构后 wizard 流程相关 LOC（目标：wizard 编排层 LOC 下降 ≥ 30%）
- 统计新增一个 wizard step 需改文件数

---

### D2 — 健壮性（Crash Recovery）

| | Before | After（目标） |
|---|---|---|
| **崩溃恢复粒度** | wizard 停在上一个 status，整个 generating_plans 重来 | 从最后 checkpoint node 恢复 |
| **中途失败处理** | plan_generator 崩溃 → generation_errors，但 web_research 结果丢失需重跑 | 每 node 独立 checkpoint，已完成 node 不重跑 |
| **TTL 管理** | 手工 `expires_at` + cron `expire_stale()` | Checkpointer thread TTL |

**测量**：
- 模拟 `generating_plans` 中途进程 kill，记录重启后恢复点
- Before：回到 `collecting_constraints` 之前的状态（需重跑 web research + 所有 plan gen）
- After：从崩溃的 plan_gen_node 恢复（已完成的 target 不重跑）

---

### D3 — 并发性能（Throughput）

| | Before | After（目标） |
|---|---|---|
| **Web Research** | asyncio.gather（已并发）| Send fan-out（并发） |
| **计划生成** | 串行 for loop（N × 30s） | Send fan-out（≈ 30s，与 N 无关） |
| **理论耗时（3 targets）** | ≈ 90s（计划生成串行）| ≈ 30s（并行） |

**测量**：
- Mock LLM（固定延迟 1s/call），跑 3-target wizard，记录 wall time
- Before baseline：`_generate_and_check` 耗时（含 web research + 3 plans + feasibility）
- After target：耗时下降 ≥ 50%（when N ≥ 2）

---

### D4 — Human-in-the-loop 可靠性

| | Before | After（目标） |
|---|---|---|
| **暂停机制** | 约定（文档 + LLM prompt），无协议保证 | `interrupt_before` 协议级暂停 |
| **绕过风险** | OpenClaw 跳过 confirm 调其他 tool，无保护 | graph 不前进，任何 invoke 都返回 interrupt state |
| **恢复方式** | 调 `/wizards/{id}/confirm` endpoint | `graph.invoke(Command(resume=True/False))` |

**测量**：
- 定性：是否存在"可被跳过"的路径
- Before：是（OpenClaw 可直接调其他 tool）
- After：否（graph 在 interrupt 状态不响应非 resume 调用）

---

### D5 — 可观测性（Observability）

| | Before | After（目标） |
|---|---|---|
| **Trace 粒度** | Python logging，无 run-level trace ID | LangSmith trace：每次 graph run 一个 trace，含所有 LLM calls |
| **调试方式** | 跨模块查日志，手动关联 | LangSmith UI 点开 run，看完整 node 执行树 |
| **LLM call 可见性** | 需在 llm_service.py 中加日志 | LangSmith 自动记录 prompt / response / token |

**测量**：
- 定性：debug 一次"计划生成失败"需要查多少个文件/日志行
- Before baseline：≥ 3 个文件（wizard_service + plan_generator + llm_service）
- After target：1 个 LangSmith trace

---

### D6 — 测试性（Testability）

| | Before | After（目标） |
|---|---|---|
| **测试总数** | 94 | ≥ 94（不能下降） |
| **状态转换测试** | 每个 service 函数单独测，state 靠 DB fixture | 可直接测试 graph edge 转换，state 是 Python dict |
| **Mock 方式** | `patch("app.services.llm_service.chat_complete")` | `patch` 或 LangChain fake model |

**测量**：
- 测试数量（重构后不得低于 94）
- Wizard 相关测试 LOC（目标：测试更聚焦，LOC 不显著增加）
- 是否可以不依赖 SQLite 测试 graph 逻辑（pure Python state dict）

---

### D7 — 扩展成本（Extension Cost）

| 操作 | Before（文件数） | After（目标） |
|---|---|---|
| 新增 wizard 步骤 | 5–7 | ≤ 3 |
| 修改状态路由逻辑 | 1 文件（wizard_service.py）+ 理解隐式控制流 | 改 graph edge，可视化立即更新 |
| 替换 LLM 模型 | 修改 llm_service.py | 替换 LangChain model binding |
| 接入新 Checkpointer 后端 | 不支持（手写 DB） | 换 `AsyncRedisSaver` 等一行配置 |

---

## 4. 预期困难与风险

### R1 — Async 兼容性

LangGraph 的 async graph（`ainvoke`）与 SQLAlchemy AsyncSession 的生命周期管理需要仔细对齐。
`AsyncSessionLocal` 目前在每个 MCP tool call 里创建/关闭，切换到 graph 后需要统一管理。

### R2 — Checkpointer vs 现有 DB 模型

`GoalGroupWizard` 表承载了 Business 数据（target_specs、reference_materials 等）+ 状态机状态。
切换到 LangGraph Checkpointer 后，需要决定：
- 方案 A：让 Checkpointer 管理全部状态，`GoalGroupWizard` 表只存摘要（读侧向后兼容）
- 方案 B：保留 `GoalGroupWizard` 表为 source of truth，Checkpointer 只做控制流 checkpoint

方案 B 迁移成本更低，但失去 Checkpointer 的崩溃恢复优势（§D2）。

### R3 — MCP Tool 层适配

MCP tool 是无状态的单次 HTTP 调用，每次调用都需要 `thread_id`（wizard_id）来恢复 graph。
需要确保 LangGraph `graph.invoke(..., config={"thread_id": ...})` 在并发多用户下线程安全。

### R4 — OpenClaw 协议对齐

LangGraph `interrupt` 机制需要 OpenClaw 理解"暂停状态"并等待用户输入后再 resume。
这需要修改 OpenClaw 的 prompt engineering，或在 MCP tool 层封装 interrupt → user-facing message 的转换。

### R5 — 测试框架对齐

现有测试用 `AsyncSession` + SQLite fixture。
LangGraph graph 测试可用 `MemorySaver` 替代持久化，但需要为 graph invoke 准备新的 fixture 模式。

---

## 5. 对比文档路线图

| 文件 | 状态 | 内容 |
|---|---|---|
| `00-baseline.md` | ✅ 已完成 | 重构前架构 + 基线指标 + 痛点 |
| `01-migration-plan.md` | ✅ 本文 | 迁移步骤 + 对比维度定义 |
| `02-comparison.md` | ⏳ 重构后填写 | Before vs After 对比表，含实测数据 |
| `03-lessons-learned.md` | ⏳ 重构后填写 | 遇到的困难、解法、踩坑总结 |
