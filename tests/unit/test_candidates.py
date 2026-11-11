from copy import deepcopy
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from zemax_mcp.candidate_models import ManageCandidates, CandidateEvaluation
from zemax_mcp.candidates import compare_candidates, evaluation_conditions
from zemax_mcp.errors import ZemaxError


def evaluated(key, value, glass):
    return dict(candidate_id=key, snapshot={'material': glass}, evaluation=dict(state='succeeded',
        contract={'evaluation': {'merit': True}, 'conditions': {'lens_units': 'Millimeters'}},
        metrics=[dict(key='merit', value=value, unit='mm')]))


def test_material_differences_compare_under_frozen_contract():
    left, right = evaluated('a', 1, 'BK7'), evaluated('b', .7, 'F2')
    result = compare_candidates(left, right)
    assert result['compatible'] and result['metrics'][0]['delta'] == pytest.approx(-.3)
    assert result['design_differences']['left'] != result['design_differences']['right']
    left['external_metrics'] = [dict(key='quote', value=10, unit='CNY', source='supplier A')]
    right['external_metrics'] = [dict(key='quote', value=8, unit='CNY', source='supplier B')]
    assert compare_candidates(left, right)['external_metrics'][0]['delta'] == -2
    right['evaluation']['contract']['conditions']['lens_units'] = 'Centimeters'
    assert not compare_candidates(left, right)['compatible']
    right['evaluation'] = None
    with pytest.raises(ZemaxError):
        compare_candidates(left, right)


def test_action_specific_contracts_and_paths():
    for value in [dict(action='create', label='baseline'),
                  dict(action='list', candidate_id='a'),
                  dict(action='select', design_id='../outside', candidate_id='a'),
                  dict(action='checkpoint', design_id='a', candidate_id='b', label='c')]:
        with pytest.raises(ValidationError):
            ManageCandidates(request=value)
    assert CandidateEvaluation(design_id='design', candidate_ids=['a']).candidate_ids == ['a']


def test_contract_retains_optical_conditions():
    original = dict(material_catalogs=['SCHOTT'], files={'coating': 'x'}, fields=[{'x': 1}],
                    wavelength=[.55], temperature=20, lens_units='Millimeters', title='example')
    result = evaluation_conditions(original)
    assert result == dict(fields=[{'x': 1}], wavelength=[.55], temperature=20, lens_units='Millimeters')
    assert original['material_catalogs'] == ['SCHOTT']


def test_persistent_index_and_candidate_context(tmp_path):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    from zemax_mcp.history import write_json
    backend = Backend(Config(tmp_path, tmp_path), native=SimpleNamespace(system=None))
    index = dict(schema_version=1, design_id='a', candidates={'b': evaluated('b', 1, 'BK7')})
    write_json(tmp_path / '_designs/a/index.json', index)
    request = ManageCandidates(request=dict(action='list', design_id='a'))
    assert backend.manage_candidates(request) == index
    restarted = Backend(Config(tmp_path, tmp_path), native=SimpleNamespace(system=None))
    assert restarted.manage_candidates(request) == index
    backend.work_path = tmp_path / 'current.zos'
    backend._selected_candidate = dict(design_id='a', candidate_id='b', parent_candidate_id=None,
                                        working_file=str(backend.work_path))
    assert backend.context()['candidate_id'] == 'b'
    backend.work_path = tmp_path / 'other.zos'
    assert 'candidate_id' not in backend.context()


@pytest.mark.parametrize('close_failure', [False, True])
def test_owned_copy_failure_resources_and_error_preservation(tmp_path, close_failure):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    origin = tmp_path / 'origin'
    (origin / 'Coatings').mkdir(parents=True)
    (origin / 'Coatings/example.dat').write_text('resource', encoding='utf-8')
    closed = []
    def save(path):
        raise ZemaxError('SAVE_FAILED', 'native save failure')
    def close(save_changes):
        closed.append(save_changes)
        if close_failure:
            raise RuntimeError('native close failure')
    owned = SimpleNamespace(LoadFile=lambda *a: True, SaveAs=save, Close=close)
    backend = Backend(Config(tmp_path, tmp_path), native=SimpleNamespace(system=SimpleNamespace(CopySystem=lambda: owned)))
    parent = dict(candidate_id='parent', model_path=str(origin / 'model.zos'), snapshot={})
    with pytest.raises(ZemaxError) as error:
        backend._candidate_save(dict(design_id='a', candidates={}), 'failed', parent, current=False)
    assert closed == [False]
    assert list((tmp_path / '_designs/a').glob('*/Coatings/example.dat'))
    if close_failure:
        assert backend.requires_reconnect
        assert error.value.details['operation_error']['code'] == 'SAVE_FAILED'
    else:
        assert error.value.code == 'SAVE_FAILED'
