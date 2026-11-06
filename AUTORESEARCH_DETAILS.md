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

## B. 文件最小字段（缺字段 = stage 未完成，`tools/autoresearch_state.py --validate` 会拦）

| 文件 | 必含字段 |
|---|---|
| `paper_search.md` | 每篇：标题/会议年份/链接/代码仓库/摘要/核心问题/数学方法/实验设置/结果/局限/缺口 |
| `baseline_selection.md` | 推荐 baseline + 3 条理由 + 代码环境数据算力需求 + 复现指标 + 可改模块 |
| `ideas.md` | 每个：研究问题/方法概述/数学机制/与 baseline 差异/预期指标/可能失败原因/**可证伪假设** |
| `idea_cards.md` | 每卡：5 维评分（假设成立性、数学一致性、兼容性、成本、风险）+ 依据 + **GO/REVISE/KILL** |
| `idea_ranking.md` | 排序 + 推荐 + 为什么不是第一名 |
| `method_proposal.md` | RQ / Hypothesis / 数学定义与推导 / 与 baseline 差异 / 模块与接口 / 创新性证据 / 预期贡献与风险 |
| `baseline_report.md` | 复现指标 vs 论文指标（逐项偏差）+ 失败案例 + 环境快照 + 未复现项及原因 |
| `research_contract_v1.md` | Hypothesis / Method Spec / Experimental Protocol / **Success Signal** / **Failure Signal** / Ablation Plan / Resource Budget / Decision Rules |
| `implementation_report.md` | 公式↔代码逐项对照（公式编号 → 文件:行 → 测试名） |
| `experiment_analysis.md` | 每个 claim 是否有实验支持 + 统计 + 失败机制 |
| `research_decision.md` | **Continue / Revise / Kill** + 依据 claim id + 下一步 |
| `next_hypothesis.md` | 由失败/异常信号长出的下一轮假设（喂回 S4） |

## C. 状态机

```json
{ "run_id": "run_20260815_ab12cd34",
  "stage": "S5",
  "status": "waiting_human",
  "contract_version": "v1",
  "artifacts": { "method_proposal.md": {"sha256": "...", "by": "DSH", "at": "..."} },
  "gates": { "human_method_approved": false, "contract_frozen": false } }
```

- `status ∈ {pending, running, blocked, waiting_human, done}`
- 进 S5 前 `human_method_approved=true`；进 S7 前 `contract_frozen=true`
- S8 出 `Revise` → `stage=S4`、`contract_version++`，旧 contract 只读

**三类人工接触点要分开记，别混成一个**：

| 类型 | 位置 | 引擎行为 | 记录 |
|---|---|---|---|
| Gate A 方法批准 | S4→S5 | 进 `waiting_human`，**阻塞流水线** | `gates.jsonl` + `human_method_approved=true` |
| Gate B 契约冻结 | S6→S7 | 进 `waiting_human`，记 sha256 后解锁 | `contract_frozen=true` |
| Decision C/R/K | S8 末尾 | **不阻塞**：本 run 已到终点，等你选 Continue/Revise/Kill 才开下一 run | `research_decision.md` + `gates.jsonl` |

## D. 三条防造假硬约束

1. **Contract 不可变**：S6 冻结记 sha256；`tools/contract_guard.py` 在 S7/S8 启动前校验，改过 → `BLOCKED`，只能新建 v2。
2. **Claim→证据链**：`tools/evidence_chain.py` 要求每个 claim 落到 `experiment_results/<run_id>/` 真实文件；缺失 → 标 `UNADJUDICATED`。
3. **产物只增不改**：`experiment_results/`、`baseline_logs/` 只允许新目录，禁止改写（hook + git 检查）。

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

## G. 要动哪些文件

**新增 3 个 skill**：`baseline-repro`（S5）、`research-contract`（S6）、`autoresearch`（编排器，由 `/idea-discovery` 改写）。

**改写 6 个**：`research-lit`→S1 双文件；`idea-creator`→S2 字段；`research-review`→S3 评分卡；`research-refine`→S4 提案；`experiment-bridge`→`method-implement`；`analyze-results`→S8 决策面。

**删除 4 个旧编排器**：`/idea-discovery`、`/experiment-bridge`、`/auto-review-loop`、`/idea-discovery-robot`（机器人特化改成 `/autoresearch --robot`）。约 30 个原子 skill 保留不动。

**新增 3 个 tool**：
- `tools/autoresearch_state.py` — state 读写、gate 检查、stage 迁移、`--validate` 字段校验
- `tools/contract_guard.py` — 冻结与变更加固
- `tools/evidence_chain.py` — claim↔实验追溯

**配套**：
- `templates/RESEARCH_CONTRACT_TEMPLATE.md` → 预注册字段（Success/Failure Signal、Decision Rules、v2 规则）
- `tools/skill-groups.tsv` → 新增 `autoresearch` 组；删掉退役的 4 个
- `docs/SKILLS_CATALOG.md`、`AGENT_GUIDE.md`、装机脚本、Feishu 通知模板
- `.gitignore` → 忽略实验产物（logs/weights/checkpoints），保留 `research/*.md`
- `install_aris.sh` → 可选步骤：装两个 `.md` 到 `~/.gemini/config/agents/`；打印 F 节的 `- insert:` YAML

## H. 验收标准（可测）

1. `dsh --profile web --dump-config` 能看到 3 条 `@deepseek-ai/dsh-mcp-client`；进 DSH 后三个工具各成功调用一次（`model-worker` 要真写出一个文件）。
2. 空项目装 `--groups autoresearch` 后，`/autoresearch "方向"` 能从 S1 走到 S4 并**停在 human gate**。
3. `--resume` 能从 `waiting_human` 继续；kill 进程重开不丢状态。
4. 8 个 stage 文件按 B 节字段生成（`autoresearch_state.py --validate` 通过）。
5. 篡改 `research_contract_v1.md` 后启动 S7 → `BLOCKED`。
6. 删掉一个 `experiment_results/` 目录 → `evidence_chain.py` 报出受影响 claim。
7. `pytest tests/ -q` 全绿；`check_skills_inventory.py` consistent。

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
