"""Locate a fluorescence input produced by the current native tests."""
from pathlib import Path
from tests.support.paths import find_outputs


def fluorescence_fixture(spec):
    original=Path(spec['fluorescence_fixture']).resolve()
    if (original/'dilute_fluorescence.zos').is_file() and (original/'fluorescence.zrd').is_file():
        return original
    candidates=sorted(find_outputs('fluorescence_integral_total_energy_*'),key=lambda p:p.stat().st_mtime,reverse=True)
    for folder in candidates:
        if (folder/'dilute_fluorescence.zos').is_file() and (folder/'fluorescence.zrd').is_file():
            return folder.resolve()
    raise FileNotFoundError('Run test_fluorescence_integral_live.py to create a current fluorescence lens/ZRD input.')
