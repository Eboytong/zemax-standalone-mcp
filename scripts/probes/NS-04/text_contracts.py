"""Inspect formal settings and current default text-report outlets."""
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.probes.D005 import runtime_contracts as contracts


def run(output, graphics=False, nsc=False):
    contracts.ANALYSIS_IDS = {
        'prescription_data': ('PrescriptionDataSettings', None),
        'surface_data': ('SurfaceDataSettings', None),
    }
    source = None
    if graphics:
        contracts.ANALYSIS_IDS = {
            'iso_element_drawing': ('ISOElementDrawing', None),
            'zemax_element_drawing': ('ZemaxElementDrawing', None),
            'prescription_graphic': ('PrescriptionGraphic', None),
        }
    if nsc:
        contracts.ANALYSIS_IDS = {
            'nsc_object_viewer': ('NSCObjectViewer', None),
            'part_viewer': ('PartViewer', None),
        }
        source = Path.home() / 'Documents/Zemax/Samples/Non-sequential/Geometry Creation/Boolean Example 4-  a lens mount.zos'
    contracts.run(output, source_model=source)


if __name__ == '__main__':
    run(sys.argv[1], '--graphics' in sys.argv[2:], '--nsc' in sys.argv[2:])
