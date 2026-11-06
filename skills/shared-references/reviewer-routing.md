# Reviewer Routing

## Default Routing

The selectable-reviewer contract is authoritative in
[reviewer-backends.md](reviewer-backends.md): resolve **invocation directive →
`.aris/reviewer.json` → host default** with `reviewer_route.py`. It supplies the
Antigravity, Grok and local Claude Code protocols, session rules, and acceptance
requirements. The defaults and legacy routes below apply after that selection.
A project or invocation choice takes precedence over the host default.

When no invocation or project override is selected, the default reviewer backend
depends on the skill and execution environment:

| Skill | Default backend | Opt-in override |
|-------|----------------|-----------------|
| `/auto-review-loop` | **`codex`** | `codex` / `antigravity` (`gemini`) / `grok` / `claude-code` (`claude`, `claude-review`), plus the legacy routes below |
| All other reviewer skills | **Codex MCP** (`mcp__codex__codex`), model **`gpt-6-astra`** | `antigravity` / `grok` / `claude-code`, plus `oracle-pro` / `agy` / `manual` |

### Codex MCP Tiered Reasoning-Effort Policy

When Codex MCP is the resolved backend (the Claude Code host default), model **`gpt-6-astra`** (GPT-6-Astra) is used with a **two-tier reasoning-effort policy** (since 2026-07-10; `ultra`/`max` need codex-cli ≥ 0.144.1):

| Tier | `model_reasoning_effort` | Which calls |
|------|--------------------------|-------------|
| **Deep-audit** | `ultra` | `/proof-checker` · `/kill-argument` (attack / defense / adjudication threads; beast-mode extra axis probes stay `xhigh`) · `/research-review` · `/experiment-audit` · `/paper-claim-audit` · `/result-to-claim` · `/meta-apply` |
| **Regular** | `xhigh` | every other reviewer call — including ALL rounds of `/auto-review-loop` and other multi-round loops (a `codex-reply` cannot change model/effort mid-thread), and per-item fan-outs like `/citation-audit` (per-entry fresh calls would multiply `ultra`'s delegation cost for no verdict gain) |

**Always pin BOTH `model` and `config.model_reasoning_effort` explicitly in the first call of every thread.** Do not rely on the user's `~/.codex/config.toml`: model and host defaults can be below the review floor.

`ultra` = deepest reasoning + automatic task delegation — right for one-shot verdict-bearing audits, wrong for per-item loops (slower, pricier). Effort enums accepted by codex-cli ≥ 0.144.1: `none / minimal / low / medium / high / xhigh / max / ultra`. `max` and `ultra` both sit above `xhigh`; ARIS uses `ultra` for the deep-audit tier and does not use `max`.

> **Do not confuse the two "max"es.** ARIS's `— effort: lite|balanced|max|beast` ([effort-contract.md](effort-contract.md)) sets how much WORK the pipeline does; Codex's `model_reasoning_effort: …|max|ultra` sets how hard the REVIEWER thinks. `— effort: max` does NOT imply `model_reasoning_effort: max`.

### Codex capability fallback (new reviewer sessions only)

Resolve the reviewer pair on the **first new Codex session of each tier** in a run, then reuse that resolved pair for later sessions of the same tier. Try the declared pair first (`gpt-6-astra` + `ultra` for deep-audit; `gpt-6-astra` + `xhigh` for regular). Then:

- Only if the call fails **before returning a usable thread** AND the error **explicitly identifies the requested effort as unsupported** (older codex-cli): retry `gpt-6-astra` + `xhigh`. (This step exists only for the deep tier's `ultra` — a regular-tier `xhigh` call skips it; `xhigh` predates 0.144.1.)
- Only if the error **explicitly identifies `gpt-6-astra` as unknown or unavailable** to this account/plan: retry `gpt-6.1-sol` + `xhigh`, then `gpt-5.6-sol` + `xhigh`, then `gpt-5.5` + `xhigh` (skip redundant intermediate steps). When a complete host model list is available, skip every unlisted model in this fallback chain, including `gpt-6.1-sol`; when no complete host model list is available, fall through them only on the same explicit model-capability error.
- **NEVER downgrade on** timeout, rate-limit/capacity, authentication, transport/protocol, server, sandbox/tool, context-length, malformed-request, or response-parse errors — a blind downgrade retry there risks double-running (and double-billing) a review that may have gone through.
- **Never run a verdict-bearing review below `xhigh`.** `gpt-5.4` is available only as an explicit user override for legacy/repro runs — it is NOT part of the automatic chain.
- Replies (`codex-reply`) inherit the successful session's model and effort — pass only the saved `threadId` plus the message.
- Trace every attempt, the resolved pair, and the fallback reason (see `review-tracing.md`); the trace records the pair that actually ran, not the target pair.
- If no allowed pair succeeds, emit `REVIEW_UNAVAILABLE` (or, for a mandatory audit gate, `ERROR`) — never a substantive verdict.
- This automatic chain applies only when no explicit reviewer-model override was supplied.

### Optional HTTP API fallback for Codex pre-dispatch failures

Claude Code + ARIS Skills may use the existing `llm-chat` MCP as an **opt-in
transport fallback** when the Codex reviewer cannot be started safely. This does
not replace the Codex capability chain above and it is disabled by default.
The user must explicitly configure the `llm-chat` server with
`LLM_REVIEW_FALLBACK_ENABLED=true`; only then does it expose
`mcp__llm-chat__review` and `mcp__llm-chat__review_reply`. The legacy
`mcp__llm-chat__chat` tool by itself is **not** a verdict-bearing fallback.
This transport fallback applies to Codex **MCP** review calls; Codex-exec
nightmare-mode behavior is unchanged.

#### Safe switch boundary

The fallback is intentionally **pre-dispatch-only**, matching ARIS-Code's
reviewer fallback safety rule:

- First apply the Codex model/effort capability fallback above.
- HTTP fallback MAY run when the Codex path is known not to have produced a
  review: the Codex MCP tool is absent/unregistered, the local MCP process
  cannot spawn or initialize, or an error explicitly proves the reviewer
  request was rejected before model execution.
- HTTP fallback MUST NOT run merely because a dispatched Codex call timed out,
  disconnected, returned an ambiguous transport/server/parse failure, or
  otherwise might have executed without returning a usable thread. Keep the
  existing `REVIEW_UNAVAILABLE` / `ERROR` behavior in those cases; silently
  issuing a second paid review risks double-running and conflicting verdicts.
- The existing `NEVER downgrade on ...` list above remains authoritative. An
  error from that list may activate HTTP fallback only when the error itself
  positively establishes that no model request was dispatched.

This boundary is deliberately narrower than "Codex returned any error." Users
who explicitly want a different reviewer regardless of Codex state should pick
that backend directly (`antigravity`, `grok`, `claude-code`, or a supported legacy
route) instead of relying on fallback.

#### HTTP fallback call contract

For a fresh fallback review, use:

```
mcp__llm-chat__review:
  prompt: [same substantive review task Codex would receive]
  executor_model: <actual executor model id>
  files:
    - <primary artifact path 1>
    - <primary artifact path 2>
```

Do **not** pass Codex-only fields such as `config.model_reasoning_effort`,
`sandbox`, `approval-policy`, `cwd`, `threadId`, base/developer instructions, or
other Codex transport parameters. `llm-chat` reads each explicit `files:` entry
locally and sends the primary artifact contents verbatim to the configured HTTP
endpoint; this is necessary because a remote OpenAI-compatible API cannot read
local Linux paths. Pass primary artifacts, not executor-written summaries, per
`reviewer-independence.md`.

For every follow-up after the HTTP fallback owns the reviewer thread — including
round 2+ and a hard-mode rebuttal ruling in the same round — use:

```
mcp__llm-chat__review_reply:
  threadId: <saved llm-chat threadId>
  prompt: [follow-up review task]
  files:
    - <changed/current primary artifacts the reviewer must inspect>
```

`review_reply` carries the prior user/reviewer exchanges in the MCP server, so
multi-round skills do not silently lose continuity when the fallback activates.

For `/auto-review-loop`, a safe HTTP fallback means the HTTP reviewer is the
backend that actually ran the current round. **Before the HTTP call**, replace
the current-round snapshot as well as the forward-looking backend:

```
REVIEWER_BACKEND=llm-chat
round_backend=llm-chat
round_requires_external_acquittal=false
```

Then pass the returned `reviewer_model` (not merely the requested alias) to
`review_gate.py --round-backend llm-chat`. The fallback must not inherit a
stale external-acquittal obligation from some unrelated round.

The HTTP reviewer transport fails closed unless it can derive known, different
families for `executor_model` and the **actual reviewer model**. The response
includes `reviewer_model`, `reviewer_family`, `executor_model`,
`executor_family`, and `independence_verified`. Prefer the provider-reported
model id when available; if the configured HTTP provider internally switches to
`LLM_FALLBACK_MODEL`, trace the model that actually served the review. Missing,
unknown, ambiguous, or same-family identity is `REVIEW_UNAVAILABLE` for an
acceptance gate.

#### Configuration and privacy

Example Claude Code registration:

```bash
claude mcp add llm-chat -s user \
  --env LLM_API_KEY=<key> \
  --env LLM_BASE_URL=https://example.com/v1 \
  --env LLM_MODEL=gemini-2.5-pro \
  --env LLM_REVIEW_FALLBACK_ENABLED=true \
  -- python3 /path/to/mcp-servers/llm-chat/server.py
```

Restart Claude Code after changing MCP configuration. Enabling this fallback
means the explicit primary artifacts passed in `files:` are sent to the
configured third-party HTTP endpoint. Keep it disabled for repositories whose
contents must not leave the machine/provider boundary.

Trace the failed Codex attempt and the HTTP call separately. The verdict trace
must name backend `llm-chat`, the actual returned reviewer model, its family,
and the reason the safe fallback activated. If `mcp__llm-chat__review` is not
available, its call fails, or cross-family identity cannot be verified, emit
`REVIEW_UNAVAILABLE` (or `ERROR` for a mandatory gate) exactly as before.

### After upgrading codex-cli

MCP servers are spawned per session: after upgrading codex-cli (e.g. to 0.144.1 for `ultra`/`max`), **restart the Claude Code session** so the `codex` MCP server (`mcp-servers/codex-exec/server.py`, which runs `codex exec`) picks up the new binary — an old server process rejects the new effort enums even though the CLI on disk is new.

## Optional: GPT-5.5 Pro via Oracle

When the resolved selection is `oracle-pro`, route the review through Oracle
MCP instead of Codex MCP. This legacy route retains its warning/fallback behavior
below; the new MCP routes follow [reviewer-backends.md](reviewer-backends.md).

### Routing Logic (add to any reviewer-invoking skill)

```
Resolve invocation, project configuration and host default as described above.

If the resolved backend is `codex`:
    → Use mcp__codex__codex with model: gpt-6-astra at the tier's effort
      (deep-audit: ultra / regular: xhigh — see the Default table above).
    → This is the DEFAULT. No change from current behavior.

If the resolved backend is `oracle-pro`:
    → Check if mcp__oracle__consult tool is available
    → If available:
        Use mcp__oracle__consult with:
          model: "gpt-5.5-pro"
          prompt: [same prompt you would send to Codex]
          files: [file paths for reviewer to read directly]
        Note: Oracle may use API mode (fast, needs OPENAI_API_KEY)
              or browser mode (slow ~1-2 min, needs Chrome + ChatGPT login)
    → If NOT available:
        Print: "⚠️ Oracle MCP not installed. Falling back to Codex at this call's declared tier."
        Use mcp__codex__codex as normal.
```

### Invariants

- `oracle-pro` is opt-in through invocation or project selection; it is not the host default
- Reviewer independence protocol still applies (pass file paths, not summaries)
- `effort` and `difficulty` are orthogonal — they don't change reviewer backend
- `beast` mode may RECOMMEND oracle-pro but never requires it
- Browser mode: acceptable for one-shot reviews; NOT recommended inside multi-round loops (too slow/brittle)

### Oracle MCP Call Format

```
mcp__oracle__consult:
  prompt: |
    [role + task + output schema]
    Read all listed files directly.
  model: "gpt-5.5-pro"
  files:
    - /absolute/path/to/file1
    - /absolute/path/to/file2
```

### Skills That Support `— reviewer: oracle-pro`

| Skill | Use case for Pro |
|-------|-----------------|
| `/research-review` | Deeper critique on paper drafts |
| `/auto-review-loop` | Final stress test (last round only in browser mode) |
| `/experiment-audit` | Line-by-line eval code audit |
| `/proof-checker` | Deep mathematical reasoning |
| `/idea-creator` | Idea evaluation depth |
| `/research-lit` | Literature analysis depth |

### Installation

```bash
# Install Oracle CLI + MCP
npm install -g @steipete/oracle

# Add Oracle MCP to Claude Code
claude mcp add oracle -s user -- oracle-mcp

# Restart Claude Code session to load

# API mode (fast, recommended):
export OPENAI_API_KEY="your-key"

# Browser mode (no API key, slower):
# Just log in to ChatGPT in Chrome
```

### NOT installed = ZERO impact

If Oracle is not installed, `— reviewer: oracle-pro` gracefully falls back to Codex. No error, no breakage, just a warning.

### Upstream development & known issues

Oracle MCP is maintained at [`steipete/oracle`](https://github.com/steipete/oracle). When you invoke `— reviewer: oracle-pro` (and especially the `o3-deep-research` / `gpt-5.5-pro` paths), it's worth checking the **[open PRs](https://github.com/steipete/oracle/pulls)** for in-flight fixes that may affect your run — e.g., model routing changes, browser-mode auth fixes, rate-limit handling, or new model alias support. ARIS does not vendor Oracle MCP; you're running the published version from `npm install -g @steipete/oracle`. If a behavior surprises you, the upstream PR queue is the first place to check before opening an issue here.

## Selectable Antigravity, Grok and Claude Code reviewers

Select `— reviewer: antigravity` (alias `gemini`), `grok`, or `claude-code`
(aliases `claude` and `claude-review`) at an existing review step, or configure
its project default. These are formal reviewer routes in the complete skill
packs. Follow [reviewer-backends.md](reviewer-backends.md) for the resolver,
first-call and reply parameters, local file access, success signals and tracing.
No partial overlay installation is required.

A transport name does not establish family: Antigravity can run Claude, and the
local Claude Code CLI can use DeepSeek. Record the actual returned model and
its source; missing values stay unknown. A completed, in-scope, positive review
can be `cross-family / accepted` only when the actual executor and reviewer
families are known and differ. Same-family review stays provisional and may
stop a drive loop. Failed or incomplete calls cannot supply a positive verdict.
The selected new backend's unavailability is `REVIEW_UNAVAILABLE`, without
silently changing providers. Existing legacy fallbacks below retain their own
contracts.

`antigravity` is the separate Antigravity MCP, with default
`gemini-4-argon-high` / `high`; `grok` defaults to `grok-4.7` / `xhigh`.
`claude-code` uses its configured CLI provider unless a model is explicitly
selected, and its bridge has no effort argument. The older `agy` route below
continues to mean **gemini-review MCP**, not the separate Antigravity MCP.

## Optional: Gemini via Antigravity CLI (`— reviewer: agy`)

When the resolved selection is `agy`, route the review through the **gemini-review MCP** with the Antigravity (`agy`) backend — a native cross-model reviewer for Antigravity users who don't run Codex MCP / Oracle. Added in [#267](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/pull/267).

### Routing Logic (add to any reviewer-invoking skill)

```
Resolve invocation, project configuration and host default as described above.

If the resolved backend is `agy`:
    → Check if the gemini-review MCP tool is available (mcp__gemini-review__review).
    → If available (server configured with GEMINI_REVIEW_BACKEND=agy):
        Use mcp__gemini-review__review with:
          prompt: [same prompt you would send to Codex]
        For round 2+: mcp__gemini-review__review_reply with the saved threadId.
        For long paper/project reviews (avoid the ~120s MCP tool timeout):
          mcp__gemini-review__review_start + mcp__gemini-review__review_status (async).
    → If NOT available:
        Print: "⚠️ gemini-review (agy) MCP not configured. Falling back to Codex at this call's declared tier."
        Use mcp__codex__codex as normal.
```

### Invariants

- `agy` is opt-in through invocation or project selection; it is not the host default.
- **Cross-model family holds by construction.** The `agy` backend is fail-closed on ARIS's invariant: it recovers the *actual* Gemini-family model id from the current invocation's Antigravity transcript, **refuses** to return a verdict if the routed model is non-Gemini (no `"agy-cli"` placeholder), and binds the recovered transcript to *this* call via a **user-event nonce** (a model echo can't spoof the binding). So when the executor is Claude, `— reviewer: agy` (Gemini) satisfies the cross-model gate.
- Reviewer independence still applies — pass prompt context only (the `tools` arg is accepted for compatibility but ignored).
- `effort` and `difficulty` are orthogonal — they don't change the reviewer backend.

### Install

```bash
# Install + authenticate the Antigravity CLI (`agy`), then add the MCP with the agy backend:
claude mcp add gemini-review --env GEMINI_REVIEW_BACKEND=agy -- python3 <path>/mcp-servers/gemini-review/server.py
# (codex mcp add gemini-review ... for Codex CLI). Without the env var the server defaults to the direct Gemini API.
```

### NOT installed = ZERO impact

If the gemini-review (agy) MCP isn't configured, `— reviewer: agy` gracefully falls back to Codex at the call's declared tier (deep-audit: ultra / regular: xhigh). No error, no breakage, just a warning.

## Optional: Manual Review (any classifiable model, zero API cost)

When the resolved selection is `manual`, route the review through the manual-review MCP server. Instead of calling an API, it opens a browser page (or writes a file on headless Linux) where the user copies the prompt to a model of their choice and pastes the response back. The reviewer model must be one ARIS can classify by family (OpenAI, Anthropic, Google, DeepSeek, Moonshot/Kimi, Qwen); an unclassifiable name cannot be shown to differ from the executor's.

**Zero API cost. Works with any text-capable model.**

### Routing Logic

```
Resolve invocation, project configuration and host default as described above.

If the resolved backend is `manual`:
    → Check if mcp__manual_review__review tool is available
    → If available:
        Use mcp__manual_review__review with:
          prompt: [same review prompt you would send to Codex; the manual
                   transport wrapper also requires the response's first line
                   to be `Reviewer-Model: <exact-model-id>`]
          config: {"model_reasoning_effort": "xhigh", "executor_model": "<actual executor model>", "require_reviewer_model": true}
        For round 2+ in multi-round skills:
          Use mcp__manual_review__review_reply with:
            threadId: [saved from prior call]
            prompt: [follow-up prompt]
            config: {"model_reasoning_effort": "xhigh", "executor_model": "<actual executor model>", "require_reviewer_model": true}
    → If NOT available:
        Print: "⚠️ Manual Review MCP not installed. Install with: claude mcp add manual-review -s user -- python3 /path/to/mcp-servers/manual-review/server.py"
        STOP. Do NOT fall back to Codex (the target user likely has no Codex subscription).
```

### Invariants

- `manual` is opt-in through invocation or project selection; it is not the host default
- **Cross-model family is mandatory, not optional.** "a model of their choice" above means any *classifiable, non-executor-family* model, determined dynamically from the actual executor model — not merely "non-Claude." Every verdict-bearing response must start with `Reviewer-Model: <exact-model-id>`; derive its family and compare it with the model-derived executor family. Missing, unknown, ambiguous, or same-family identity is `REVIEW_UNAVAILABLE` for an acceptance gate. The UI warning is advisory; the traced model identities and derivation are the gate.
- Prompt fidelity: the review task text is exactly what Codex would receive; the manual transport wrapper may add only the model-identity response-format line used by the provenance gate
- `config.model_reasoning_effort` is shown as a recommendation badge, not embedded in the prompt
- Thread continuity: `review_reply` shows previous exchanges so the user can maintain context in their chosen model
- Reviewer independence protocol still applies

### Thread continuity

For round 2+ in multi-round skills (`/auto-review-loop`, `/proof-checker` Phase 3):
- Use `mcp__manual_review__review_reply` with the saved `threadId`
- The browser page displays previous prompt/response exchanges
- The user should continue the conversation in the same model session for best results

### Installation

```bash
claude mcp add manual-review -s user -- python3 /path/to/mcp-servers/manual-review/server.py
```

### Modes

- **Browser mode** (default): opens a local web page on Windows/macOS/Linux desktop
- **File mode** (`MANUAL_REVIEW_MODE=file`): writes prompt to a per-thread subdirectory. Read `.aris/pending_review/pending_review.json` for the `prompt_file` and `response_file` paths — for headless/SSH environments

### Skills That Support `— reviewer: manual`

The following skills are wired for manual review (Claude Code only):

| Skill | Manual support |
|-------|----------------|
| `/research-review` | Yes |
| `/auto-review-loop` | Yes |
| `/experiment-audit` | Yes |
| `/proof-checker` | Yes |
| `/idea-creator` | Yes |

> `/research-lit` supports `oracle-pro` only; manual review is not wired because the skill has no reviewer call blocks.

> **Platform note**: This legacy manual-review recipe documents the main Claude
> Code skills. It does not limit the selectable Antigravity, Grok or Claude Code
> MCP routes, which are available in both complete host packs. Follow the active
> host's routing reference for its legacy manual/Oracle behavior.

### Nightmare mode (Codex-only)

Manual review supports medium/hard MCP-style review. Codex-exec nightmare mode is Codex-only and must fail closed when reviewer is manual.

### NOT installed = explicit error (not silent fallback)

If manual-review MCP is not installed, `— reviewer: manual` prints install instructions and stops. It does NOT fall back to Codex — the target user likely has no Codex subscription, so a silent fallback would fail anyway.

### `codex exec` CLI is NOT an equivalent Codex backend

The mainline reviewer contract is `mcp__codex__codex` + `mcp__codex__codex-reply`: skills rely on **thread continuity** (e.g. `/idea-creator` Phase 4 runs its devil's-advocate triage as a same-thread `codex-reply`), structured returns, and saved `threadId` traces. `codex exec --ephemeral` is a stateless one-shot — fine for a single self-contained review, but NOT a drop-in replacement: hand-rewriting every MCP call to `codex exec` silently loses reply continuity and tends to mangle SKILL.md instructions (observed in the wild as "the executor skips phases and improvises" — issue #284).

If Codex MCP is broken in your setup, prefer in order:

1. Fix the MCP registration: `claude mcp add codex -s user -- python3 "$HOME/aris_repo/mcp-servers/codex-exec/server.py"` (codex-cli 0.154 removed `codex mcp-server`; the bridge replaces it — verified on 0.153.4 and 0.154.0, needs `codex exec resume`), then `/mcp` in-session to (re)connect.
2. Codex-CLI-as-executor: use the native mirror pack [`skills/skills-codex/`](../skills-codex/) — designed to run inside Codex CLI without Claude-side MCP.
3. One-shot `codex exec` only for skills whose review is a single call with no follow-up reply.
