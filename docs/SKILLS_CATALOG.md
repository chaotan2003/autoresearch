# ARIS Skills Catalog

Every skill that ships with ARIS, grouped by role. **48 skills** as of the
latest update; new skills land via PR and get added to the table below.

- Each `Skill` link goes to the canonical `SKILL.md` (the LLM-readable spec).
- `Role` is a one-line summary — see the `SKILL.md` for the full contract,
  phases, and triggers.
- `Requires` lists external dependencies beyond ARIS core (Codex MCP, Gemini
  API, Modal account, LaTeX toolchain, etc.). `None` means it works out of
  the box on a standard install.

> **Codex CLI mirror:** every skill below has a parallel implementation
> under [`skills/skills-codex/`](../skills/skills-codex/) for Codex CLI users.
> The mirror swaps the Codex-MCP reviewer path for Codex-native
> `spawn_agent` + `send_input`. SKILL semantics are otherwise identical;
> the table below tracks the main-tree canonical files.

---

## 🏗️ Workflow Orchestrators

End-to-end pipelines that chain many sub-skills. Most users start here.

| Skill | Role | Requires |
|---|---|---|
| [`/idea-discovery`](../skills/idea-discovery/SKILL.md) | **Workflow 1** — research-lit → idea-creator → novelty-check → research-review → research-refine-pipeline | Codex MCP |
| [`/idea-discovery-robot`](../skills/idea-discovery-robot/SKILL.md) | Workflow 1 adapter for robotics / embodied AI — robotics-aware literature survey + benchmark-anchored ideation | Codex MCP |
| [`/experiment-bridge`](../skills/experiment-bridge/SKILL.md) | **Workflow 1.5** — read experiment plan → implement code → sanity check → deploy to GPU → collect initial results | GPU (local / remote / Vast / Modal) |
| [`/auto-review-loop`](../skills/auto-review-loop/SKILL.md) | **Workflow 2** — autonomous review → fix → re-review until positive or max rounds; uses Codex MCP reviewer | Codex MCP |
| [`/auto-review-loop-llm`](../skills/auto-review-loop-llm/SKILL.md) | Same as Workflow 2 but uses any OpenAI-compatible LLM via [`llm-chat`](../mcp-servers/llm-chat/) MCP server | llm-chat MCP |
| [`/research-refine-pipeline`](../skills/research-refine-pipeline/SKILL.md) | Sub-pipeline used by `/idea-discovery` — refine method + plan experiments in one chain | Codex MCP |
| [`/dse-loop`](../skills/dse-loop/SKILL.md) | Autonomous design-space exploration loop for computer architecture / EDA — run → analyze → tune → iterate until objective met | Domain-specific tools |
| [`/meta-optimize`](../skills/meta-optimize/SKILL.md) | **Workflow M** — analyze ARIS usage logs and propose SKILL.md / prompt / default-parameter improvements (outer-loop self-evolution) | Codex MCP, hook logging |
| [`/meta-apply`](../skills/meta-apply/SKILL.md) | **Privileged landing gate** — the only skill allowed to mutate the skill corpus; lands `/meta-optimize` patches the human approved, after a fresh cross-model jury PASS on the staged diff (read-only producer ≠ privileged applier) | Codex MCP, human-in-loop |

## 📚 Literature & Search

Paper retrieval, summarization, novelty verification.

| Skill | Role | Requires |
|---|---|---|
| [`/research-lit`](../skills/research-lit/SKILL.md) | Multi-source literature search — Zotero / Obsidian / local PDFs / web / arXiv / S2 / DeepXiv / Exa / Gemini / OpenAlex with cross-source dedup | None (sources gated by MCP / SDK availability) |
| [`/arxiv`](../skills/arxiv/SKILL.md) | Search, download, summarize arXiv papers; multi-result table + per-paper detail | None |
| [`/semantic-scholar`](../skills/semantic-scholar/SKILL.md) | Published-venue paper search (IEEE / ACM / Springer) — citation counts, venue metadata, TLDR | None (rate-limited without S2 API key) |
| [`/deepxiv`](../skills/deepxiv/SKILL.md) | Progressive paper reading — search → brief → head → section → trending → web search | `pip install deepxiv-sdk` |
| [`/exa-search`](../skills/exa-search/SKILL.md) | AI-powered broad web search with content extraction — blogs, docs, news, papers | `pip install exa-py` + `EXA_API_KEY` |
| [`/keenable-search`](../skills/keenable-search/SKILL.md) | Keyless broad web search with page-text snippets, plus fetching a known URL as markdown (blogs, docs, project pages, news) | None (optional `KEENABLE_API_KEY` raises rate limits) |
| [`/firecrawl-search`](../skills/firecrawl-search/SKILL.md) | Broad web search with full-page markdown, plus scraping a known URL (HTML or PDF) to markdown — blogs, docs, project pages, technical reports | `FIRECRAWL_API_KEY` |
| [`/web-debug-search`](../skills/web-debug-search/SKILL.md) | Multi-source debugging search across GitHub, Stack Exchange, Chinese technical communities, and general web — routing, compatibility, and discovery-only results | None |
| [`/openalex`](../skills/openalex/SKILL.md) | OpenAlex API search — 250M+ open citation graph, institutional affiliations, funding data | `pip install requests` |
| [`/gemini-search`](../skills/gemini-search/SKILL.md) | Gemini-driven literature discovery — decomposes topics into sub-problems, aliases, variants | `gemini-cli` v0.40+ |
| [`/alphaxiv`](../skills/alphaxiv/SKILL.md) | Quick single-paper lookup via [AlphaXiv](https://www.alphaxiv.org) — three-tier fallback (overview → markdown → LaTeX source) | None |
| [`/novelty-check`](../skills/novelty-check/SKILL.md) | Verify a research idea is novel against recent literature — multi-source search + cross-model verification + closest-prior-work table | Codex MCP |

## 💡 Ideation & Method Design

Generating, refining, planning research ideas before implementation.

| Skill | Role | Requires |
|---|---|---|
| [`/idea-creator`](../skills/idea-creator/SKILL.md) | Brainstorm 8-12 ideas, filter by feasibility, pilot on GPU, rank by signal | Codex MCP, GPU for pilots |
| [`/research-refine`](../skills/research-refine/SKILL.md) | Iterative method refinement — problem anchor → up to 5 review rounds → score ≥ 9 | Codex MCP |
| [`/experiment-plan`](../skills/experiment-plan/SKILL.md) | Turn a refined proposal into a claim-driven experiment roadmap — ablations, budgets, run order | None |
| [`/ablation-planner`](../skills/ablation-planner/SKILL.md) | Design ablation studies from a reviewer's perspective (after main results pass `/result-to-claim`) | Codex MCP |
| [`/formula-derivation`](../skills/formula-derivation/SKILL.md) | Structure theory derivations — organize assumptions, build derivation chains, turn scattered equations into coherent narrative | None |

## 🧠 Proof Engineering

Orchestrating and independently auditing mathematical proofs.

| Skill | Role | Requires |
|---|---|---|
| [`/proof-orchestrator`](../skills/proof-orchestrator/SKILL.md) | Stateful proof-run orchestration: run directories, cross-run continuation, manual GPT Pro handoff packages, optional DeepSeek second opinion (additional evidence only — `/proof-writer` drafts proofs, `/proof-checker` owns verification and submission acceptance) | None by default; llm-chat MCP only for optional DeepSeek review |
| [`/proof-writer`](../skills/proof-writer/SKILL.md) | Draft rigorous mathematical proofs for ML / AI theory — theorems, lemmas, propositions, corollaries; fill in missing steps; formalize sketches | None |
| [`/lean-formalize`](../skills/lean-formalize/SKILL.md) | Formalize, continue, or audit a Lean proof when requested or useful for a substantial mathematical obligation; preserve the original statement, connect actual inputs, and verify the final declaration and its axioms | Lean project/toolchain; authorized cross-family reviewer for substantial proof checkpoints |

## 🧪 Experiments & Infrastructure

GPU job submission, scheduling, monitoring, profiling.

| Skill | Role | Requires |
|---|---|---|
| [`/research-implement-feature`](../skills/research-implement-feature/SKILL.md) | Build from a plain "implement X" request — runnable spine first, then one feature per rung; every under-determined decision declared in an assumption ledger before the code depends on it, plus a cross-model sweep for the ones that slipped through undeclared | Codex MCP |
| [`/run-experiment`](../skills/run-experiment/SKILL.md) | Deploy experiments to local / remote / Vast.ai / Modal GPU | GPU (configurable) |
| [`/monitor-experiment`](../skills/monitor-experiment/SKILL.md) | Monitor running experiments, check progress, collect results | None |
| [`/analyze-results`](../skills/analyze-results/SKILL.md) | Compute statistics, generate comparison tables, surface insights from experiment results | None |
| [`/experiment-queue`](../skills/experiment-queue/SKILL.md) | SSH job queue for multi-seed / multi-config sweeps — OOM retry, stale-screen cleanup, wave gating, crash-safe state | SSH access |
| [`/vast-gpu`](../skills/vast-gpu/SKILL.md) | Rent, manage, destroy on-demand GPU on [Vast.ai](https://vast.ai) | Vast.ai account + `vast-cli` |
| [`/serverless-modal`](../skills/serverless-modal/SKILL.md) | Run GPU workloads on [Modal](https://modal.com) — zero-config serverless, auto scale-to-zero | `pip install modal` + Modal account |
| [`/qzcli`](../skills/qzcli/SKILL.md) | Manage GPU compute jobs on the Qizhi (启智) platform via `qzcli` (kubectl-style CLI) | `qzcli` installed |
| [`/training-check`](../skills/training-check/SKILL.md) | Periodically poll W&B metrics during training — catch NaN, loss divergence, idle GPUs early | W&B account |
| [`/system-profile`](../skills/system-profile/SKILL.md) | Profile a target (script / process / GPU / memory / interconnect) with external tools + code instrumentation; produce actionable report | Profiling tools |

## 🛡️ Review, Audit & Assurance

Cross-model critique, integrity checking, evidence verification.

| Skill | Role | Requires |
|---|---|---|
| [`/research-review`](../skills/research-review/SKILL.md) | Single-round deep critical review from external LLM (Codex GPT xhigh by default; `oracle-pro` route for Pro tier) | Codex MCP (or Oracle MCP) |
| [`/experiment-audit`](../skills/experiment-audit/SKILL.md) | Cross-model integrity check of experiment code + results — catches fake ground truth, score-normalization fraud, phantom results, scope inflation | Codex MCP |
| [`/result-to-claim`](../skills/result-to-claim/SKILL.md) | Map experimental results to intended claims — judges what's supported, what's not, what's missing; routes to next action | Codex MCP |
| [`/proof-checker`](../skills/proof-checker/SKILL.md) | Rigorous mathematical proof verification — 20-category issue taxonomy, two-axis severity, side-condition checklists, counterexample red team, proof-obligation ledger | Codex MCP |
| [`/kill-argument`](../skills/kill-argument/SKILL.md) | Two-thread adversarial review — Thread 1 writes the strongest 200-word rejection memo; Thread 2 (independent) defends point-by-point and surfaces still-unresolved issues | Codex MCP |

## 🧰 Meta, Utilities & Integrations

Cross-cutting infrastructure used by other skills or run on demand.

| Skill | Role | Requires |
|---|---|---|
| [`/research-wiki`](../skills/research-wiki/SKILL.md) | Persistent research knowledge base — papers / ideas / experiments / claims with typed relationships. Workflow hooks auto-ingest across the research lifecycle | None (pure Python stdlib) |
| [`/wiki-enrich`](../skills/wiki-enrich/SKILL.md) | Fill the per-paper TODO sections that `ingest_paper` leaves as scaffolds (Karpathy LLM-wiki principle). Fetch chain alphaxiv → deepxiv → arXiv → page abstract; idempotent by default, `--force` to rewrite | Python stdlib + WebFetch |
| [`/render-html`](../skills/render-html/SKILL.md) | Render ARIS Markdown / JSON artifacts into reviewed single-file HTML views for human reading | Python stdlib; Codex MCP for review gate |
| [`/feishu-notify`](../skills/feishu-notify/SKILL.md) | Send notifications to Feishu / Lark — push-only (webhook) or interactive (bidirectional) modes. Off by default | Feishu webhook URL |

---

## How to use this catalog

- **Looking for a workflow entry point?** Start with [Workflow Orchestrators](#%EF%B8%8F-workflow-orchestrators).
- **Want to add a skill to an existing workflow?** Read the orchestrator's
  `SKILL.md` to see which sub-skills it composes.
- **Building your own pipeline?** Pick the skills from each category and
  chain them via prompt — no framework lock-in, every skill is a single
  `SKILL.md` readable by any LLM agent.

## Adding a new skill

1. Create `skills/<name>/SKILL.md` with `name:` + `description:` frontmatter
   (the description shows up in the LLM's slash-command autocomplete).
2. Per the
   [`integration-contract.md`](../skills/shared-references/integration-contract.md)
   §2 contract, if your skill invokes any helper script under `tools/`, use
   the canonical resolver chain — do NOT hardcode `python3 tools/foo.py`.
3. Add a row to the appropriate category table above (or propose a new
   category in your PR if your skill doesn't fit).
4. The advisory CI lint will catch any hardcoded-path regressions on PR.

See the [main README](../README.md) for installation, setup, and end-to-end
workflow examples.
