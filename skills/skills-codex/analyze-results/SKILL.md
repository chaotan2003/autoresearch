---
name: "analyze-results"
description: "Analyze ML experiment results, compute statistics, generate comparison tables and insights. Use when user says \"analyze results\", \"compare\", or needs to interpret experimental data."
---

# Analyze Experiment Results

## Autoresearch stage contract

When this skill runs under `/autoresearch` it is stage **S8**. It finishes exactly
when the state machine says so, and it does not continue into the next stage.

| | |
|---|---|
| reads | `research/research_contract_v1.md` |
| writes | `research/experiment_analysis.md`, `research/research_decision.md` |
| actor | DSH runs the matrix, agents analyse |
| gate after | none (ends the run) |

Close it with `python3 "$STATE" done` (resolve `$STATE` as in `/autoresearch` § Helper resolution), which refuses to pass while a promised file is missing.
Everything below is this stage's method; the table decides when the stage is done.

Analyze: $ARGUMENTS

## Workflow

### Step 1: Locate Results
Find all relevant JSON/CSV result files:
- Check `figures/`, `results/`, or project-specific output directories
- Parse JSON results into structured data

### Step 2: Build Comparison Table
Organize results by:
- **Independent variables**: model type, hyperparameters, data config
- **Dependent variables**: primary metric (e.g., perplexity, accuracy, loss), secondary metrics
- **Delta vs baseline**: always compute relative improvement

### Step 3: Statistical Analysis
- If multiple seeds: report mean +/- std, check reproducibility
- If sweeping a parameter: identify trends (monotonic, U-shaped, plateau)
- Flag outliers or suspicious results

### Step 4: Generate Insights
For each finding, structure as:
1. **Observation**: what the data shows (with numbers)
2. **Interpretation**: why this might be happening
3. **Implication**: what this means for the research question
4. **Next step**: what experiment would test the interpretation

### Step 5: Update Documentation
If findings are significant:
- Propose updates to project notes or experiment reports
- Draft a concise finding statement (1-2 sentences)

## Output Format
Always include:
1. Raw data table
2. Key findings (numbered, concise)
3. Suggested next experiments (if any)

