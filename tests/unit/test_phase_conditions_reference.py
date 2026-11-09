import importlib.util
import math
from pathlib import Path

import pytest


path=Path(__file__).resolve().parents[2]/'scripts/probes/PO-01/phase_conditions_reference.py'
spec=importlib.util.spec_from_file_location('phase_conditions_reference',path)
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_control_patch_uses_real_request_without_rewriting_original_fields():
    baseline=dict(fields=[dict(number=1,x=0.,y=0.,weight=1.,vdx=.1),
                          dict(number=2,x=0.,y=20.,weight=.5)])
    patch=probe.settings_patch(baseline,probe.CASES[2])
    assert patch.fields[0].y==5 and patch.fields[0].vdx==.1
    assert patch.fields[1].y==20 and patch.fields[1].weight==.5
    assert baseline['fields'][0]['y']==0
    assert patch.primary_wavelength==1
    assert patch.polarization.jx==1 and patch.polarization.y_phase==90


def test_oblique_direction_and_batch_use_same_controlled_field():
    settings=dict(fields=[dict(number=1,x=0.,y=5.),dict(number=2,x=0.,y=20.)],
                  field_normalization='Radial')
    points=[dict(section='sagittal',pupil=-.3),dict(section='tangential',pupil=.4)]
    request=probe.trace_request(points,settings,dict(jx=1.,jy=1.,y_phase=90.))
    assert [r.hy for r in request.rays]==[.25,.25]
    assert [(r.px,r.py) for r in request.rays]==[(-.3,0.),(0.,.4)]
    assert all(r.wavelength==1 for r in request.rays)
    direction=probe.incident_direction(settings['fields'][0])
    assert direction==pytest.approx([0,math.sin(math.radians(5)),math.cos(math.radians(5))])
