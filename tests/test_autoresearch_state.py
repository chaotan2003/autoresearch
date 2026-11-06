"""Behaviour of the autoresearch state machine (tools/autoresearch_state.py)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "tools" / "autoresearch_state.py"


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def state(root: Path, *args: str) -> dict:
    result = run(root, *args, "--json")
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def write(root: Path, name: str, body: str = "x") -> None:
    path = root / "research" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def fill_stage(root: Path) -> None:
    """Create the artifacts the current stage promises, then close it."""
    current = state(root, "status")
    for target in current["writes"]:
        write(root, Path(target).name)
    state(root, "done")


def walk_to_gate(root: Path, gate: str) -> None:
    """Close stages until the requested gate opens, approving earlier gates."""
    while True:
        current = state(root, "status")
        if current["status"] == "waiting_human":
            if current["gate"] == gate:
                return
            state(root, "gate", "approve", "--note", "walk")
            continue
        assert current["stage"] != "S8", "walked past the requested gate"
        state(root, "start")
        fill_stage(root)


def test_init_reports_first_stage_and_missing_artifacts(tmp_path: Path) -> None:
    result = state(tmp_path, "init", "--direction", "test-time scaling")
    assert result["stage"] == "S1"
    assert result["status"] == "pending"
    assert result["actor"] == "scout"
    assert result["writes"] == ["research/paper_search.md", "research/baseline_selection.md"]
    assert len(result["missing"]) == 2
    assert (tmp_path / ".autoresearch" / "state.json").exists()
    assert (tmp_path / ".autoresearch" / "traces").is_dir()


def test_done_refuses_missing_artifacts(tmp_path: Path) -> None:
    state(tmp_path, "init", "--direction", "t")
    state(tmp_path, "start")
    write(tmp_path, "paper_search.md")
    result = run(tmp_path, "done")
    assert result.returncode == 1
    assert "baseline_selection.md" in result.stderr
    assert state(tmp_path, "status")["stage"] == "S1"


def test_full_run_advances_through_both_gates(tmp_path: Path) -> None:
    state(tmp_path, "init", "--direction", "t")

    walk_to_gate(tmp_path, "A")
    assert state(tmp_path, "next")["status"] == "waiting_human"
    state(tmp_path, "gate", "approve", "--note", "method ok")
    assert state(tmp_path, "status")["stage"] == "S5"

    walk_to_gate(tmp_path, "B")
    frozen = state(tmp_path, "status")["contract"]
    assert frozen["version"] == 1
    assert len(frozen["sha256"]) == 64
    state(tmp_path, "gate", "approve", "--note", "contract ok")

    assert state(tmp_path, "status")["stage"] == "S7"
    state(tmp_path, "start")
    fill_stage(tmp_path)
    state(tmp_path, "start")
    fill_stage(tmp_path)

    final = state(tmp_path, "status")
    assert final["status"] == "finished"
    assert final["stage"] == "S8"
    gates = (tmp_path / ".autoresearch" / "gates.jsonl").read_text().splitlines()
    events = [json.loads(line)["event"] for line in gates]
    assert events == ["awaiting_human", "approve", "awaiting_human", "approve"]


def test_rejected_gate_sends_work_back_without_skipping(tmp_path: Path) -> None:
    state(tmp_path, "init", "--direction", "t")
    walk_to_gate(tmp_path, "A")
    state(tmp_path, "gate", "reject", "--note", "novelty too weak")
    current = state(tmp_path, "status")
    assert current["stage"] == "S4"
    assert current["status"] == "pending"
    last = json.loads((tmp_path / ".autoresearch" / "gates.jsonl").read_text().splitlines()[-1])
    assert last["event"] == "reject"
    assert last["note"] == "novelty too weak"


def test_frozen_contract_cannot_change_silently(tmp_path: Path) -> None:
    state(tmp_path, "init", "--direction", "t")
    walk_to_gate(tmp_path, "B")
    first = state(tmp_path, "status")["contract"]["sha256"]

    state(tmp_path, "reopen", "--stage", "S6", "--note", "contract v2")
    write(tmp_path, "research_contract_v1.md", "different contract")
    state(tmp_path, "start")
    refused = run(tmp_path, "done")
    assert refused.returncode == 1
    assert "immutable" in refused.stderr
    assert state(tmp_path, "status")["contract"]["sha256"] == first

    state(tmp_path, "start")
    bumped = state(tmp_path, "done", "--contract-version", "2")
    assert bumped["status"] == "waiting_human"
    assert bumped["contract"]["version"] == 2
    assert bumped["contract"]["sha256"] != first


def test_reopen_moves_back_and_keeps_the_trail(tmp_path: Path) -> None:
    state(tmp_path, "init", "--direction", "t")
    state(tmp_path, "start")
    fill_stage(tmp_path)
    state(tmp_path, "start")
    fill_stage(tmp_path)

    current = state(tmp_path, "status")
    assert current["stage"] == "S3"
    moved = state(tmp_path, "reopen", "--stage", "S1", "--note", "papers were wrong")
    assert moved["stage"] == "S1"
    assert moved["status"] == "pending"
    history = state(tmp_path, "status")["history_tail"]
    assert any(entry["event"] == "reopen" for entry in history)


def test_start_is_refused_while_a_gate_is_open(tmp_path: Path) -> None:
    state(tmp_path, "init", "--direction", "t")
    walk_to_gate(tmp_path, "A")
    refused = run(tmp_path, "start")
    assert refused.returncode == 1
    assert "gate" in refused.stderr.lower()