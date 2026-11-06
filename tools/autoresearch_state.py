#!/usr/bin/env python3
"""ARIS autoresearch state machine.

The orchestrator never decides the next step from memory: it asks this file.
Every stage transition is a command, every artifact is checked on disk, and
human gates are appended to ``gates.jsonl`` so the decision trail survives.

    python3 tools/autoresearch_state.py init --direction "one-line topic"
    python3 tools/autoresearch_state.py next
    python3 tools/autoresearch_state.py start
    python3 tools/autoresearch_state.py done --artifacts research/paper_search.md
    python3 tools/autoresearch_state.py gate approve --note "method ok"
    python3 tools/autoresearch_state.py reopen --stage S4 --note "contract v2"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = 1
STATE_DIR = Path(".autoresearch")
STATE_FILE = STATE_DIR / "state.json"
GATES_FILE = STATE_DIR / "gates.jsonl"
TRACES_DIR = STATE_DIR / "traces"

# stage id -> (actor, reads, writes, gate after this stage)
# ``writes`` are relative to the research root so the tool and the skills agree.
STAGES: dict[str, dict[str, Any]] = {
    "S1": {
        "name": "找文献 + 选 baseline",
        "actor": "scout",
        "reads": [],
        "writes": ["paper_search.md", "baseline_selection.md"],
        "gate": None,
    },
    "S2": {
        "name": "提 10 个 idea",
        "actor": "worker",
        "reads": ["paper_search.md", "baseline_selection.md"],
        "writes": ["ideas.md", "idea_cards.md"],
        "gate": None,
    },
    "S3": {
        "name": "idea 打分排序",
        "actor": "codex",
        "reads": ["idea_cards.md"],
        "writes": ["idea_ranking.md"],
        "gate": None,
    },
    "S4": {
        "name": "查新 + 方法提案",
        "actor": "scout",
        "reads": ["idea_ranking.md", "paper_search.md"],
        "writes": ["method_proposal.md"],
        "gate": "A",
    },
    "S5": {
        "name": "复现 baseline",
        "actor": "dsh",
        "reads": ["paper_search.md", "method_proposal.md"],
        "writes": ["baseline_report.md"],
        "gate": None,
    },
    "S6": {
        "name": "写研究合同",
        "actor": "dsh",
        "reads": ["baseline_report.md", "method_proposal.md"],
        "writes": ["research_contract_v1.md"],
        "gate": "B",
    },
    "S7": {
        "name": "实现方法",
        "actor": "codex",
        "reads": ["research_contract_v1.md"],
        "writes": ["implementation_report.md"],
        "gate": None,
    },
    "S8": {
        "name": "跑实验 + 分析",
        "actor": "dsh",
        "reads": ["research_contract_v1.md"],
        "writes": ["experiment_analysis.md", "research_decision.md"],
        "gate": None,
    },
}
ORDER = list(STAGES)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fail(message: str) -> "NoReturn":  # type: ignore[name-defined]
    print(json.dumps({"ok": False, "error": message}), file=sys.stderr)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> dict[str, Any]:
    if not STATE_FILE.exists():
        fail("no state: run `init` first")
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now()
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", "utf-8")


def append_gate(record: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with GATES_FILE.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    if not payload.get("ok", True):
        print("ERROR " + payload.get("error", ""), file=sys.stderr)
        return
    for key in ("stage", "stage_name", "status", "actor", "next_action"):
        if key in payload:
            print(f"{key}: {payload[key]}")
    for key in ("reads", "writes", "missing"):
        if payload.get(key):
            print(f"{key}:")
            for item in payload[key]:
                print(f"  - {item}")
    if "note" in payload:
        print("note: " + payload["note"])


def stage_paths(stage_id: str, root: Path) -> tuple[list[Path], list[Path]]:
    spec = STAGES[stage_id]
    return (
        [root / name for name in spec["reads"]],
        [root / name for name in spec["writes"]],
    )


def require_stage(stage: str) -> None:
    if stage not in STAGES:
        fail(f"unknown stage {stage!r}; expected one of {', '.join(ORDER)}")


# ---------------------------------------------------------------- commands


def cmd_init(args: argparse.Namespace) -> dict[str, Any]:
    if STATE_FILE.exists() and not args.force:
        fail("state already exists; use --force to overwrite")
    for directory in (STATE_DIR, TRACES_DIR, Path(args.root)):
        directory.mkdir(parents=True, exist_ok=True)
    state = {
        "schema": SCHEMA,
        "direction": args.direction,
        "root": args.root,
        "stage": args.stage,
        "status": "pending",
        "contract": {"version": 1, "sha256": None, "frozen_at": None},
        "artifacts": {},
        "history": [{"at": now(), "event": "init", "stage": args.stage}],
        "created_at": now(),
    }
    save(state)
    return {"ok": True, **describe(state)}


def describe(state: dict[str, Any]) -> dict[str, Any]:
    root = Path(state["root"])
    stage = state["stage"]
    spec = STAGES[stage]
    reads, writes = stage_paths(stage, root)
    return {
        "ok": True,
        "stage": stage,
        "stage_name": spec["name"],
        "status": state["status"],
        "actor": spec["actor"],
        "gate": spec["gate"],
        "reads": [str(p) for p in reads],
        "writes": [str(p) for p in writes],
        "missing": [str(p) for p in writes if not p.exists()],
        "contract": state.get("contract", {}),
    }


def cmd_next(args: argparse.Namespace) -> dict[str, Any]:
    state = load()
    payload = describe(state)
    status = state["status"]
    if status == "waiting_human":
        payload["next_action"] = (
            f"gate {STAGES[state['stage']]['gate']} needs a human: "
            "`gate approve --note ...` or `reopen --stage <S#> --note ...`"
        )
    elif status == "finished":
        payload["next_action"] = "run finished; start a new round with `init --force`"
    elif status == "running":
        payload["next_action"] = (
            f"stage {state['stage']} is running: finish it with "
            f"`done --artifacts {' '.join(payload['writes'])}`"
        )
    else:
        payload["next_action"] = f"`start` stage {state['stage']} ({STAGES[state['stage']]['name']})"
    payload["direction"] = state.get("direction", "")
    return payload


def cmd_start(args: argparse.Namespace) -> dict[str, Any]:
    state = load()
    if state["status"] == "waiting_human":
        fail("a human gate is open; approve or reopen before starting work")
    if state["status"] == "finished":
        fail("run is finished; use `init --force` to start a new round")
    state["status"] = "running"
    state["history"].append({"at": now(), "event": "start", "stage": state["stage"]})
    save(state)
    return {**describe(state), "next_action": "do the work, then call `done`"}


def cmd_done(args: argparse.Namespace) -> dict[str, Any]:
    state = load()
    stage = state["stage"]
    spec = STAGES[stage]
    root = Path(state["root"])
    _, expected = stage_paths(stage, root)

    declared = [Path(item) for item in args.artifacts] if args.artifacts else expected
    missing = [str(p) for p in declared if not p.exists()]
    if missing:
        fail("declared artifacts are missing: " + ", ".join(missing))
    undeclared = [str(p) for p in expected if not p.exists()]
    if undeclared:
        fail(
            "stage contract is not met, still missing: "
            + ", ".join(undeclared)
            + " (pass --artifacts only for extra files)"
        )

    state["artifacts"][stage] = [str(p) for p in declared]
    state["history"].append(
        {"at": now(), "event": "done", "stage": stage, "artifacts": [str(p) for p in declared], "note": args.note}
    )

    if stage == "S6":
        contract = root / "research_contract_v1.md"
        digest = sha256(contract)
        previous = state["contract"].get("sha256")
        if previous and previous != digest and not args.contract_version:
            fail(
                "contract already frozen with a different sha256; a frozen contract is "
                "immutable — bump it with `--contract-version 2` and write the new file"
            )
        state["contract"] = {
            "version": args.contract_version or state["contract"].get("version", 1),
            "sha256": digest,
            "frozen_at": now(),
        }

    if spec["gate"]:
        state["status"] = "waiting_human"
        append_gate(
            {
                "at": now(),
                "gate": spec["gate"],
                "stage": stage,
                "event": "awaiting_human",
                "contract_sha256": state["contract"]["sha256"],
            }
        )
    elif stage == "S8":
        state["status"] = "finished"
    else:
        state["status"] = "pending"
        state["stage"] = ORDER[ORDER.index(stage) + 1]
    save(state)
    return {**describe(state), "next_action": cmd_next(argparse.Namespace())["next_action"]}


def cmd_gate(args: argparse.Namespace) -> dict[str, Any]:
    state = load()
    stage = state["stage"]
    spec = STAGES[stage]
    if state["status"] != "waiting_human" or not spec["gate"]:
        fail(f"no gate is open at stage {stage}")
    if args.decision == "approve":
        state["status"] = "pending"
        state["stage"] = ORDER[ORDER.index(stage) + 1]
    else:
        # A rejected gate sends the work back, it never skips ahead.
        state["status"] = "pending"
        if spec["gate"] == "B":
            state["stage"] = "S4"
        else:
            state["stage"] = stage
    append_gate(
        {
            "at": now(),
            "gate": spec["gate"],
            "stage": stage,
            "event": args.decision,
            "note": args.note,
            "contract_sha256": state["contract"]["sha256"],
        }
    )
    state["history"].append(
        {"at": now(), "event": "gate_" + args.decision, "stage": stage, "note": args.note}
    )
    save(state)
    return {**describe(state), "note": args.note or ""}


def cmd_reopen(args: argparse.Namespace) -> dict[str, Any]:
    state = load()
    require_stage(args.stage)
    append_gate(
        {
            "at": now(),
            "gate": STAGES[state["stage"]]["gate"],
            "stage": state["stage"],
            "event": "reopen",
            "reopen_to": args.stage,
            "note": args.note,
            "contract_sha256": state["contract"]["sha256"],
        }
    )
    state["history"].append(
        {"at": now(), "event": "reopen", "from": state["stage"], "to": args.stage, "note": args.note}
    )
    state["stage"] = args.stage
    state["status"] = "pending"
    save(state)
    return {**describe(state), "note": args.note or ""}


def cmd_fail(args: argparse.Namespace) -> dict[str, Any]:
    state = load()
    state["status"] = "failed"
    state["history"].append(
        {"at": now(), "event": "failed", "stage": state["stage"], "reason": args.reason}
    )
    save(state)
    return {**describe(state), "note": args.reason}


def cmd_status(args: argparse.Namespace) -> dict[str, Any]:
    state = load()
    payload = describe(state)
    payload["direction"] = state.get("direction", "")
    payload["contract"] = state.get("contract", {})
    payload["artifacts"] = state.get("artifacts", {})
    payload["history_tail"] = state.get("history", [])[-5:]
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # Accepted before or after the subcommand. The subcommand copy uses SUPPRESS
    # so it never resets a value already parsed at the top level.
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create .autoresearch/state.json", parents=[common])
    p.add_argument("--direction", required=True, help="one-line research direction")
    p.add_argument("--stage", default="S1")
    p.add_argument("--root", default="research")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("next", help="what to do now", parents=[common])
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("start", help="mark the current stage running", parents=[common])
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("done", help="close the current stage after checking artifacts", parents=[common])
    p.add_argument("--artifacts", nargs="*", default=[])
    p.add_argument("--note", default="")
    p.add_argument("--contract-version", type=int, default=0)
    p.set_defaults(func=cmd_done)

    p = sub.add_parser("gate", help="record a human gate decision", parents=[common])
    p.add_argument("decision", choices=["approve", "reject"])
    p.add_argument("--note", default="")
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("reopen", help="send the run back to an earlier stage", parents=[common])
    p.add_argument("--stage", required=True)
    p.add_argument("--note", default="")
    p.set_defaults(func=cmd_reopen)

    p = sub.add_parser("fail", help="mark the current stage failed", parents=[common])
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_fail)

    p = sub.add_parser("status", help="full state", parents=[common])
    p.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    try:
        payload = args.func(args)
    except SystemExit:
        return 1
    emit(payload, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())