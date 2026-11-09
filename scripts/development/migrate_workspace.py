from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


SOURCE = Path(r"C:\Users\tonge\Desktop\Zemax_MCP")
TARGET = Path(r"C:\Users\tonge\Desktop\mcp")
BASE_PYTHON = Path(r"C:\Users\tonge\Zemax_MCP_Runtime\.venv\Scripts\python.exe")
WORKTREE_ROOT = Path(r"C:\Users\tonge\.codex\worktrees")
EXPECTED_WORKTREES = 5
RESUME_MARKER = ".migration-in-progress"
TARGET_GIT_VALID = False


def run(args: list[str], *, cwd: Path | None = None) -> None:
    print("+", subprocess.list2cmdline([str(arg) for arg in args]), flush=True)
    subprocess.run([str(arg) for arg in args], cwd=cwd, check=True)


def ignore_rebuildable(_directory: str, names: list[str]) -> set[str]:
    ignored = {".venv", ".pytest_cache", "build", "pytest-of-tonge", "__pycache__"}
    ignored.update(name for name in names if name.endswith(".pyc"))
    if TARGET_GIT_VALID and Path(_directory).resolve() == SOURCE.resolve():
        ignored.add(".git")
    return ignored.intersection(names)


def list_worktree_pointers() -> list[Path]:
    pointers = sorted(WORKTREE_ROOT.glob("*/Zemax_MCP/.git"))
    if len(pointers) != EXPECTED_WORKTREES:
        raise RuntimeError(f"Expected {EXPECTED_WORKTREES} DSH checkouts; found {len(pointers)}")
    return pointers


def main() -> None:
    global TARGET_GIT_VALID
    if os.path.normcase(str(SOURCE)) != os.path.normcase(r"C:\Users\tonge\Desktop\Zemax_MCP"):
        raise RuntimeError("Source path guard failed")
    if os.path.normcase(str(TARGET)) != os.path.normcase(r"C:\Users\tonge\Desktop\mcp"):
        raise RuntimeError("Target path guard failed")
    if SOURCE == TARGET or not SOURCE.is_dir() or not TARGET.is_dir():
        raise RuntimeError("Expected source and target directories to exist and differ")
    if not BASE_PYTHON.is_file():
        raise RuntimeError(f"Python runtime not found: {BASE_PYTHON}")

    marker = TARGET / RESUME_MARKER
    target_items = list(TARGET.iterdir())
    if target_items and not marker.is_file():
        raise RuntimeError("Target must be empty or contain this migration's resume marker")
    if not (SOURCE / ".git").is_dir():
        raise RuntimeError("Source Git metadata is missing")
    worktree_entries = list((SOURCE / ".git" / "worktrees").glob("*"))
    if len(worktree_entries) != EXPECTED_WORKTREES:
        raise RuntimeError(f"Expected {EXPECTED_WORKTREES} Git worktree records; found {len(worktree_entries)}")
    pointers = list_worktree_pointers()

    if not marker.exists():
        marker.write_text("Migration in progress", encoding="ascii")

    if (TARGET / ".git" / "config").is_file():
        try:
            subprocess.run(
                ["git", "-C", str(TARGET), "rev-parse", "--verify", "HEAD"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            TARGET_GIT_VALID = True
            print("Existing target Git metadata is readable; preserving read-only object files.", flush=True)
        except subprocess.CalledProcessError:
            TARGET_GIT_VALID = False

    print(f"Copying project, user data, evidence, and Git metadata: {SOURCE} -> {TARGET}", flush=True)
    shutil.copytree(
        SOURCE,
        TARGET,
        dirs_exist_ok=True,
        ignore=ignore_rebuildable,
        copy_function=shutil.copy2,
    )
    for relative in (
        Path("src/zemax_mcp"),
        Path("development/ledgers"),
        Path("tests"),
        Path("requirements/all.lock.txt"),
        Path(".git/config"),
    ):
        if not (TARGET / relative).exists():
            raise RuntimeError(f"Copied project is missing {relative}")
    script_target = TARGET / "scripts" / "development" / "migrate_workspace.py"
    script_target.parent.mkdir(parents=True, exist_ok=True)
    if Path(__file__).resolve() != script_target.resolve():
        shutil.copy2(Path(__file__), script_target)

    run([BASE_PYTHON, "--version"])
    run([BASE_PYTHON, "-m", "venv", TARGET / ".venv"])
    project_python = TARGET / ".venv" / "Scripts" / "python.exe"
    run([project_python, "-m", "pip", "install", "-r", TARGET / "requirements" / "all.lock.txt"])
    run([project_python, "-m", "pip", "install", "--no-deps", "-e", TARGET])

    temp_root = TARGET / ".local" / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    run(
        [
            project_python,
            "-m",
            "pytest",
            "-q",
            TARGET / "tests" / "unit",
            f"--basetemp={temp_root / 'pytest'}",
        ],
        cwd=TARGET,
    )
    run([project_python, TARGET / "scripts" / "development" / "native_startup_check.py"], cwd=TARGET)
    startup_module = TARGET / "scripts" / "development" / "native_startup_check.py"
    namespace = {"__file__": str(startup_module), "__name__": "_migration_context"}
    exec(compile(startup_module.read_text(encoding="utf-8"), str(startup_module), "exec"), namespace)
    context = namespace["process_context"]()
    if context["elevated"] or context["integrity_rid"] != 8192:
        evidence_root = TARGET / ".local" / "evidence" / "development" / "BASE-04"
        passed = False
        for result_file in sorted(evidence_root.glob("stdio-recovery-*/result.json"), reverse=True):
            try:
                if __import__("json").loads(result_file.read_text(encoding="utf-8")).get("state") == "passed":
                    passed = True
                    print(f"Using successful medium-context stdio evidence: {result_file.parent}", flush=True)
                    break
            except (OSError, ValueError):
                continue
        if not passed:
            raise RuntimeError("Run native_stdio_check.py from a non-elevated medium-integrity PowerShell before finalizing in an elevated shell.")
    else:
        run([project_python, TARGET / "scripts" / "development" / "native_stdio_check.py"], cwd=TARGET)

    new_head = subprocess.check_output(
        ["git", "-C", str(TARGET), "rev-parse", "HEAD"], text=True
    ).strip()
    run(["git", "-C", TARGET, "worktree", "list", "--porcelain"])

    old_prefix = (str(SOURCE).replace("\\", "/") + "/.git/").encode("utf-8")
    new_prefix = (str(TARGET).replace("\\", "/") + "/.git/").encode("utf-8")
    backups: dict[Path, bytes] = {}
    try:
        for pointer in pointers:
            original = pointer.read_bytes()
            if new_prefix in original:
                continue
            if old_prefix not in original:
                raise RuntimeError(f"Unexpected worktree pointer: {pointer}")
            backups[pointer] = original
            pointer.write_bytes(original.replace(old_prefix, new_prefix))

        run(["git", "-C", TARGET, "worktree", "list", "--porcelain"])
        for pointer in pointers:
            checkout = pointer.parent
            run(["git", "-C", checkout, "status", "--short", "--branch"])
    except Exception:
        for pointer, content in backups.items():
            pointer.write_bytes(content)
        raise

    if SOURCE.resolve() != Path(r"C:\Users\tonge\Desktop\Zemax_MCP").resolve():
        raise RuntimeError("Source deletion guard failed")
    shutil.rmtree(SOURCE)
    if SOURCE.exists():
        raise RuntimeError("Old project directory remains")
    marker.unlink(missing_ok=True)

    print(f"Migration completed: {TARGET}", flush=True)
    print(f"Git HEAD: {new_head}", flush=True)
    print("Environment, unit tests, Standalone startup, stdio, and shared worktrees passed.", flush=True)


if __name__ == "__main__":
    main()
