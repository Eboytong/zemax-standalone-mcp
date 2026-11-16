"""Serial v261 regressions for the v1.4.1 product fixes."""
from contextlib import contextmanager
from itertools import product
import json
import math
from pathlib import Path
import time

import pytest

from tests.support.paths import run_dir
from zemax_mcp import __version__
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


class RegressionRun:
    def __init__(self, folder):
        self.folder = folder
        self.backend = Backend(Config(Path(r'C:\Program Files\ANSYS Inc\v261\Zemax OpticStudio'), folder))
        self.calls = []
        self.results = []

    def call(self, tool, arguments=None):
        response = self.backend.dispatch(tool, arguments or {})
        self.calls.append(dict(tool=tool, arguments=arguments, response=response))
        assert response['ok'], response
        return response['data']

    def finish(self, task):
        deadline = time.monotonic() + 60
        while task['state'] not in {'succeeded', 'failed', 'cancelled'}:
            assert time.monotonic() < deadline, task
            time.sleep(.02)
            task = self.call('get_task_status', dict(task_id=task['task_id']))
        return task, self.call('get_task_result', dict(task_id=task['task_id']))

    def write(self):
        record = dict(product_version=__version__, install_dir=str(self.backend.config.install_dir),
                      opticstudio_version=self.backend.version, opticstudio_build=self.backend.build_id,
                      results=self.results)
        (self.folder / 'regressions.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        (self.folder / 'calls.json').write_text(json.dumps(self.calls, ensure_ascii=False, indent=2), encoding='utf-8')

    @contextmanager
    def case(self, name):
        record = dict(test=name, outcome='running')
        self.results.append(record)
        try:
            self.call('new_system')
            yield record
        except BaseException as exc:
            record.update(outcome='failed', error=str(exc))
            raise
        else:
            record['outcome'] = 'passed'
        finally:
            self.write()


@pytest.fixture(scope='module')
def regression_run():
    run = RegressionRun(run_dir('v141_product_regressions'))
    try:
        run.call('connect')
        print(f'Native version: {run.backend.version}; build: {run.backend.build_id}; product: {__version__}', flush=True)
        yield run
    finally:
        run.write()
        run.backend.shutdown()
        print(f'v1.4.1 regression evidence: {run.folder}', flush=True)


@pytest.mark.zemax
def test_v141_native_merit_tolerant_target_and_weight(regression_run):
    run = regression_run
    with run.case('merit_tolerant_readback') as record:
        requested = 49.99999950000002
        result = run.call('update_merit_function', dict(mode='replace', operands=[
            dict(type='EFFL', target=requested, weight=requested)]))
        row = result['operands'][0]
        record.update(requested=requested, actual_target=row['target'], actual_weight=row['weight'])
        assert row['type'] == 'EFFL'
        assert row['target'] != requested, record
        assert math.isclose(row['target'], requested, rel_tol=1e-12, abs_tol=1e-12)
        assert math.isclose(row['weight'], requested, rel_tol=1e-12, abs_tol=1e-12)


@pytest.mark.zemax
@pytest.mark.parametrize('kind', ['deformation', 'temperature', 'direct_index'])
def test_v141_native_star_import_generated_zst(regression_run, kind):
    run = regression_run
    with run.case('star_import_' + kind) as record:
        run.call('insert_surfaces', dict(at=1))
        run.call('update_system_settings', dict(aperture_value=2, material_catalogs=['SCHOTT'],
            wavelengths=[dict(wavelength_um=.55)]))
        run.call('update_surfaces', dict(changes=[dict(surface=1, material='N-BK7', thickness=20,
            semi_diameter=1, replace_solves=True)]))
        if kind == 'deformation':
            rows = [[x, y, 0., 0., 0., .01] for x, y in product([-1., 0., 1.], repeat=2)]
        else:
            rows = [[x, y, z, 21. if kind == 'temperature' else 1.5]
                    for x, y, z in product([-1., 0., 1.], [-1., 0., 1.], [0., 10., 20.])]
        source = run.folder / (kind + '.txt')
        source.write_text('\n'.join(' '.join(map(str, row)) for row in rows) + '\n', encoding='utf-8')
        task, result = run.finish(run.call('run_star_operation', dict(request=dict(
            kind='import_' + kind, surface=1, path=str(source), length_unit='Millimeters', coordinate_system='local'))))
        record.update(task=task, result=result, fit_requested=False)
        assert task['state'] == 'succeeded', result
        resource = result['source_resource']
        assert resource['source'] == str(source)
        assert Path(resource['staged']).is_file()
        native = Path(resource['native'])
        assert native.is_absolute() and native.is_file() and native.suffix.lower() == '.zst', resource
        assert resource['native'] != resource['staged']
        assert result['actual']['filename'] == str(native)
        assert result['actual']['imported'] and result['actual']['total'] == len(rows)
        readback = run.call('get_star_data', dict(surface=1, data_kind=kind, include_points=True, count=2))
        assert readback['imported'] and len(readback['rows']) == 2


@pytest.mark.zemax
def test_v141_native_paraboloid_fft_through_focus_failed_result(regression_run):
    run = regression_run
    with run.case('paraboloid_fft_through_focus_no_result') as record:
        run.call('update_system_settings', dict(aperture_value=10,
            fields=[dict(x=0, y=0), dict(x=0, y=1), dict(x=0, y=2)],
            wavelengths=[dict(wavelength_um=.48), dict(wavelength_um=.55), dict(wavelength_um=.65)], primary_wavelength=2))
        run.call('update_surfaces', dict(changes=[dict(surface=1, radius=-200, conic=-1, material='MIRROR',
            thickness=-100, semi_diameter=5, replace_solves=True)]))
        run.call('save_lens_as', dict(path=str(run.folder / 'paraboloid.zos')))
        task, result = run.finish(run.call('run_analysis', dict(request=dict(kind='fft_through_focus_mtf',
            field=1, wavelength=2, sampling='S_256x256', number_of_steps=3, delta_focus=.1, frequency=50))))
        record.update(task=task, result=result)
        assert task['state'] == 'failed', result
        assert task['error']['code'] == 'NO_RESULT_DATA', task
        details = task['error']['details']
        report = Path(details['native_text'])
        text = report.read_text(encoding='utf-16')
        record.update(native_text_path=str(report), native_error_text=text)
        assert '计算终止' in text or 'computation terminated' in text.lower(), text
        assert '无效的结果' in text or 'invalid result' in text.lower(), text
        assert result['completed'] is False
        assert task['close_attempted'] and not task.get('cleanup_warnings'), task


@pytest.mark.zemax
def test_v141_native_cooke_fft_through_focus_valid_curves(regression_run):
    run = regression_run
    with run.case('cooke_fft_through_focus_valid_curves') as record:
        lens = Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        run.call('open_lens', dict(path=str(lens)))
        task, result = run.finish(run.call('run_analysis', dict(request=dict(kind='fft_through_focus_mtf'))))
        record.update(task=task, result=result)
        assert task['state'] == 'succeeded', result
        full = run.backend._full_result(task['task_id'])
        assert full['series'] and all(series['x'] and series['y'] for series in full['series'])
        assert task['close_attempted'] and not task.get('cleanup_warnings'), task
