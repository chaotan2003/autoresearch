---
name: autoresearch
description: 'Run the whole research pipeline as one state machine: literature → ideas → ranking → method → baseline → contract → implementation → experiments, stopping at human gates A and B. Use when the user says "run the research pipeline", "跑实验流水线", "/autoresearch", "start autoresearch", "继续研究", "resume research", or wants autonomous idea-to-experiment work with checkpoints instead of one-off prompts.'
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, mcp__codex__codex, mcp__codex__codex-reply, mcp__model-scout__worker, mcp__model-worker__worker, mcp__antigravity__antigravity
---

# Autoresearch: one pipeline, eight stages, three human contacts

Run the stage that `tools/autoresearch_state.py` says is next. Do not decide the
next step from memory and do not do two stages in one turn.

Argument: `$ARGUMENTS`

- empty → resume: `python3 tools/autoresearch_state.py next`
- `--status` → print `status --json` and stop
- `--stage S4` → `reopen --stage S4` only when the user asked to go back
- `<new direction>` and no state yet → `init --direction "<direction>"`
- `--robot` → read `research/direction.md` as the direction instead of the argument

## Loop

1. `python3 tools/autoresearch_state.py next --json`
2. Dispatch by the `actor` field (table below).
3. Check the artifacts on disk yourself. The child agent's chat reply is not evidence.
4. `start` before the work, `done` after it. `done` refuses a missing artifact; that
   refusal is the point, fix the file rather than passing `--artifacts` to dodge it.
5. When `status` is `waiting_human`, write the ask into `research/human_notes.md`,
   notify Feishu with `/feishu-notify`, and stop. Never approve your own gate.

## Dispatch

| Stage | Actor | How |
|---|---|---|
| S1 | scout | `mcp__model-scout__worker` (`backend: antigravity`, effort high) → `/research-lit` source `agy` |
| S2 | worker | `mcp__model-worker__worker` (`backend: antigravity`) → `/idea-creator` Phase 1-2 only |
| S3 | codex | `mcp__codex__codex` with `sandbox: "danger-full-access"` → `/research-review` in ranking mode |
| S4 | scout | `mcp__model-scout__worker` for novelty, `mcp__codex__codex` for a second opinion, then `/research-refine` |
| S5 | dsh | `/baseline-repro` — you run the commands, the agents do not |
| S6 | dsh | `/research-contract` then freeze |
| S7 | codex | `mcp__codex__codex` with `sandbox: "danger-full-access"` → `/method-implement` |
| S8 | dsh | run the matrix, then `/analyze-results` |

`agy` headless runs need `--dangerously-skip-permissions`; without it every tool
call is auto-denied and the run returns "no output produced". `codex` needs
`---sandbox danger-full-access` on this machine (bubblewrap cannot start) and
`IAIEMAS_API_KEY` in its environment.

## The task brief

Every dispatch sends paths, never content. Five fields:

```
READ ONLY:   <the stage's reads, exact paths>
WRITE:       <the stage's writes, exact paths>
MUST CONTAIN: <the fields this stage promises>
DO NOT:      <rank for S2, rank nothing else; invent no identifier; edit inputs>
REPORT:      changed paths + any gap that needs a human decision
```

Keep it under ~40 lines. A long brief with the upstream content pasted in defeats
the context isolation the pipeline exists for.

## Verification before `done`

| Stage | Check |
|---|---|
| S1 | `python3 tools/verify_papers.py --input research/paper_search.md` → every arXiv ID verified or explicitly N/A; at least 3 angles covered |
| S2 | `grep -c '^### idea_' research/idea_cards.md` is 10; every card has all 7 fields; no ranking words |
| S3 | `research/idea_ranking.md` has a score table and a weak list; top 3 named |
| S4 | `method_proposal.md` names the closest prior work and the delta in one sentence |
| S5 | `baseline_report.md` has the reproduced number next to the expected number and a deviation line |
| S6 | contract has all sections; sha256 frozen by `done` |
| S7 | `pytest` for the method passes; `implementation_report.md` maps each contract claim to a file |
| S8 | every claim in the contract has an experiment id and a result; no result without a log path |

## Hard rules

1. **One stage per turn.** A stage that fails does not silently merge into the next one.
2. **Never write a stage artifact yourself** when the stage's actor is an agent. If the
   agent fails twice, record `fail --reason` and put the question in `human_notes.md`.
3. **Never edit a frozen contract.** Bump to v2 with `done --contract-version 2`.
4. **Gates are human.** `gate approve` only on the user's explicit words; put the quote
   in `--note`.
5. **Fixtures never become results.** A number in `baseline_report.md` without a log path
   is a fabrication; refuse to write it.

## Failure protocol

First failure: same brief plus a `PREVIOUS ATTEMPT FAILED: <one line>` section, retried
once. Second failure: `fail --reason "..."`, append the question to
`research/human_notes.md`, notify Feishu, stop. Do not lower the acceptance bar to get
past a stage.

## Artifacts

State lives in `.autoresearch/state.json`; gate decisions append to
`.autoresearch/gates.jsonl`; every agent call is logged to
`.autoresearch/traces/<stage>/<timestamp>/` with the brief, the reply and the diff of
the files it touched.