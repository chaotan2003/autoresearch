---
name: gemini-search
description: Search research papers via agy (Antigravity CLI driving a Gemini model) for broad literature discovery. Use when user says "gemini search", "gemini papers", "agy search", "search with gemini", or wants AI-powered literature discovery beyond arXiv/Semantic Scholar indexes.
argument-hint: "[search-query]"
allowed-tools: Bash(*), Read, Write, mcp__model-scout__*
---

# Gemini Literature Search (via agy)

Search query: $ARGUMENTS

## Role & Positioning

This skill uses the Gemini model, driven by the **`agy`** CLI, as a **broad literature discovery** source:

| Skill | Source | Best for |
|-------|--------|----------|
| `/arxiv` | arXiv API | Latest preprints, cutting-edge unrefereed work |
| `/semantic-scholar` | Semantic Scholar API | Published venue papers (IEEE, ACM, Springer) with citation counts |
| `/deepxiv` | DeepXiv CLI | Layered reading: search, brief, section map, section reads |
| `/exa-search` | Exa API | Broad web search: blogs, docs, news, companies, research papers |
| `/gemini-search` | `agy` + `aris-scout` | **AI-powered broad literature discovery** — searches across multiple angles, aliases, and sub-problems |

Use `agy` when you want AI-driven discovery that goes beyond keyword matching — it decomposes topics into sub-problems, explores naming variants, opens pages to confirm identifiers, and surfaces papers that traditional API searches may miss.

## Constants

- **MAX_RESULTS = 15** — Target number of papers the scout should find.
- **MIN_YEAR = 2022** — Default minimum publication year. Override with `— year: 2020-`.
- **DEFAULT_MODEL = gemini-3.8-flash-high** — Model passed to `agy --model`. Override with `— model: gemini-3-pro` when the query needs deeper synthesis. `agy models` lists what the logged-in account can actually reach.

> Overrides (append to arguments):
> - `/gemini-search "topic" — max: 20` — request up to 20 papers
> - `/gemini-search "topic" — year: 2020-` — papers from 2020 onward
> - `/gemini-search "topic" — code-only` — only papers with open-source code
> - `/gemini-search "topic" — venues: NeurIPS,ICML,ICLR` — focus on specific venues
> - `/gemini-search "topic" — model: gemini-3-pro` — stronger model for harder queries

## Environment & Setup

### Prerequisites

1. **agy** (Antigravity CLI) — installed and authenticated with a Google account

   ```bash
   agy --version
   ```

2. **`aris-scout` agent profile** — provides the `search_web` and `read_url_content` tools

   ```bash
   cp mcp-servers/model-worker/aris-scout.md ~/.gemini/config/agents/
   agy agent      # must list aris-scout
   ```

### MCP Configuration

Register the bridge (preferred path). `AGY_AGENT` selects the `agy` agent profile:

```json
{
  "mcpServers": {
    "model-scout": {
      "command": "python3",
      "args": ["/abs/path/to/aris/mcp-servers/model-worker/server.py"],
      "env": {
        "AGY_AGENT": "aris-scout",
        "MODEL_WORKER_ALLOWED_ROOTS": "[\"/abs/project\"]"
      }
    }
  }
}
```

The CLI fallback below needs no MCP server at all.

Codex one-liner equivalent:

```bash
codex mcp add model-scout \
  --env AGY_AGENT=aris-scout \
  --env 'MODEL_WORKER_ALLOWED_ROOTS=["/abs/project"]' \
  -- python3 /abs/path/to/aris/mcp-servers/model-worker/server.py
```

### Authentication

`agy` reuses the Antigravity login; no `GEMINI_API_KEY` is involved and no `gemini` binary is ever called. Headless runs (MCP, `-p`) must pass `--dangerously-skip-permissions`, otherwise any tool that would prompt is auto-denied and the run returns "no output produced".

### Tools Used

| Tool | Where | Description |
|------|-------|-------------|
| `search_web` | agy built-in | Broad multi-angle web/academic discovery |
| `read_url_content` | agy built-in | Open a result page to confirm its arXiv ID or DOI |
| `mcp__model-scout__worker` | MCP bridge | Start an `agy` session under the `aris-scout` profile |

### Verify Setup

```bash
agy agent | grep aris-scout
```

## Workflow

### Step 1: Parse Arguments

Parse `$ARGUMENTS` for:
- **query**: The research topic (required)
- **max**: Override MAX_RESULTS
- **year**: Minimum publication year (e.g., `2020-`)
- **code-only**: Only include papers with open-source code
- **venues**: Comma-separated venue filter
- **model**: Override DEFAULT_MODEL

### Step 2: Execute Search (MCP Priority)

**Priority 1 — agy over MCP** (preferred):

Call `mcp__model-scout__worker` with the search prompt. It starts an `agy` session under the `aris-scout` profile:

```
mcp__model-scout__worker({
  backend: 'antigravity',
  model: 'gemini-3.8-flash-high',
  effort: 'high',
  cwd: '<project root>',
  prompt: 'You are a research literature scout. Search comprehensively for papers on: "QUERY"

IMPORTANT CONSTRAINTS:
1. Search from MULTIPLE angles — do not just use the exact query. Decompose the topic into sub-problems, aliases, neighboring tasks, and common benchmark/settings variants.
2. Prefer papers that are genuinely relevant, not merely keyword-adjacent.
3. Include top venues, journals, surveys, recent preprints, and papers with code when available.
4. Focus on papers from MIN_YEAR onward unless older foundational work is necessary.

For EACH paper found, provide ALL of the following in this exact format:
- Title: [exact title]
- Authors: [full author list]
- Year: [publication year]
- Venue: [exact conference/journal name + year, or "arXiv preprint" if not published]
- arXiv ID: [format 2401.12345, or "N/A"]
- DOI: [if available, or "N/A"]
- Code URL: [GitHub/GitLab link if available, or "No code"]
- Summary: [one-sentence core contribution]

Find at least MAX_RESULTS papers with good coverage across:
- strong recent papers from top venues
- surveys/reviews if they exist
- papers with open-source code
- closely related variants of the topic

Format as a numbered list with all fields for each paper.',
  model: 'gemini-3.8-flash-high'
})
```

**Priority 2 — agy CLI fallback** (if the MCP server is unavailable):

If `mcp__model-scout__worker` fails or is not configured, run the same prompt through the CLI:

```bash
agy -p '<same prompt as above>' \
  --agent aris-scout --mode accept-edits \
  --disable-slash-commands --dangerously-skip-permissions \
  --output-format text 2>/dev/null
```

- **Timeout**: 300 seconds — the scout opens pages, which is slower than a chat completion
- **Stderr**: pipe to `/dev/null`; `agy` logs progress there

**When to use which:**
- MCP is preferred because it survives across calls, keeps a conversation thread, and avoids shell escaping issues.
- CLI fallback needs no MCP server at all — useful when the bridge is not configured or has crashed.

### Step 3: Parse Results

Extract structured paper information from Gemini's response. For each paper, normalize to:

```
{
  title, authors, year, venue,
  arxiv_id,    // "N/A" if not available
  doi,         // "N/A" if not available
  code_url,    // "No code" if not available
  summary      // one-sentence contribution
}
```

If Gemini returns fewer papers than requested, note this but do not re-query.

### Step 4: Present Results

Format results as a structured table:

```
| # | Title | Venue | Year | Code | Summary |
|---|-------|-------|------|------|---------|
| 1 | ... | NeurIPS 2024 | 2024 | [GitHub](url) | ... |
| 2 | ... | IEEE TWC | 2023 | No | ... |
```

For each paper, also show:
- **arXiv ID**: if available (for cross-reference with `/arxiv`)
- **DOI**: if available (canonical link for published papers)
- **Code**: GitHub/GitLab link or "No"

### Step 5: Offer Follow-up

After presenting results, suggest:

```text
/semantic-scholar "topic"    — search published venue papers with citation counts
/arxiv "arXiv:XXXX.XXXXX"   — fetch specific preprint details
/research-lit "topic" — sources: gemini, semantic-scholar  — combined multi-source review
/novelty-check "idea"       — verify novelty against literature
```

## Key Rules

- **MCP first, CLI second.** Always try `mcp__model-scout__worker` before falling back to `agy -p`.
- **The model is a discovery source, not a database.** Its results may include papers it "knows about" from training data. Always cross-verify critical details (exact titles, venues, years) via `/semantic-scholar` or `/arxiv` when precision matters.
- **Do not trust model-reported citation counts.** They are often hallucinated. Use Semantic Scholar for authoritative citation data.
- **Pipe stderr to `/dev/null` in CLI mode** — `agy` logs progress there.
- **Timeout generously in CLI mode** — a real scout run opens pages, so 300s is normal. A 120s timeout cuts it off mid-search.
- **`--dangerously-skip-permissions` is required headless.** Without it, `agy -p` cannot prompt and silently returns "no output produced".
- If both MCP and CLI are unreachable, suggest using `/semantic-scholar`, `/arxiv`, or `/research-lit "topic" — sources: web` as alternatives.
