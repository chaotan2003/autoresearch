"""Tests for install_aris_codex.sh (project-local symlink installer)."""

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / "tools" / "install_aris_codex.sh"


def run(
    cmd: list[str], *, cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        text=True,
        capture_output=True,
        check=check,
        env=env,
    )


def make_skill(path: Path, body: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(body)


def make_minimal_aris_repo(root: Path) -> Path:
    repo = root / "aris"
    make_skill(repo / "skills" / "skills-codex" / "alpha", "# alpha\n")
    make_skill(repo / "skills" / "skills-codex" / "beta", "# beta-base\n")
    (repo / "skills" / "skills-codex" / "shared-references").mkdir(parents=True, exist_ok=True)
    (repo / "skills" / "skills-codex" / "shared-references" / "reviewer-routing.md").write_text("base\n")
    make_skill(repo / "skills" / "skills-codex-claude-review" / "beta", "# beta-claude-overlay\n")
    make_skill(repo / "skills" / "skills-codex-gemini-review" / "beta", "# beta-gemini-overlay\n")
    return repo


def test_install_aris_codex_dry_run_has_no_project_writes(tmp_path: Path) -> None:
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    dry_run = run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(repo),
            "--dry-run",
        ]
    )

    assert "(dry-run) no changes made" in dry_run.stdout
    assert not (project / ".aris").exists()
    assert not (project / ".agents").exists()
    assert not (project / "AGENTS.md").exists()


def test_install_aris_codex_avoids_bash4_associative_arrays() -> None:
    text = INSTALL_SCRIPT.read_text()
    assert "declare -A" not in text


def test_goal_pulse_managed_doc_preserves_user_text_and_no_doc(tmp_path: Path) -> None:
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    agents = project / "AGENTS.md"
    user_text = "# My project\nKeep my instructions.\n"
    agents.write_text(user_text)
    command = ["bash", str(INSTALL_SCRIPT), str(project), "--aris-repo", str(repo), "--quiet"]

    run(command + ["--no-doc"])
    assert agents.read_text() == user_text
    run(command + ["--reconcile"])
    generated = agents.read_text()
    assert generated.startswith(user_text)
    assert "by default, without another confirmation" in generated
    assert "HERO-Anti-OverDefense/tree/main/skills/goal-pulse" in generated
    assert "`${CODEX_HOME:-~/.codex}/skills/goal-pulse/SKILL.md`" in generated
    run(command + ["--reconcile", "--no-doc"])
    assert agents.read_text() == generated
    assert sorted(path.name for path in (project / ".agents" / "skills").iterdir()) == [
        "alpha", "beta", "shared-references"
    ]


def test_install_aris_codex_reconcile_and_uninstall(tmp_path: Path) -> None:
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(repo),
            "--quiet",
        ]
    )

    manifest = project / ".aris" / "installed-skills-codex.txt"
    assert manifest.exists()
    assert (project / "AGENTS.md").exists()
    agents_text = (project / "AGENTS.md").read_text()
    assert "ARIS Codex Skill Scope" in agents_text
    assert f"ARIS repo root: `{repo}`" in agents_text
    assert "repo_root" in agents_text
    assert '$1=="repo_root"{print $2; exit}' in agents_text
    assert "$1==repo_root" not in agents_text
    assert (project / ".agents" / "skills" / "alpha").is_symlink()
    assert (project / ".agents" / "skills" / "beta").resolve() == (repo / "skills" / "skills-codex" / "beta")
    assert (project / ".agents" / "skills" / "shared-references").resolve() == (
        repo / "skills" / "skills-codex" / "shared-references"
    )

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(repo),
            "--reconcile",
            "--with-claude-review-overlay",
            "--quiet",
        ]
    )
    assert (project / ".agents" / "skills" / "beta").resolve() == (
        repo / "skills" / "skills-codex-claude-review" / "beta"
    )

    (repo / "skills" / "skills-codex" / "alpha").rename(repo / "skills" / "skills-codex" / "alpha-removed")
    make_skill(repo / "skills" / "skills-codex" / "gamma", "# gamma\n")
    # #366 selective install: a plain --quiet reconcile no longer silently adopts
    # new upstream skills (that would defeat the point of the new-skill
    # confirmation gate) -- it must be requested explicitly via --add-new.
    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(repo),
            "--reconcile",
            "--with-claude-review-overlay",
            "--add-new",
            "--quiet",
        ]
    )
    assert not (project / ".agents" / "skills" / "alpha").exists()
    assert (project / ".agents" / "skills" / "gamma").is_symlink()

    (project / ".agents" / "skills" / "local-only").mkdir(parents=True)
    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(repo),
            "--uninstall",
            "--quiet",
        ]
    )
    assert (project / ".agents" / "skills" / "local-only").exists()
    assert not (project / ".agents" / "skills" / "beta").exists()
    assert (project / ".aris" / "installed-skills-codex.txt.prev").exists()
    assert "ARIS Codex Skill Scope" not in (project / "AGENTS.md").read_text()


def test_install_aris_codex_uninstall_uses_manifest_repo_root(tmp_path: Path) -> None:
    original_repo = make_minimal_aris_repo(tmp_path / "original")
    other_repo = make_minimal_aris_repo(tmp_path / "other")
    project = tmp_path / "project"
    project.mkdir()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(original_repo),
            "--quiet",
        ]
    )

    alpha_link = project / ".agents" / "skills" / "alpha"
    assert alpha_link.is_symlink()
    assert alpha_link.resolve() == original_repo / "skills" / "skills-codex" / "alpha"

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(other_repo),
            "--uninstall",
            "--quiet",
        ]
    )

    assert not alpha_link.exists()
    assert not (project / ".agents" / "skills" / "beta").exists()
    assert not (project / ".agents" / "skills" / "shared-references").exists()
    assert not (project / ".aris" / "installed-skills-codex.txt").exists()
    assert (project / ".aris" / "installed-skills-codex.txt.prev").exists()


def test_install_aris_codex_reconcile_removes_stale_links_from_manifest_repo(tmp_path: Path) -> None:
    original_repo = make_minimal_aris_repo(tmp_path / "original")
    new_repo = make_minimal_aris_repo(tmp_path / "new")
    (new_repo / "skills" / "skills-codex" / "alpha").rename(
        new_repo / "skills" / "skills-codex" / "alpha-removed"
    )
    make_skill(new_repo / "skills" / "skills-codex" / "gamma", "# gamma\n")
    project = tmp_path / "project"
    project.mkdir()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(original_repo),
            "--quiet",
        ]
    )

    alpha_link = project / ".agents" / "skills" / "alpha"
    beta_link = project / ".agents" / "skills" / "beta"
    assert alpha_link.is_symlink()
    assert alpha_link.resolve() == original_repo / "skills" / "skills-codex" / "alpha"

    # #366 selective install: new upstream skills need --add-new (or an
    # interactive yes) on reconcile -- a plain --quiet reconcile only keeps
    # what was already installed and drops what upstream removed.
    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(new_repo),
            "--reconcile",
            "--add-new",
            "--quiet",
        ]
    )

    assert not alpha_link.exists()
    assert beta_link.resolve() == new_repo / "skills" / "skills-codex" / "beta"
    assert (project / ".agents" / "skills" / "gamma").resolve() == (
        new_repo / "skills" / "skills-codex" / "gamma"
    )
    manifest = (project / ".aris" / "installed-skills-codex.txt").read_text()
    assert "\talpha\t" not in manifest
    assert f"repo_root\t{new_repo}" in manifest


def test_install_aris_codex_reconcile_accepts_already_deleted_stale_link(tmp_path: Path) -> None:
    original_repo = make_minimal_aris_repo(tmp_path / "original")
    new_repo = make_minimal_aris_repo(tmp_path / "new")
    (new_repo / "skills" / "skills-codex" / "alpha").rename(
        new_repo / "skills" / "skills-codex" / "alpha-removed"
    )
    project = tmp_path / "project"
    project.mkdir()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(original_repo),
            "--quiet",
        ]
    )

    alpha_link = project / ".agents" / "skills" / "alpha"
    assert alpha_link.is_symlink()
    alpha_link.unlink()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(new_repo),
            "--reconcile",
            "--quiet",
        ]
    )

    manifest = (project / ".aris" / "installed-skills-codex.txt").read_text()
    assert "\talpha\t" not in manifest
