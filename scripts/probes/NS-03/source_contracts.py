"""Bounded native source spectrum/direction settings and result outlets."""
import sys
from pathlib import Path

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.probes.D005 import runtime_contracts as contracts


def run(output, remaining=False):
    contracts.ANALYSIS_IDS={
        'source_spectrum_viewer':('SourceSpectrumViewer',None),
        'directivity_plot':('DirectivityPlot',None),
    }
    if remaining:
        contracts.ANALYSIS_IDS={name:(native,None) for name,native in [
            ('flux_vs_wavelength','FluxvsWavelength'),
            ('source_color_1931','SourceColorChart1931'),
            ('source_color_1976','SourceColorChart1976'),
            ('source_polar_viewer','SourcePolarViewer'),
            ('source_illumination_map','SourceIlluminationMap'),
            ('photoluminescence_viewer','PhotoluminscenceViewer'),
            ('radiant_source_model_viewer','RadiantSourceModelViewerSettings'),
            ('roadway_lighting','RoadwayLighting'),
        ]}
    contracts.run(output,source_model=Path.home()/'Documents/Zemax/Samples/Non-sequential/Colorimetry/Example 1  Two-color mixing gives white.zos')


if __name__=='__main__':run(sys.argv[1],'--remaining' in sys.argv[2:])
