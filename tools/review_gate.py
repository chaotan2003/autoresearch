#!/usr/bin/env python3
"""Deterministic state transitions for /auto-review-loop reviewer backends.

The skill remains the orchestrator.  This helper owns only the stop/continue/
escalate decision so that the safety-critical transition table is executable
and testable instead of existing solely as prose in SKILL.md.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
from dataclasses import asdict, dataclass


TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

KNOWN_FAMILIES = {
    "openai", "anthropic", "google", "deepseek", "moonshot", "qwen",
    "zhipu", "minimax", "xiaomi", "bytedance", "xai", "meta", "mistral",
}
POSITIVE_VERDICTS = {"ready", "almost"}
REPORTED_MODEL_BACKENDS = {"antigravity", "grok", "claude-code"}
SUCCESSFUL_REVIEW_STATUSES = {"ok", "fallback_used", "success", "completed"}
VALID_BACKENDS = {"codex", "manual", "oracle-pro", "agy", "llm-chat"} | REPORTED_MODEL_BACKENDS
VALID_VERDICTS = POSITIVE_VERDICTS | {"not ready"}


@dataclass(frozen=True)
class Transition:
    decision: str
    next_backend: str | None
    requires_external_acquittal: bool
    identity_assurance: str
    reason: str
    review_independence: str = "unknown"
    acceptance_status: str = "provisional"


def _normalized(value: str) -> str:
    return value.strip().lower()


def derive_model_family(model: str) -> str:
    name = _normalized(model)
    families: set[str] = set()
    if re.search(r"(^|[^a-z0-9])(gpt|chatgpt|codex|oracle|o1|o3|o4)([^a-z0-9]|$)", name):
        families.add("openai")
    if re.search(r"(^|[^a-z0-9])(claude|sonnet|opus|haiku|anthropic)([^a-z0-9]|$)", name):
        families.add("anthropic")
    if re.search(r"(^|[^a-z0-9])(gemini|google)([^a-z0-9]|$)", name):
        families.add("google")
    # [0-9.]* so versioned names (qwen3-max, qwen2.5-72b) still match.
    if re.search(r"(^|[^a-z0-9])(deepseek)[0-9.]*([^a-z0-9]|$)", name):
        families.add("deepseek")
    if re.search(r"(^|[^a-z0-9])(kimi|moonshot)[0-9.]*([^a-z0-9]|$)", name):
        families.add("moonshot")
    if re.search(r"(^|[^a-z0-9])(qwen|tongyi)[0-9.]*([^a-z0-9]|$)", name):
        families.add("qwen")
    if re.search(r"(^|[^a-z0-9])(glm|zhipu)[0-9.]*([^a-z0-9]|$)", name):
        families.add("zhipu")
    if re.search(r"(^|[^a-z0-9])(minimax|abab)[0-9.]*([^a-z0-9]|$)", name):
        families.add("minimax")
    if re.search(r"(^|[^a-z0-9])(mimo|xiaomi)[0-9.]*([^a-z0-9]|$)", name):
        families.add("xiaomi")
    if re.search(r"(^|[^a-z0-9])(doubao|bytedance|volcengine)[0-9.]*([^a-z0-9]|$)", name):
        families.add("bytedance")
    if re.search(r"(^|[^a-z0-9])(grok)[0-9.]*([^a-z0-9]|$)", name):
        families.add("xai")
    if re.search(r"(^|[^a-z0-9])(llama)[0-9.]*([^a-z0-9]|$)", name):
        families.add("meta")
    if re.search(r"(^|[^a-z0-9])(mistral|mixtral)[0-9.]*([^a-z0-9]|$)", name):
        families.add("mistral")
    return next(iter(families)) if len(families) == 1 else "unknown"


def evaluate_transition(
    *,
    round_backend: str,
    score: float,
    verdict: str,
    requires_external_acquittal: bool = False,
    executor_model: str = "",
    reviewer_model: str = "",
    codex_available: bool = False,
    manual_available: bool = False,
    manual_identity_reported: bool = False,
    review_completed: bool = False,
    review_scope_complete: bool = False,
    review_status: str = "",
) -> Transition:
    """Return the authoritative transition for one completed review round.

    ``executor_model`` is caller-declared in the drive/finalizer integration.
    It is useful for fail-closed route selection, but the resulting family
    relation is not independent identity attestation. Family strings are never
    accepted as inputs; this helper derives them from the model identities
    itself.
    For antigravity, grok and claude-code, ``reviewer_model`` must be the
    actual model reported by the backend, never its requested model or route
    name. Completion and scope flags describe this review round only.
    """

    backend = _normalized(round_backend)
    normalized_verdict = _normalized(verdict)
    executor = derive_model_family(executor_model)
    reviewer = derive_model_family(reviewer_model)

    if backend not in VALID_BACKENDS:
        return Transition(
            "review_unavailable",
            None,
            requires_external_acquittal,
            "unverified",
            f"unknown reviewer backend: {round_backend}",
        )
    if normalized_verdict not in VALID_VERDICTS:
        return Transition(
            "review_unavailable",
            None,
            requires_external_acquittal,
            "unverified",
            f"unknown verdict: {verdict}",
        )
    if not math.isfinite(score) or not 1 <= score <= 10:
        return Transition(
            "review_unavailable",
            None,
            requires_external_acquittal,
            "unverified",
            f"score must be finite and within 1..10: {score}",
        )
    positive = score >= 6 and normalized_verdict in POSITIVE_VERDICTS

    if backend in REPORTED_MODEL_BACKENDS:
        independence = (
            "unknown"
            if executor not in KNOWN_FAMILIES or reviewer not in KNOWN_FAMILIES
            else "same-family" if executor == reviewer else "cross-family"
        )
        if requires_external_acquittal:
            return Transition(
                "review_unavailable", None, True, "unverified",
                "external-acquittal state permits only codex or manual",
                independence,
            )
        if (
            _normalized(review_status) not in SUCCESSFUL_REVIEW_STATUSES
            or not review_completed
            or not review_scope_complete
        ):
            return Transition(
                "review_unavailable", None, False, "unverified",
                "review did not complete successfully within its required scope",
                independence,
            )
        if independence == "unknown":
            return Transition(
                "review_unavailable", None, False, "unverified",
                "reported reviewer or executor model family cannot be derived",
                independence,
            )
        if not positive:
            return Transition(
                "continue", backend, False, "caller_declared",
                "completed reviewer did not meet the positive threshold",
                independence,
            )
        return Transition(
            "stop", None, False, "caller_declared",
            "completed reviewer returned a positive verdict within its required scope",
            independence,
            "accepted" if independence == "cross-family" else "provisional",
        )

    if not positive:
        return Transition(
            "continue",
            backend,
            requires_external_acquittal,
            "unverified",
            "positive threshold not met",
        )

    if backend == "llm-chat":
        if requires_external_acquittal:
            return Transition(
                "review_unavailable",
                None,
                True,
                "unverified",
                "external-acquittal state permits only codex or manual",
            )
        if executor not in KNOWN_FAMILIES or reviewer not in KNOWN_FAMILIES:
            return Transition(
                "review_unavailable",
                None,
                False,
                "unverified",
                "HTTP reviewer family relation cannot be derived",
            )
        if executor == reviewer:
            return Transition(
                "review_unavailable",
                None,
                False,
                "failed",
                "HTTP reviewer is same-family as the declared executor model",
            )
        return Transition(
            "stop",
            None,
            False,
            "caller_declared",
            "HTTP reviewer returned a positive cross-family verdict; executor identity remains caller-declared",
        )

    if backend in {"codex", "oracle-pro", "agy"} and not requires_external_acquittal:
        return Transition(
            "stop",
            None,
            False,
            "not_required",
            "non-finalizer backend preserves the pre-finalizer positive-stop contract",
        )

    if backend in {"oracle-pro", "agy"} and requires_external_acquittal:
        return Transition(
            "review_unavailable",
            None,
            True,
            "unverified",
            "external-acquittal state permits only codex or manual",
        )

    if backend == "manual" and not manual_identity_reported:
        return Transition(
            "review_unavailable",
            None,
            requires_external_acquittal,
            "unverified",
            "manual final verdict is missing its required reported model identity",
        )

    if backend == "manual":
        if executor not in KNOWN_FAMILIES or reviewer not in KNOWN_FAMILIES:
            return Transition(
                "review_unavailable",
                None,
                requires_external_acquittal,
                "unverified",
                "manual verdict family relation cannot be derived",
            )
        if executor == reviewer:
            return Transition(
                "review_unavailable",
                None,
                requires_external_acquittal,
                "failed",
                "manual reviewer is same-family as the declared executor model",
            )

    if requires_external_acquittal:
        if executor not in KNOWN_FAMILIES or reviewer not in KNOWN_FAMILIES:
            return Transition(
                "review_unavailable",
                None,
                True,
                "unverified",
                "finalizer family relation cannot be derived",
            )
        if executor == reviewer:
            return Transition(
                "review_unavailable",
                None,
                True,
                "failed",
                "finalizer is same-family as the declared executor model",
            )
        return Transition(
            "stop",
            None,
            False,
            "caller_declared",
            "policy-approved finalizer returned a positive verdict; executor identity remains caller-declared",
        )

    return Transition(
        "stop",
        None,
        False,
        "caller_declared",
        "explicit manual backend returned a positive verdict with its required model identity",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round-backend", required=True, choices=sorted(VALID_BACKENDS))
    parser.add_argument("--score", required=True, type=float)
    parser.add_argument("--verdict", required=True, choices=sorted(VALID_VERDICTS))
    parser.add_argument("--requires-external-acquittal", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--executor-model", default="")
    parser.add_argument("--reviewer-model", default="")
    parser.add_argument("--codex-available", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--manual-available", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--manual-identity-reported", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--review-completed", action="store_true")
    parser.add_argument("--review-scope-complete", action="store_true")
    parser.add_argument("--review-status", default="")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    transition = evaluate_transition(
        round_backend=args.round_backend,
        score=args.score,
        verdict=args.verdict,
        requires_external_acquittal=args.requires_external_acquittal,
        executor_model=args.executor_model,
        reviewer_model=args.reviewer_model,
        codex_available=args.codex_available,
        manual_available=args.manual_available,
        manual_identity_reported=args.manual_identity_reported,
        review_completed=args.review_completed,
        review_scope_complete=args.review_scope_complete,
        review_status=args.review_status,
    )
    print(json.dumps(asdict(transition), sort_keys=True))


if __name__ == "__main__":
    main()
