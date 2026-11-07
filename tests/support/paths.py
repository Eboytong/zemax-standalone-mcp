"""
MCP Test Support - Path Management

Centralized path management for test outputs and fixtures.
Replaces direct PROJECT_ROOT/"outputs" usage to enable lifecycle management.

Usage:
    from tests.support import paths

    # For temporary test runs (14 days retention)
    run_dir = paths.run_dir("analyses")

    # For fixtures (permanent, must register in fixtures.json)
    fixture_dir = paths.fixture_dir("finite_comp", role="fixture")

    # Find existing outputs (searches legacy + new locations)
    found = paths.find_outputs("finite_comp_*")
"""

import os
from pathlib import Path
from typing import Optional, List
import secrets


PROJECT_ROOT = Path(__file__).parents[2]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# Legacy mode: set ZEMAX_TEST_OUTPUT_LEGACY=1 to use old behavior
LEGACY_MODE = os.environ.get('ZEMAX_TEST_OUTPUT_LEGACY', '0') == '1'


def run_dir(kind: str, role: str = "run") -> Path:
    """
    Get directory for test run output (14 days retention).

    Args:
        kind: Test kind (e.g., "analyses", "tolerance")
        role: "run" (default) or "fixture" (permanent)

    Returns:
        Path to output directory in outputs/runs/ or outputs/fixtures/
    """
    if LEGACY_MODE:
        # Legacy behavior: write to outputs/ root
        hex_id = secrets.token_hex(5)
        dir_path = OUTPUTS_DIR / f"{kind}_{hex_id}"
    else:
        # New behavior: separate by role
        hex_id = secrets.token_hex(5)
        if role == "fixture":
            dir_path = OUTPUTS_DIR / "fixtures" / f"{kind}_{hex_id}"
        else:
            dir_path = OUTPUTS_DIR / "runs" / f"{kind}_{hex_id}"

    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def fixture_dir(kind: str, role: str = "fixture") -> Path:
    """
    Get directory for fixture output (permanent).
    Must be registered in tests/fixtures.json.

    Args:
        kind: Fixture kind
        role: Should always be "fixture"

    Returns:
        Path to fixture directory in outputs/fixtures/
    """
    return run_dir(kind, role="fixture")


def output(name: str) -> Path:
    """
    Path of a named acceptance/fixture batch under outputs/ (legacy layout).

    Used for read-only references to recorded evidence. New run output must go
    through run_dir()/fixture_dir() instead.
    """
    return OUTPUTS_DIR / name


def evidence_root(path: Path) -> Optional[Path]:
    """
    Re-root a recorded evidence path onto the current outputs/ directory.

    ``saved-cross-reference.json`` records absolute source paths such as
    ``...\\outputs\\finite_imaging_F2_W0_5a95bab011\\<session>\\<task>.json``.
    The scan unit is the first-level batch folder, because that is what
    ``validate_folder()`` walks for analyses of one model. Returns ``None`` when
    the path has no ``outputs`` segment.
    """
    path = Path(path)
    try:
        relative = path.resolve().relative_to(OUTPUTS_DIR)
    except ValueError:
        parts = path.parts
        lowered = [part.lower() for part in parts]
        if "outputs" not in lowered:
            return None
        index = lowered.index("outputs")
        parts = parts[index + 1:]
        if not parts:
            return None
        return OUTPUTS_DIR.joinpath(parts[0])
    if not relative.parts:
        return None
    return OUTPUTS_DIR.joinpath(relative.parts[0])


def find_outputs(pattern: str) -> List[Path]:
    """
    Find outputs matching pattern in legacy + new locations.

    Searches in order:
    1. outputs/ top-level (legacy 256 dirs)
    2. outputs/fixtures/
    3. outputs/runs/

    Args:
        pattern: Glob pattern (e.g., "finite_comp_*")

    Returns:
        List of matching paths
    """
    found = []

    # Search legacy top-level
    if OUTPUTS_DIR.exists():
        found.extend(OUTPUTS_DIR.glob(pattern))

    # Search fixtures/
    fixtures_dir = OUTPUTS_DIR / "fixtures"
    if fixtures_dir.exists():
        found.extend(fixtures_dir.glob(pattern))

    # Search runs/
    runs_dir = OUTPUTS_DIR / "runs"
    if runs_dir.exists():
        found.extend(runs_dir.glob(pattern))

    return found


def assert_ancestor_is_outputs_or_fixtures(path: Path) -> bool:
    """
    Verify path is under outputs/ or fixtures/ (for test_high_confidence_live.py).

    Returns:
        True if ancestor is named "outputs" or "fixtures"
    """
    for parent in path.parents:
        if parent.name in ("outputs", "fixtures"):
            return True
    return False
