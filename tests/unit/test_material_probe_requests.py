"""Check direct probe requests against the backend contract without starting ZOS."""
import ast
import runpy
from pathlib import Path

from zemax_mcp.models import COMMAND_MODELS


def test_dispersion_probe_wavelength_request_keeps_primary_at_system_level():
    root = Path(__file__).resolve().parents[2]
    probe = runpy.run_path(str(root/'scripts/probes/MA-01/dispersion_step_identity.py'))
    wavelengths = [.55, .5499, .5501]
    payload = probe['wavelength_request'](wavelengths)
    parsed = COMMAND_MODELS['update_system_settings'].model_validate(payload)
    assert parsed.primary_wavelength == 1
    assert [w.wavelength_um for w in parsed.wavelengths] == wavelengths


def test_material_probe_system_updates_validate_as_direct_backend_requests():
    root = Path(__file__).resolve().parents[2]
    path = root / 'scripts/probes/D002-MODEL_GLASS/model_glass_control018.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    requests = [node.args[1] for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'call' and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == 'update_system_settings']
    assert len(requests) == 3
    context = dict(dict=dict, changes={'pressure_atm': 0},
                   baseline={'pressure_atm': 1}, key='pressure_atm',
                   WAVELENGTHS=[.5875618, .5876, .4861327, .4861, .6562725, .6563])
    for expression in requests:
        payload = eval(compile(ast.Expression(expression), str(path), 'eval'), context)
        COMMAND_MODELS['update_system_settings'].model_validate(payload)


def test_athermal_probe_enables_environment_before_temperature_controls():
    root = Path(__file__).resolve().parents[2]
    probe = runpy.run_path(str(root/'scripts/probes/MA-01/athermal_missing_data.py'))
    request = COMMAND_MODELS['update_system_settings'].model_validate(probe['environment_request'](19.99))
    assert request.adjust_index_to_environment is True
    assert request.temperature_c == 19.99 and request.pressure_atm == 1.0


def test_athermal_catalog_keeps_placeholder_positions_and_missing_thermal_data(tmp_path):
    root = Path(__file__).resolve().parents[2]
    probe = runpy.run_path(str(root/'scripts/probes/MA-01/athermal_missing_data.py'))
    path = tmp_path/'sample.agf'
    path.write_text('NM F2HTi 2 0 1.6 36\nCD _ 0.1 0.2\nTD\nED 8.2 9.2\n', encoding='utf-8')
    entry = probe['catalog_records'](path)['F2HTI']
    assert entry['name'] == 'F2HTi'
    assert entry['cd'] == [None, 0.1, 0.2] and entry['td'] == []


def test_model_environment_refresh_request_preserves_environment_contract():
    root=Path(__file__).resolve().parents[2]
    probe=runpy.run_path(str(root/'scripts/probes/D002-MODEL_GLASS/environment_refresh.py'))
    for temperature,pressure in probe['ENVIRONMENTS']:
        parsed=COMMAND_MODELS['update_system_settings'].model_validate(
            probe['environment_request'](temperature,pressure))
        assert parsed.adjust_index_to_environment is True
        assert parsed.temperature_c==temperature and parsed.pressure_atm==pressure


def test_model_environment_candidates_separate_temperature_and_pressure():
    root=Path(__file__).resolve().parents[2]
    probe=runpy.run_path(str(root/'scripts/probes/D002-MODEL_GLASS/environment_refresh.py'))
    baseline=[1.6,1.61,1.59]
    changed=probe['environment_candidates'](baseline,10,1)
    assert changed['nominal_20_air']==baseline
    assert all(a<b for a,b in zip(changed['temperature_air'],baseline))
    vacuum=probe['environment_candidates'](baseline,20,0)
    assert vacuum['nominal_20_air']==vacuum['temperature_air']
    assert all(a>b for a,b in zip(vacuum['nominal_20_air'],baseline))


def test_gradium_capping_order_probe_changes_order_without_changing_final_parameters():
    root=Path(__file__).resolve().parents[2]
    probe=runpy.run_path(str(root/'scripts/probes/MA-01/gradium_capping_order.py'))
    plans=probe['plans'](2)
    assert list(plans[0]['updates'][0])==[1,2,8]
    assert list(plans[1]['updates'][0])==[1,8,2]
    for plan in plans:
        final={1:.01,2:1.,8:0}
        for patch in plan['updates']:
            COMMAND_MODELS['update_surfaces'].model_validate(dict(changes=[dict(surface=2,parameters=patch,replace_solves=True)]))
            final.update(patch)
        assert final=={1:.01,2:-.2,8:2}
