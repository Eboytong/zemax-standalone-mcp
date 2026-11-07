from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest


def pytest_addoption(parser):
    parser.addoption("--run-zemax", action="store_true", default=False, help="Run real OpticStudio integration tests")


def pytest_collection_modifyitems(config, items):
    for item in items:
        item.user_properties.append(("validation_layer","native"if "zemax"in item.keywords else"ordinary"))
    if not config.getoption("--run-zemax"):
        skip = pytest.mark.skip(reason="Use --run-zemax to create a real Standalone instance")
        for item in items:
            if "zemax" in item.keywords:
                item.add_marker(skip)
