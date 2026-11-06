# AUTORESEARCH 技术附录（细节都在这里，主计划见 AUTORESEARCH_PLAN.md）

> 这份文件是给"执行时查"用的，不需要通读。主计划一页版在 `AUTORESEARCH_PLAN.md`。

## A. 目录约定

```
<project>/
├── research/                       # 唯一产物根
│   ├── paper_search.md             # S1
│   ├── baseline_selection.md       # S1
│   ├── ideas.md                    # S2（v2/v3 追加，不覆盖）
│   ├── idea_cards.md               # S3
│   ├── idea_ranking.md             # S3
│   ├── method_proposal.md          # S4
│   ├── baseline_report.md          # S5
│   ├── baseline_config/            # S5（只读快照）
│   ├── baseline_logs/              # S5
│   ├── research_contract_v1.md     # S6（冻结）
│   ├── research_contract_v2.md     # S8→S4 回炉时
│   ├── implementation_report.md    # S7
│   ├── method/                     # S7
│   ├── tests/                      # S7
│   ├── experiment_configs/         # S7（冻结）
│   ├── experiment_results/         # S8（每次一个子目录，只增不改）
│   ├── experiment_analysis.md      # S8
│   ├── research_decision.md        # S8
│   ├── next_hypothesis.md          # S8
│   └── human_notes.md              # 你随手写：跨领域知识/否决理由/方向偏好
└── .autoresearch/
    ├── state.json                  # 状态机（唯一真相）
    ├── gates.jsonl                 # 每次拍板：谁/何时/批准了哪个文件 hash
    └── traces/<stage>/<date>_run<NN>/   # 每次 agent 调用原文
```

**每个 stage 启动时自动读 `research/human_notes.md`**（不存在就跳过）；stage 结束时把自己的疑问以 `## <stage> 待确认` 段追加进去，形成双向对话。

## B. 文件最小字段（缺字段 = stage 未完成；现阶段靠 skill 自检 + `done` 检查文件是否存在）

| 文件 | 必含字段 |
|---|---|
| `paper_search.md` | 每篇：标题/会议年份/链接/代码仓库/摘要/核心问题/数学方法/实验设置/结果/局限/缺口 |
| `baseline_selection.md` | 推荐 baseline + 3 条理由 + 代码环境数据算力需求 + 复现指标 + 可改模块 |
| `ideas.md` | 10 条一句话 research question（编号 1–10，不含评分） |
| `idea_cards.md` | 每卡 7 字段：claim / method sketch / needs / smallest experiment / expected outcome / risk / novelty check。**不含排名词** |
| `idea_ranking.md` | 评分表（novelty / feasibility / falsifiability / payoff 各 1–5 + total）+ top 3 + 弱项列表 + 为什么不是第一名 |
| `method_proposal.md` | RQ / Hypothesis / 数学定义与推导 / 与 baseline 差异 / 模块与接口 / 创新性证据 / 预期贡献与风险 |
| `baseline_report.md` | 复现指标 vs 论文指标（逐项偏差）+ 失败案例 + 环境快照 + 未复现项及原因 |
| `research_contract_v1.md` | Hypothesis / Method Spec / Experimental Protocol / **Success Signal** / **Failure Signal** / Ablation Plan / Resource Budget / Decision Rules |
| `implementation_report.md` | 公式↔代码逐项对照（公式编号 → 文件:行 → 测试名） |
| `experiment_analysis.md` | 每个 claim 是否有实验支持 + 统计 + 失败机制 |
| `research_decision.md` | **Continue / Revise / Kill** + 依据 claim id + 下一步 |
| `next_hypothesis.md` | 由失败/异常信号长出的下一轮假设（喂回 S4） |

## C. 状态机

`tools/autoresearch_state.py` 实际写出的 `.autoresearch/state.json`（2026-11-06 试跑原文，节选）：

```json
{ "schema": 1,
  "direction": "test-time compute scaling for LLM reasoning: …",
  "root": "research",
  "stage": "S4",
  "status": "waiting_human",
  "contract": { "version": 1, "sha256": null, "frozen_at": null },
  "artifacts": {
    "S1": ["research/paper_search.md", "research/baseline_selection.md"],
    "S2": ["research/ideas.md", "research/idea_cards.md"],
    "S3": ["research/idea_ranking.md"],
    "S4": ["research/method_proposal.md"] },
  "history": [
    { "at": "2026-11-06T07:30:40+00:00", "event": "done", "stage": "S1",
      "artifacts": ["…"], "note": "13 papers, 13/13 verified" } ] }
```

- `status ∈ {pending, running, waiting_human, finished, failed}`
- `stage` 只是当前步骤号；下一步读 `STAGES[stage]` 的 actor/reads/writes，不另存计划
- Gate A 把 `status` 从 `waiting_human` 放回 `pending` 才进 S5；Gate B 同样放行才进 S7
- S8 出 `Revise` → `reopen --stage S4`，合同要 `--contract-version 2` 才能重建

**三类人工接触点要分开记，别混成一个**：

| 类型 | 位置 | 引擎行为 | 记录 |
|---|---|---|---|
| Gate A 方法批准 | S4→S5 | `status=waiting_human`，**阻塞流水线** | `gates.jsonl` 一行 + `history` 一条 |
| Gate B 合同冻结 | S6→S7 | `status=waiting_human`，`done` 时已记 sha256 | `gates.jsonl` 一行（带 `contract_sha256`） |
| Decision C/R/K | S8 末尾 | **不阻塞**：本 run 已 `finished`，等你选 Continue/Revise/Kill 才开下一 run | `research_decision.md` + `gates.jsonl` |

## D. 三条防造假约束的实现现状（2026-11-06 核对）

| 约束 | 现状 | 说明 |
|---|---|---|
| 1. Contract 不可变 | **代码强制（一半）** | S6 `done` 记 sha256，同一步再 `done` 且内容变了直接拒绝，除非 `--contract-version 2`。**缺**：S7/S8 启动时不回头比对 hash，改文件不会被拦 |
| 2. Claim→证据链 | **只有规则** | `skills/autoresearch/SKILL.md` 要求每个 claim 落到 `experiment_results/<run>/` 真实文件；仓库里**没有** `evidence_chain.py`，也没有 `UNADJUDICATED` 标记器 |
| 3. 产物只增不改 | **只有约定** | `experiment_results/`、`baseline_logs/` 只允许新目录；没有 hook、没有 git 检查强制 |

补法（按优先级）：① `start` 时若 `contract.sha256` 非空就比对盘上文件；② 写 `tools/evidence_chain.py` 扫合同 claim id → 对应结果文件，缺失标 `UNADJUDICATED`；③ 把每次 agent 调用写入 `.autoresearch/traces/`（目录已建，目前无写入方）。

## E. 现成方案调研（GitHub，2026-11）：不引入外部多 Agent 框架

**"DSH 统筹 + agy 探索 + Codex 评审 + 文件交接" 不需要第三方框架，DSH 官方 MCP client + 本仓已有 stdio server 就够。**

| 项目 | 实际是什么 | 为什么不采用 |
|---|---|---|
| `@deepseek-ai/dsh-mcp-client`（DSH 官方） | 把外部 MCP server 的工具注册成 `mcp__<server>__<tool>` | **采用**：已随 DSH 装在本机 `dsh/node_modules/`，解析路径与现有 `dsh-llm-pi-ai` 一致，零安装 |
| `Boulea7/agy-mcp`（26★，PyPI `agy-mcp`） | 把 `agy` 包成 10 个 MCP 工具，含长任务 supervisor | 与本仓 `antigravity-exec` 功能重叠；多一层外部依赖 |
| `Fanch-hui/codex-bridge`（307★） | 让 **ChatGPT 网页版**当大脑，经 MCP 调本机 codex/agy/dsh/opencode | 主控方向相反（它要 ChatGPT 当主控） |
| `xiaolai/cc-suite`（56★） | 一个插件在 Claude Code / Codex / AGY 之间互相委派 | 解决"人坐在哪个 CLI 里"，不是"状态机 + 人工闸门" |
| ~~`agent-rack`~~ | **GitHub 上搜不到对应项目** | 该条调研项记为**误记**；功能最接近 `codex-bridge` |

## F. DSH 挂 MCP：配置（B2 用）

`cordis.patch.yml` 的语义是补丁列表：
- `- id: X` = **改已存在的条目**，找不到就 warn 然后**静默跳过**；
- `- insert: [...]` = **新增条目**。

新增 MCP 条目**必须**包在 `- insert:` 下。来源：`dsh/node_modules/@deepseek-ai/dsh-app-boot/lib/index.js` 的 `applyEntryPatches()`。

追加到 `~/.dsh/profiles/web/cordis.patch.yml`（**追加，不要覆盖**）：

```yaml
- insert:
    - id: mcp-codex
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: codex
        transport: stdio
        command: python3
        args: ['/home/tc/Auto-claude-code-research-in-sleep/mcp-servers/codex-exec/server.py']
        toolCallTimeoutMs: 3660000

    - id: mcp-antigravity
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: antigravity
        transport: stdio
        command: python3
        args: ['/home/tc/Auto-claude-code-research-in-sleep/mcp-servers/antigravity-exec/server.py']
        env:
          AGY_BIN: /home/tc/.local/bin/agy
        toolCallTimeoutMs: 3660000

    - id: mcp-model-worker
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: model-worker
        transport: stdio
        command: python3
        args: ['/home/tc/Auto-claude-code-research-in-sleep/mcp-servers/model-worker/server.py']
        env:
          MODEL_WORKER_ALLOWED_ROOTS: '["/home/tc/Auto-claude-code-research-in-sleep"]'
          AGY_BIN: /home/tc/.local/bin/agy
        toolCallTimeoutMs: 3660000

    - id: mcp-model-scout
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: model-scout
        transport: stdio
        command: python3
        args: ['/home/tc/Auto-claude-code-research-in-sleep/mcp-servers/model-worker/server.py']
        env:
          # same server, different agy agent profile: the scout owns search_web
          AGY_AGENT: aris-scout
          MODEL_WORKER_ALLOWED_ROOTS: '["/home/tc/Auto-claude-code-research-in-sleep"]'
          AGY_BIN: /home/tc/.local/bin/agy
        toolCallTimeoutMs: 3660000
```

**飞书不在这个列表里**：`mcp-servers/feishu-bridge` 是独立 **HTTP 服务**（`lark_oapi`，`POST /send`、`GET /poll`），不是 MCP 协议。Gate 通知走 `/feishu-notify`（Bash + curl）。

**已验证**：把上面写成临时文件跑 `dsh --profile web --patch /tmp/x.yml --dump-config`，组合结果正确出现 `mcp-codex` / `mcp-model-worker` 条目。
**未验证**：重启后模型能否真拿到工具、`agy`/`codex` 能否被子进程拉起 —— B2 验。

B2 前置：
1. `agy` 已登录（`agy models` 能列模型）；`codex` 已登录。
2. `mkdir -p ~/.gemini/config/agents/`，把 `mcp-servers/antigravity-exec/aris-antigravity-review.md`、`mcp-servers/model-worker/aris-model-worker.md`、`mcp-servers/model-worker/aris-scout.md` 复制进去（**已实测**：`agy agent` 会列出 `aris-model-worker` 和 `aris-scout`；`commandExecutionPolicy` 只接受 `off`/`auto`，写 `on` 会让该 profile 静默不出现）。
3. `dsh --profile web --dump-config | grep -c 'mcp-'` 应为 4。
4. 进 DSH 确认 `mcp__codex__*`、`mcp__antigravity__*`、`mcp__model-worker__*` 各真调一次。

**回退链**：MCP 不可用 → CLI 直调（`codex exec` / `agy`，新进程、上下文天然干净）→ 再不行写 `.autoresearch/traces/.../manual_request.md` 人工搬运。三条路径产物契约一致，回退不改 stage 逻辑。

## G. 实际改了什么（B0–B5 跑完后的账）

| 计划项 | 实际 | 说明 |
|---|---|---|
| 新增 3 个 skill | ✅ 3/3 | `autoresearch`（编排器）、`baseline-repro`（S5）、`research-contract`（S6） |
| 改写 6 个 skill | ✅ 6/6 | `research-lit`→S1、`idea-creator`→S2、`research-review`→S3、`research-refine`→S4、`experiment-bridge`→S7、`analyze-results`→S8；每个加一段 `## Autoresearch stage contract`，主树 + Codex 镜像同步改 |
| 删旧编排器 | ✅ 2 个（原计划 4 个） | 删了 `/idea-discovery`、`/idea-discovery-robot`；**保留** `/experiment-bridge`（已变成 S7 的执行体）和 `/auto-review-loop`（独立评审闭环，不被 autoresearch 替代）。缩小删除范围是因为实测影响面：每个编排器牵动 4–5 个测试、13–17 处文档引用 |
| `tools/autoresearch_state.py` | ✅ | 8 阶段、双闸门、artifact 存在性、合同 sha256 冻结、`gates.jsonl` 追加 |
| `tools/contract_guard.py` | ❌ 未单独实现 | 冻结逻辑并进了状态机：S6 `done` 算 hash，再 `done` 内容变了就拒绝。但 S7/S8 启动**不回头校验**（见 D 节） |
| `tools/evidence_chain.py` | ❌ 未实现 | claim→实验文件追溯目前只是 SKILL 里的规则 |
| `templates/RESEARCH_CONTRACT_TEMPLATE.md` | ✅ | 合同字段模板 |
| `tools/skill-groups.tsv` 新增 `autoresearch` 组 | ✅ | 见文件第 77 行 |
| `docs/SKILLS_CATALOG.md`、`AGENT_GUIDE.md`、镜像 | ✅ | 49 skills 一致；`check_skills_inventory.py` 通过 |
| `install_aris.sh` 装 agy profile + 打印 MCP YAML | ❌ 未做 | 现状是 README 3.1 里的手工 `cp` 三步。换机器漏装会报 `unknown agent` |
| `.gitignore` 忽略实验产物 | ❌ 未做 | 目前靠约定 |

## H. 验收标准与实测结果（2026-11-06）

| # | 标准 | 结果 |
|---|---|---|
| 1 | DSH 里 4 个 MCP 各成功调用一次 | ✅ 4/4（`model-scout` 真写出 `mcp-smoke-dsh.md`；`antigravity` 首次报 `unknown agent "aris-antigravity-review"`，补装 profile 后通过） |
| 2 | `/autoresearch "方向"` 从 S1 走到 S4 并停在 human gate | ✅ 真跑：13 篇文献全核验 → 10 idea 卡 → Codex 打分 → 方法提案 → `waiting_human` |
| 3 | `--resume` 能从 `waiting_human` 继续，进程重启不丢状态 | ✅ 另一进程 `status` 读到同一状态（`--resume` 在 SKILL 里映射为 `next`） |
| 4 | 8 个 stage 文件按 B 节字段生成 | ⚠️ 只实测 S1–S4；S5–S8 未跑过（demo 无 GPU）。`--validate` 选项**不存在**：字段完整性靠 SKILL 自检 + `done` 的文件存在性检查 |
| 5 | 篡改 `research_contract_v1.md` 后启动 S7 → `BLOCKED` | ❌ 未实现。只有 S6 的 `done` 会比对 hash，S7 启动不校验 |
| 6 | 删掉一个 `experiment_results/` 目录 → 报出受影响 claim | ❌ 未实现（同 5，`evidence_chain.py` 不存在） |
| 7 | `pytest tests/ -q` 全绿；库存检查一致 | ✅ `961 passed / 4 skipped`，`ARIS skill inventory is consistent.` |

## I. 决策记录

### 第 1 轮

| # | 决策 | 结论 |
|---|---|---|
| Q1 | 项目形态 | **原地改造 ARIS**：保留原子 skill 当工具箱，思想以源文档为准 |
| Q2 | 入口形态 | **1 编排器 + 可单跑的 stage skill** |
| Q3 | 产物根 | **`research/` 单根 + 源文档原文件名** |
| Q4 | 旧编排器 | **吸收实现手法后退役删除** |
| Q5 | 独立 session | **CLI 新进程**（`codex exec` / `agy`；不再调用 `gemini` CLI） |
| Q6 | Human gate | **文件化 `waiting_human` + 飞书** |

### 第 2 轮

| # | 决策 | 结论 |
|---|---|---|
| Q7 | 新技能与旧技能 | **直接改写旧 skill 本体**；只有 3 个真缺口新写 |
| Q8 | 编排器宿主 | **Python 引擎 + 薄 SKILL.md，DSH 主控；DSH 用 MCP 调 agy/codex** |
| Q9 | 人的输入 | **每个 stage 自动读 `research/human_notes.md`**，并追加待确认问题 |
| Q10 | 实验追踪 | **沿用现有** `/run-experiment`、`/experiment-queue`、`/monitor-experiment`、W&B；只加 decision + 证据链 |

### 第 3 轮（GitHub 调研后）

| # | 决策 | 结论 |
|---|---|---|
| Q11 | 是否引入现成多 Agent 框架 | **不引入**（见 E 节） |
| Q12 | S1/S2 由谁写文件 | **`model-worker`（backend `antigravity`）写**，它有 author profile 有写权限；`antigravity-exec` 降为只读"第二意见"。S1 的**检索**留在 DSH 本地脚本（`tools/*_fetch.py`） |

## J. 建议记成 ADR（可选）

- `docs/adr/0001-replace-orchestrators-with-autoresearch.md`：为什么删掉 W1/W1.5/W2 而不是并存。
- `docs/adr/0002-dsh-as-orchestrator-via-mcp.md`：为什么选 DSH+MCP 而非纯 CLI 或 Claude Code 优先。
## K. 试跑记录（2026-11-06，真调用，非模拟）

跑在 `/home/tc/Desktop/test/autoresearch-demo`，用 B1 状态机驱动，S1→S2→S3 三步全自动交接。

| 步 | 执行体 | 产出 | 校验结果 |
|---|---|---|---|
| S1 | `agy --agent aris-scout` | `paper_search.md` 12.4 KB / 4 个角度 / 13 篇；`baseline_selection.md` 1.0 KB | `verify_papers.py`：**13/13 verified，hallucination_rate 0.0** |
| S2 | `agy --agent aris-model-worker` | `ideas.md` 1.3 KB（10 条）；`idea_cards.md` 15.9 KB（10 卡 × 7 字段，字段数实测 10/10/10/10/10/10/10） | 状态机 `done` 通过 |
| S3 | `codex exec --sandbox danger-full-access` | `idea_ranking.md` 3.1 KB：8 项打分表 + top3 + weak 列表 | 明确指出 2 个 idea 是"参数扫描" |

**结论**：三层机制（起进程 / 传路径 / 核文件）成立；三个 agent 三个独立上下文，没有串味。

### 本次踩到的新坑（B2 必看）

1. **`codex` 的 provider 需要 `IAIEMAS_API_KEY`**，它定义在 `~/.config/iaiemas/env.sh`（由 `~/.bashrc` source）。DSH 进程环境里没有 → MCP 的 codex 条目必须包一层：
   ```yaml
   command: bash
   args: ['-c', 'set -a; . "$HOME/.config/iaiemas/env.sh"; set +a; exec python3 <repo>/mcp-servers/codex-exec/server.py']
   ```
   这样密钥不进 yml。
2. **`codex --sandbox workspace-write` 在本机直接失败**：`bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`。必须传 `danger-full-access`。所以 skill 里调 `mcp__codex__codex` 时要显式带 `sandbox: "danger-full-access"`。
3. **`agy` headless 必须 `--dangerously-skip-permissions`**，否则工具调用被自动拒绝，只回一句 `no output produced`。
4. **`agy` profile 的 `commandExecutionPolicy` 只接受 `off` / `auto`**；写 `on` 会让该 profile 静默从 `agy agent` 里消失。

## L. S4 → Gate A 试跑（2026-11-06 续）

| 项 | 结果 |
|---|---|
| S4 执行体 | `agy --agent aris-scout`，读 `paper_search.md` + `idea_ranking.md` |
| 产出 | `method_proposal.md` 5.1 KB：top-3 逐个查新（含 closest paper / 一句话 delta / verdict）+ 单一方法提案 |
| 状态机 | `done` 后 `status = waiting_human`，`gates.jsonl` 追加 `{"gate":"A","event":"awaiting_human"}` |
| 能停 | 另起一个 Python 进程跑 `next`，仍返回同一个闸门提示（状态在磁盘，不在进程里） |
| 能续 | 单元测试覆盖 `gate approve → S5`、`gate reject → 留在 S4`、`reopen --stage S1` |

**这一步暴露了一个真问题（闸门存在的理由）**：scout 把 Idea 3 判为 "Incremental"、Idea 6 判为 "Novel"，
但 Part 2 却选了 Idea 3 写提案。判断自相矛盾，机器校验抓不到（文件存在、字段齐全），只有人看
Gate A 才能拦。结论：Gate A 不能做成自动通过，必须留给人。

## M. B5 删除范围的实测影响面

| skill | tests 引用 | docs 引用 | 结论 |
|---|---|---|---|
| `idea-discovery` | 4 | 13 | 删；但 `check_skills_inventory.py` 的 `iteration_log` 接线检查要从它改指向 `/autoresearch` |
| `idea-discovery-robot` | 1 | 4 | 删；`--robot` 语义并入 `/autoresearch --robot` |
| `experiment-bridge` | 1 | 9 | **不删**：它已是 S7 实现阶段，改名 `method-implement` 的成本高于收益（1 个 test + 9 处文档 + 目录/镜像） |
| `auto-review-loop` | 4 | 15 | **不删**：它是独立的评审闭环（Workflow 2），autoresearch 的 S3/S8 评审不替代它 |

## N. B2 实测：MCP 服务端已跑通（2026-11-06）

用 `mcp-servers/model-worker/client.py --local` 走完整 MCP stdio 协议（initialize → tools/list → tools/call），
不经过 DSH：

| 项 | 结果 |
|---|---|
| 环境 | `AGY_AGENT=aris-scout`，`MODEL_WORKER_ALLOWED_ROOTS=["/home/tc/Desktop/test"]` |
| 调用 | `worker{prompt, cwd, backend: antigravity, model: gemini-3.8-flash-high, effort: high}` |
| 返回 | `status: SUCCESS`，`threadId: 4690072d-…`，`model: gemini-3.8-flash-high`，`effort: high` |
| 副作用 | 真写出 `research/mcp-smoke.md`（3 篇按年份排序的论文表） |

**唯一没验的是 DSH 自己的 MCP client 接线**——那要重启一次 DSH 才会加载 4 个新条目。

### 新坑：`--model` 变体名自带 effort 后缀

`agy --model gemini-3.8-flash-high --effort medium` 直接报错：
`invalid model selection: --model gemini-3.8-flash-high conflicts with --effort=medium`。

规则：**模型名里的 `-low/-medium/-high` 就是 effort 档位，两个参数必须同档，或者只传其中一个。**
`model: gemini-3.8-flash-high` 配 `effort: high` 正确；配 `medium` 会 500 前失败。

## O. B5 迁移地图（历史记录，完成状态见 P 节）

### 已做（2026-11-06 round 2，零风险部分）

- `skills/idea-discovery/`、`skills/idea-discovery-robot/` 及其 Codex 镜像顶部加了
  **Deprecated 横幅**，指向 `/autoresearch`（robot 版指向 `/autoresearch --robot`）。
- `docs/SKILLS_CATALOG.md` 两行标成 ⚠️ Deprecated（**行保留**，因为库存检查要求每个
  skill 都在目录里）。
- `iteration_log.py --direction` 的方向去重写回从 `idea-discovery` 迁到
  `idea-creator`（S2 的真实归属）：主线和 Codex 镜像各加一节
  `### Direction diversity write-back (S2)`。
- `987 passed / 4 skipped`，库存检查一致。

### 待做（真删，约 1-2 小时）

删除清单：

1. 目录：`skills/idea-discovery/`、`skills/idea-discovery-robot/` 及两个 Codex 镜像目录。
2. 测试整删：`tests/test_auto_proceed_contract.py`（127 行，全部关于 idea-discovery 的
   AUTO_PROCEED 契约）、`tests/test_idea_discovery_gate.py`（400 行）。
3. 工具整删：`tools/idea_discovery_gate.py`（删 skill 后成孤儿）。
4. 库存：`tools/skill-groups.tsv` 删 2 行；`docs/SKILLS_CATALOG.md` 删 2 行；
   11 处 live count 从 **51 → 49**。
5. 检查器：`tools/check_skills_inventory.py` 的 `iteration_log` 接线检查现在读的是
   `skills/idea-discovery/SKILL.md`，删后必抛异常 → 改成读
   `skills/idea-creator/SKILL.md`（已经写回该内容，改一行路径即可）。
6. 跨 skill 引用 16 处需改写为 `/autoresearch`：
   `alphaxiv`、`experiment-bridge`、`feishu-notify`、`render-html`、
   `research-implement-feature`、`research-lit`、`research-review`、`wiki-enrich`，
   以及 `shared-references/` 下的 `integration-contract.md`、`output-composition.md`、
   `output-language.md`、`output-manifest.md`、`resumable-runs.md`。
7. 冻结 overlay `skills/skills-codex-gemini-review/` 里仍有这两个 skill 的副本；
   要么一并删并改 `tests/test_codex_skill_mirror.py` 的 `expected_gemini` 集合
   （7 → 5），要么保留并在 README 里说明它是历史快照。**建议删**，否则目录里留着
   指向已删 skill 的冻结副本。
8. `tests/test_codex_skill_mirror.py:424` 的 `required_terms` 里有 `idea-discovery`
   条目，随目录一起删。

**为什么这轮没做**：一次删除会同时改 8 个 skill 文档 + 5 个 shared-reference + 2 个
测试文件 + 1 个工具 + 1 个检查器，任何一处漏改都会让仓库变红；必须一次提交改完并
跑两次全量测试。弃用横幅 + 目录下架 + 写回迁移已经把"用户不会被引导到旧编排器"这件事
先落地了。

## P. B5 完成（2026-11-06 round 3）

按 O 节清单一次改完，单次提交：

| 项 | 结果 |
|---|---|
| 删除目录 | `skills/idea-discovery/`、`skills/idea-discovery-robot/` + 2 个 Codex 镜像 |
| 删除测试 | `test_auto_proceed_contract.py`（127 行）、`test_idea_discovery_gate.py`（400 行） |
| 删除工具 | `tools/idea_discovery_gate.py`（删 skill 后成孤儿） |
| 冻结 overlay | `skills-codex-gemini-review/` 移出这 2 个副本（7 → 5），README 同步 |
| 引用改写 | 26 个文件的 `/idea-discovery` → `/autoresearch`（含 5 个 shared-reference、8 个 skill、模板） |
| 库存 | `skill-groups.tsv` / `SKILLS_CATALOG.md` 各删 2 行；11 处 live count **51 → 49** |
| 检查器 | `iteration_log` 接线检查改读 `idea-creator`（内容已在 round 2 写回） |
| 结果 | **961 passed / 4 skipped**，`ARIS skill inventory is consistent.`（49 skills） |

**保留不删**（并记入本节以免以后被误删）：

- `experiment-bridge` —— 它就是 S7 实现阶段的执行体，改名 `method-implement` 的成本
  （1 个 test + 9 处文档 + 目录/镜像/计数）高于收益。
- `auto-review-loop` —— 独立的多轮评审闭环（Workflow 2），autoresearch 的 S3/S8 评审
  只是在流水线里各用一次，不构成替代。

**遗留内部标识**：`tools/run_state.py` 与 `tests/test_run_state.py` 里仍有字符串
`idea-discovery-evidence`，它是 run_state 的 gate **名字**（测试夹具），不是 skill 引用，
改名会影响历史 run 记录的可读性，故保留。
