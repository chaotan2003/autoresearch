"""Static contract guards for non-blocking AUTO_PROCEED checkpoints.

`/idea-discovery` is the surviving workflow that resolves `AUTO_PROCEED` once
and then chains nested sub-skills, so it carries the contract the retired
end-to-end orchestrator used to carry.
"""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IDEA_SKILLS = (
    REPO_ROOT / "skills" / "idea-discovery" / "SKILL.md",
    REPO_ROOT / "skills" / "skills-codex" / "idea-discovery" / "SKILL.md",
    REPO_ROOT
    / "skills"
    / "skills-codex-gemini-review"
    / "idea-discovery"
    / "SKILL.md",
)
AUTO_PROCEED_SKILLS = IDEA_SKILLS

TRUE_BRANCH = re.compile(
    r"\*\*(?:If|When) `AUTO_PROCEED=true` \(non-blocking\):\*\*"
    r"(?P<body>.*?)"
    r"(?=\*\*(?:If|When) `AUTO_PROCEED=false` \(blocking\):\*\*)",
    re.DOTALL,
)

# The mode is resolved exactly once, before Phase 0, and governs the whole
# chain — that is what makes the nested workflows inherit it.
MODE_RESOLUTION = re.compile(
    r"Resolve `AUTO_PROCEED` once from `\$ARGUMENTS` before Phase \d+ and keep"
    r"\s+that mode\s+for the entire workflow\."
)

# Every nested sub-skill invocation /idea-discovery emits, in phase order. The
# quoted-argument forms pin the actual invocation, not the pipeline diagram.
NESTED_INVOCATIONS = (
    '/research-lit "$ARGUMENTS"',
    '/idea-creator "$ARGUMENTS"',
    '/novelty-check "',
    '/research-review "',
    '/research-refine-pipeline "',
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_all_auto_proceed_variants_define_same_turn_checkpoint_semantics() -> None:
    for path in AUTO_PROCEED_SKILLS:
        text = read(path)
        assert "## Checkpoint execution rule" in text, path
        assert "`AUTO_PROCEED=true` is non-blocking" in text, path
        assert "continue executing in the **same turn**" in text, path
        assert "Do not ask for confirmation" in text, path
        assert "wait for silence" in text, path
        assert "or end the turn at a checkpoint" in text, path
        assert "`AUTO_PROCEED=false` is blocking" in text, path
        assert "Resume only after an explicit reply" in text, path
        assert "Feishu **interactive** gate" in text, path
        assert "intentional blocking exception" in text, path


def test_auto_proceed_branches_report_a_choice_without_asking() -> None:
    for path in IDEA_SKILLS:
        branches = [match.group("body") for match in TRUE_BRANCH.finditer(read(path))]
        assert len(branches) == 3, path
        for branch in branches:
            assert "AUTO_PROCEED:" in branch, path
            assert "?" not in branch, path
            assert "same turn" in branch, path


def test_silence_timeout_antipattern_is_absent() -> None:
    forbidden = (
        "wait 10 seconds",
        "(If no response, I'll proceed",
        "or no response + AUTO_PROCEED=true",
        "**pause and present the top ideas",
    )
    for path in AUTO_PROCEED_SKILLS:
        text = read(path)
        for phrase in forbidden:
            assert phrase not in text, f"{path}: stale AUTO_PROCEED instruction: {phrase}"


def test_idea_discovery_resolves_mode_once_before_nesting_workflows() -> None:
    for path in IDEA_SKILLS:
        text = read(path)
        resolutions = list(MODE_RESOLUTION.finditer(text))
        assert len(resolutions) == 1, (
            f"{path}: `AUTO_PROCEED` must be resolved exactly once, before the "
            "first phase, and govern the entire workflow"
        )
        resolution_at = resolutions[0].start()
        for invocation in NESTED_INVOCATIONS:
            at = text.find(invocation)
            assert at != -1, (path, invocation)
            assert at > resolution_at, (
                f"{path}: {invocation.strip()} is invoked before AUTO_PROCEED is "
                "resolved, so the nested workflow cannot inherit the resolved mode"
            )
        assert "$AUTO_PROCEED" not in text, (
            f"{path}: the unresolved `$AUTO_PROCEED` placeholder leaked into an "
            "invocation; pass the resolved mode instead"
        )


def test_user_docs_match_same_turn_auto_proceed_contract() -> None:
    docs = (
        REPO_ROOT / "README.md",
    )
    stale_phrases = (
        "if user doesn't respond",
        "用户不回复时自动",
        "Each phase presents results and waits for your feedback",
    )
    for path in docs:
        text = read(path)
        assert "same turn" in text or "同一轮" in text, path
        for phrase in stale_phrases:
            assert phrase not in text, f"{path}: stale AUTO_PROCEED wording: {phrase}"