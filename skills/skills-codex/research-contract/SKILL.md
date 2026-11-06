---
name: research-contract
description: 'Freeze a research claim into an immutable experiment contract: claim, hypothesis, variables, primary experiment, ablations, metric, success criterion, budget, stop condition, and the claim-to-experiment evidence map. Use when the user says "写研究合同", "freeze the contract", "research contract", "定实验计划并冻结", or before implementation so later results cannot quietly redefine what was being tested.'
---

# Research Contract

## Helper resolution

The state machine and the citation verifier live in the ARIS repo, not in the user's
project. Resolve them first, then call the variables:

```bash
ARIS_REPO="${ARIS_REPO:-}"
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills-codex.txt ]; then
  ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills-codex.txt 2>/dev/null) || true
fi
if [ -z "${ARIS_REPO:-}" ] && [ -n "${HOME:-}" ] && [ -f "$HOME/.aris/repo" ]; then
  ARIS_REPO=$(cat "$HOME/.aris/repo" 2>/dev/null) || true
fi
STATE=""
[ -n "$ARIS_REPO" ] && [ -f "$ARIS_REPO/tools/autoresearch_state.py" ] && STATE="$ARIS_REPO/tools/autoresearch_state.py"
[ -z "$STATE" ] && [ -f tools/autoresearch_state.py ] && STATE="tools/autoresearch_state.py"
VERIFY=""
[ -n "$ARIS_REPO" ] && [ -f "$ARIS_REPO/tools/verify_papers.py" ] && VERIFY="$ARIS_REPO/tools/verify_papers.py"
[ -z "$VERIFY" ] && [ -f tools/verify_papers.py ] && VERIFY="tools/verify_papers.py"
```

The contract is what the run promises to test. It is written before the method exists,
frozen by sha256, and never edited afterwards — that is the only way a later "it worked"
can mean anything.

Argument: `$ARGUMENTS` (optional emphasis, e.g. `--budget 8xA100-days`)

## Inputs

- `research/method_proposal.md` — the claim and the mechanism.
- `research/baseline_report.md` — the reference numbers and the frozen baseline setting.
- `research/idea_ranking.md` — the reviewer's reason the chosen idea is falsifiable.
- `research/human_notes.md` — any constraint the user already stated.

## Steps

1. Read the four inputs. Do not add a claim that no input supports.
2. Fill every section below. A section you cannot fill is a question for the user, not a
   place for plausible text — write `OPEN: <question>` and stop before freezing.
3. Write `research/research_contract_v1.md`.
4. Freeze it: `python3 "$STATE" done`. The tool stores the sha256 and
   moves the run to Gate B (`waiting_human`).
5. After the user approves, the file is read-only. Any change is a new version:
   bump to v2 with `done --contract-version 2` and keep v1 on disk.

## Output: research/research_contract_v1.md

```markdown
# Research contract v1 — <short title>

## Claim
One sentence: what will be true if this works, stated so it could be false.

## Hypothesis and mechanism
Why the intervention should move the metric. Two to four sentences, no hedging.

## Baseline
Name, arXiv id, and the exact numbers from research/baseline_report.md that all
comparisons use.

## Variables
- Independent: <the one thing the method changes>
- Controlled: <what is held fixed — data, budget, decoding, hardware>
- Measured: <the primary metric and the secondary diagnostics>

## Primary experiment
Dataset / split / seeds / budget / the exact command shape.
Success criterion: <metric> ≥ <baseline + delta> with <statistic> over <n> seeds.

## Ablations
Each ablation names the component it removes and the claim it tests.
| id | removes | claim tested | expected direction |

## Evidence map
Every claim fragment mapped to the experiment that can support or kill it.
| claim id | claim fragment | supporting experiment | kill condition |

## Budget
GPU-hours, wall-clock, and the cost of the primary experiment plus ablations.

## Stop conditions
What result would make continuing pointless, and what result triggers a redesign.
Decided now, before the numbers are known.

## Out of scope
What this contract explicitly does not test.
```

## Freeze rules

- The sha256 in `.autoresearch/state.json` is the version of record. `done` refuses to
  overwrite a frozen hash; `--contract-version 2` is the only way forward.
- v2 must state what changed and why, in a short `## Change log` section, and v1 stays on
  disk untouched.
- The experiment stage (S8) may not add a claim that is absent from the evidence map. A
  result that fits no claim id goes into `experiment_analysis.md` as an observation, not
  as support for the claim.

## Rules

- One dominant claim. A second contribution is allowed only if the first survives.
- Success criterion must be decidable by a script, not by reading the plots.
- Never write a predicted number into the contract as if it were measured.
- If the user vetoes the contract at Gate B, record why in `.autoresearch/gates.jsonl`
  via `gate reject --note "..."` and reopen S4; do not patch the contract in place.

## Handoff

Implementation (`S7`) reads only this contract. Experiments (`S8`) read only this
contract plus `method/`. If either stage needs a fact that is not in the contract, that
is a contract bug — report it, do not improvise.