---
name: baseline-repro
description: 'Reproduce the selected baseline before claiming any improvement: pin the environment, run the published setting, record the number next to the expected number, and report the deviation instead of tuning it away. Use when the user says "reproduce the baseline", "复现 baseline", "run the baseline", "跑通 baseline", "baseline 复现", or before any method experiment needs a reference number.'
---

# Baseline Reproduction

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

The baseline number is the denominator of every later claim. A tuned baseline makes
the whole run worthless, so this stage prefers an honest deviation over a good number.

Argument: `$ARGUMENTS` (optional: `--stage S5` is implied by the state machine)

## Inputs

- `research/baseline_selection.md` — the chosen baseline, its arXiv ID, dataset,
  metric, compute budget and expected number.
- `research/paper_search.md` — for the exact setting and any released code link.
- `research/method_proposal.md` — only to know which knobs the method will change, so
  the baseline is frozen at the setting the method is compared against.

## Steps

1. **Freeze the setting.** Copy the published configuration verbatim into
   `research/baseline_config/`: model id, decoding parameters, seeds, dataset split,
   evaluation script, hardware. If the paper is ambiguous, write down the ambiguity and
   pick the setting that is closest to the one the method will be compared at.
2. **Pin the environment.** Record `python --version`, the framework version, the GPU
   and driver, and the exact commit of any cloned repo in
   `research/baseline_config/env.txt`. Container or lockfile preferred.
3. **Run small first.** One seed, a small subset, to prove the harness gives a
   number at all. Then the published setting, seeds matching the paper (or 3 if unstated).
4. **Keep every log.** `research/baseline_logs/<run-id>.log` plus the raw metrics file.
   A number without a log path cannot enter the report.
5. **Compare honestly.** Write the reproduced number next to the expected number and the
   absolute and relative deviation.

## Output: research/baseline_report.md

```markdown
# Baseline reproduction

- Baseline: <name> (<arXiv id>)
- Setting: <dataset / split / metric / budget>
- Expected from paper: <number ± interval if stated>
- Reproduced: <number> (n seeds, mean ± std)
- Deviation: <abs> / <pct> — <within tolerance | outside tolerance>
- Verdict: reproduced | reproduced-with-caveat | not reproduced

## Runs
| run id | seed | command | log | metric |

## Deviations from the paper
<each difference and why, one line each>

## Environment
<python/framework/GPU/driver/commit>

## What this baseline fixes for the method stage
<the exact numbers and settings S7/S8 must compare against>
```

## Tolerance

Default tolerance is 1.0 absolute point or 2% relative, whichever is looser, on the
paper's primary metric. Outside tolerance is `reproduced-with-caveat` if the gap has a
known cause (different hardware precision, unstated preprocessing), and `not reproduced`
if the harness itself is in doubt. Never move the goalposts into the method stage; a
broken baseline stops the run here.

## Rules

- Do not tune the baseline toward the expected number. Do not add tricks the paper did
  not use. If you must change something to make it run, list it under deviations.
- Reuse `/run-experiment`, `/experiment-queue` and `/monitor-experiment` for remote or
  queued runs; this skill is the contract around them, not a replacement.
- Three failed reproduction attempts is a stop condition: `fail --reason`, write the
  question into `research/human_notes.md`, hand it to the user.

## Handoff

`python3 "$STATE" done` — refuses to close the stage unless
`research/baseline_report.md` exists. The next stage (`/research-contract`) reads this
file and nothing else about the baseline.