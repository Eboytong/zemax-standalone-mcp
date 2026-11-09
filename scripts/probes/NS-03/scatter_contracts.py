"""Capture current native scatter-viewer settings and result outlets."""
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.probes.D005 import runtime_contracts as contracts


def run(output):
    contracts.ANALYSIS_IDS = {
        'scatter_function_viewer': ('ScatterFunctionViewer', None),
        'scatter_polar_plot': ('ScatterPolarPlotSettings', None),
    }
    contracts.run(output)


if __name__ == '__main__':
    run(sys.argv[1])
