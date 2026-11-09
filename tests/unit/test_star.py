from pathlib import Path
from types import SimpleNamespace as N

import pytest
from pydantic import ValidationError
from zemax_mcp.errors import ZemaxError
from zemax_mcp.evaluation import Cancelled
from zemax_mcp.star import StarMixin, BRANCHES, check_deformation_option
from zemax_mcp.star_models import RunStar, StarRead


@pytest.mark.parametrize('payload', [
    dict(kind='fit_deformation', surface=0),
    dict(kind='fit_temperature', surface=1, deformation_option='OnlyRBMs'),
    dict(kind='fit_deformation', surface=1, deformation_option='NoDeformation', apply='enable'),
    dict(kind='fit_deformation', surface=1, deformation_option='OnlyRBMs', apply='disable'),
    dict(kind='fit_direct_index', surface=1, settings={}),
    dict(kind='fit_direct_index', surface=1, settings={'grid_1': 0}),
    dict(kind='fit_direct_index', surface=1, settings={'mba_tolerance': float('nan')}),
    dict(kind='fit_direct_index', surface=1, settings={'mba_min_fill': 2}),
    dict(kind='import_deformation', surface=1, path='fixture.txt', length_unit='Millimeters'),
])
def test_star_typed_conditions(payload):
    with pytest.raises(ValidationError): RunStar(request=payload)


class Backend(StarMixin):
    def __init__(self, directory, kind='deformation'):
        self.directory = directory
        self.source_path, self.work_path = 'source.zos', 'work.zos'
        self.revision = 0
        self.events = []
        self.restore_fails = False
        self.import_fails = False
        self.clobber_fit = False
        self.native = N(application=N(IsSTARModuleEnabled=True))
        self.fea = N(NumberOfDataPoints=2, Filename='baseline.txt')
        self.fits = N(Settings=N(Type=0, Grid1=8, Grid2=8, Grid3=8, MBAMaxLevel=4, MBATol=.01, MBAMinFill=.1),
                      IsSurfaceDeformationEnabled=False, IsTemperatureProfileEnabled=False, Options='NoDeformation')
        self.branch = N(FEAData=self.fea, Fits=self.fits,
                        RBMs=N(IsEnabled=False, UsedWeights=False, Decenters=N(X=0,Y=0,Z=0)),
                        CoordinateTransform=N(IsEnabled=False, Transform=N()))
        self.points = [N(X=float(i),Y=0.,Z=0.,DX=0.,DY=0.,DZ=.1,T=20.,Index=1.5) for i in range(2)]
        self.fea.GetFEAPointsSafe = lambda: self.points
        self.fea.IsDirectIndexApplied = lambda: getattr(self, 'index_enabled', False)
        for data_kind, (name, imported, method, enable, disable, active) in BRANCHES.items():
            setattr(self.fea, imported, True)
            setattr(self.fea, method, self.import_data)
            setattr(self.fits, enable, lambda active=active: self.apply(active, True))
            setattr(self.fits, disable, lambda active=active: self.apply(active, False))
        self.fits.Refit = self.refit
        self.local = True
        self.branch.IsDataLocalCS = lambda: self.local
        self.branch.SetDataIsLocal = lambda: setattr(self, 'local', True)
        self.branch.SetDataIsGlobal = lambda: setattr(self, 'local', False)
        star_data = N(**{values[0]: self.branch for values in BRANCHES.values()})
        self.row = N(STARData=star_data)
        self.system = N(SystemData=N(Units=N(LensUnits='Millimeters')))
    def _require_sequential(self): pass
    def _row(self, index): return self.row
    def context(self): return dict(model_revision=self.revision)
    def _mutate(self, label):
        self.events.append('checkpoint'); self.revision += 1
        self.last_checkpoint = 'checkpoint.zos'
    def _cancel_boundary(self, task):
        if task['cancel_requested']: raise Cancelled()
    def _composite(self, kind, settings, factory):
        self.task = dict(cancel_requested=False, rows=[])
        self.flow = factory(self.task)
        return self.task
    def _restore_model(self, task, snapshot, source, work):
        self.events.append('restore')
        if self.restore_fails: raise ZemaxError('RESTORE_FAILED', 'fixture restoration failure')
        task['restoration'] = dict(restored=True)
    @staticmethod
    def _evaluation_error(exc):
        return exc.as_dict() if isinstance(exc, ZemaxError) else dict(code='NATIVE_ERROR',message=str(exc))
    def import_data(self, path):
        self.events.append('import')
        if self.import_fails: raise ZemaxError('NATIVE_IMPORT', 'fixture import failure')
        self.fea.Filename = path
    def apply(self, active, enabled):
        self.events.append('apply')
        if active: setattr(self.fits, active, enabled)
        else: self.index_enabled = enabled
    def refit(self):
        self.events.append('refit')
        if self.clobber_fit: self.fits.Settings.Grid1 = 99


@pytest.mark.parametrize('kind', BRANCHES)
def test_star_point_paging_preserves_data_kind_and_native_state(tmp_path, kind):
    b = Backend(tmp_path)
    result = b.get_star_data(StarRead(surface=1, data_kind=kind, include_points=True, count=1))
    assert len(result['rows']) == 1 and result['next_start'] == 1
    assert result['fit_settings']['Grid1'] == 8
    assert result['coordinate_unit'] == 'Millimeters'
    assert b.revision == 0 and b.events == []
    b.points = []
    with pytest.raises(ZemaxError) as exc:
        b.get_star_data(StarRead(surface=1, data_kind=kind, include_points=True))
    assert exc.value.code == 'INVALID_RESULT_DATA'


def test_star_feature_flag_checked_before_data_access(tmp_path):
    b = Backend(tmp_path); b.native.application.IsSTARModuleEnabled = False
    def unexpected_access(index):
        raise AssertionError('STAR data must not be accessed while the module is disabled')
    b._row = unexpected_access
    with pytest.raises(ZemaxError) as exc: b.get_star_data(StarRead(surface=1))
    assert exc.value.code == 'FEATURE_UNAVAILABLE'
    assert exc.value.details['enabled'] is False
    assert 'Enterprise-level' in exc.value.details['required_license']
    assert '2024 R2' in exc.value.details['requirement_source']
    assert '1708' in exc.value.details['requirement_source']
    assert 'IsSTARModuleEnabled' in exc.value.details['next_action']
    assert b.events == [] and b.revision == 0


@pytest.mark.parametrize('kind', BRANCHES)
def test_star_import_stages_resource_and_checks_coordinate_selection(tmp_path, kind):
    b = Backend(tmp_path)
    source = tmp_path / 'source.txt'; source.write_text('0 0 0 0 0 0\n')
    req = RunStar(request=dict(kind='import_'+kind, surface=1, path=str(source),
                               length_unit='Millimeters', coordinate_system='global'))
    assert RunStar.model_validate(req.model_dump()) == req
    b.run_star_operation(req); list(b.flow)
    result = b.task['payload']['actual']
    assert result['local_coordinates'] is False
    assert Path(result['filename']).parent.name.startswith('star_input_')
    assert b.events == ['checkpoint', 'import']
    assert b.task['baseline']['context']['model_revision'] == 0


def import_request(path, unit='Millimeters'):
    return RunStar(request=dict(kind='import_deformation', surface=1, path=str(path),
                                length_unit=unit, coordinate_system='local'))


def test_star_input_preflight_does_not_modify_model(tmp_path):
    b = Backend(tmp_path)
    with pytest.raises(ZemaxError) as exc: b.run_star_operation(import_request(tmp_path/'missing.txt'))
    assert exc.value.code == 'INVALID_INPUT_FILE'
    path = tmp_path/'fea.txt'; path.write_text('fixture')
    with pytest.raises(ZemaxError) as exc: b.run_star_operation(import_request(path, 'Meters'))
    assert exc.value.code == 'UNIT_MISMATCH'
    assert b.events == []


@pytest.mark.parametrize('restore_fails', [False, True])
def test_star_import_failure_restores_and_preserves_original_error(tmp_path, restore_fails):
    b = Backend(tmp_path); b.import_fails = True; b.restore_fails = restore_fails
    path = tmp_path/'fea.txt'; path.write_text('fixture')
    b.run_star_operation(import_request(path))
    with pytest.raises(ZemaxError) as exc: list(b.flow)
    assert b.events == ['checkpoint', 'import', 'restore']
    if restore_fails:
        assert exc.value.code == 'STAR_RESTORE_FAILED'
        assert exc.value.details['original_error']['code'] == 'NATIVE_IMPORT'
    else: assert exc.value.code == 'NATIVE_IMPORT'


def test_star_import_cancel_restores_at_boundary(tmp_path):
    b = Backend(tmp_path)
    path = tmp_path/'fea.txt'; path.write_text('fixture')
    b.run_star_operation(import_request(path)); next(b.flow)
    b.task['cancel_requested'] = True
    with pytest.raises(Cancelled): next(b.flow)
    assert b.events[-1] == 'restore'


@pytest.mark.parametrize('clobber', [False, True])
def test_star_fit_partial_settings_final_readback_and_apply_order(tmp_path, monkeypatch, clobber):
    import zemax_mcp.star as module
    monkeypatch.setattr(module, 'checked_setting', lambda native, obj, name, value: setattr(obj, name, value))
    b = Backend(tmp_path); b.clobber_fit = clobber
    q = RunStar(request=dict(kind='fit_temperature', surface=1, settings=dict(grid_1=16), apply='enable'))
    b.run_star_operation(q)
    if clobber:
        with pytest.raises(ZemaxError) as exc: list(b.flow)
        assert exc.value.code == 'SETTING_REJECTED' and b.events[-1] == 'restore'
    else:
        list(b.flow)
        assert b.events == ['checkpoint', 'refit', 'apply']
        assert b.fits.Settings.Grid1 == 16 and b.fits.Settings.Grid2 == 8


def test_star_option_compares_enum_values_instead_of_alias_names():
    class Enum:
        def __init__(self, value): self.value=value
        def Equals(self, other): return self.value == other.value
        def __str__(self): return 'native_alias'
    fits = N(Options=Enum(1))
    native = N(api=N(Editors=N(LDE=N(STARDeformationOption=None))), enum=lambda _,name: Enum(1))
    check_deformation_option(native, fits, 'DeformationWithoutRBMs')


@pytest.mark.parametrize('kind', BRANCHES)
def test_star_native_fitted_sample_values(tmp_path, kind):
    b = Backend(tmp_path)
    b.fits.GetFittedDeformation = lambda x,y: N(DX=x, DY=y, DZ=.25)
    b.fits.GetFittedIndex = lambda x,y,z: 1.5
    b.fits.GetFittedTemperature = lambda x,y,z: 21.
    result = b.get_star_data(StarRead(surface=1, data_kind=kind, sample_points=[dict(x=1,y=2)]))
    row = result['fit_evaluations'][0]
    if kind == 'deformation': assert (row['dx'],row['dy'],row['dz']) == (1,2,.25)
    else: assert row['refractive_index'] == 1.5
    if kind == 'temperature': assert row['temperature'] == 21.


def unload_request(kind):
    return RunStar(request=dict(kind='unload_'+kind, surface=1))


def _wire_unload(b, kind, clears=True, raises=False):
    attr = BRANCHES[kind][1]

    def _unload():
        b.events.append('unload')
        if raises:
            raise ZemaxError('NATIVE_UNLOAD', 'fixture unload failure')
        if clears:
            setattr(b.fea, attr, False)
    b.fea.UnloadData = _unload
    b.fea.Filename = 'loaded_fea.txt'


@pytest.mark.parametrize('kind', BRANCHES)
def test_star_unload_success_clears_flag_and_retains_source(tmp_path, kind):
    b = Backend(tmp_path)
    _wire_unload(b, kind, clears=True)
    srcfile = tmp_path / 'fea_src.txt'; srcfile.write_text('fixture')
    b.fea.Filename = str(srcfile)
    attr = BRANCHES[kind][1]
    assert getattr(b.fea, attr) is True
    b.run_star_operation(unload_request(kind)); list(b.flow)
    payload = b.task['payload']
    assert payload['before'] == dict(imported=True, total=2, filename=str(srcfile))
    assert payload['after']['imported'] is False
    sf = payload['source_file']
    assert sf['path'] == str(srcfile)
    assert sf['exists_before'] is True and sf['exists_after'] is True
    assert sf['no_source_delete_performed'] is True
    assert srcfile.exists()  # adapter did not delete the staged source
    assert payload['detail']['imported'] is False
    assert b.events == ['checkpoint', 'unload']
    assert b.task['baseline']['context']['model_revision'] == 0


@pytest.mark.parametrize('kind', BRANCHES)
def test_star_unload_succeeds_when_detail_read_unavailable(tmp_path, kind):
    """Empty-data Fits objects may be inaccessible; a successful unload must not fail on it."""
    b = Backend(tmp_path)
    _wire_unload(b, kind, clears=True)

    def boom(req):
        raise ZemaxError('INVALID_RESULT_DATA', 'Fits unavailable on empty data')

    b.get_star_data = boom
    b.run_star_operation(unload_request(kind)); list(b.flow)
    payload = b.task['payload']
    assert payload['after']['imported'] is False
    assert 'detail' not in payload
    assert payload['detail_unavailable']['code'] == 'INVALID_RESULT_DATA'
    assert b.events == ['checkpoint', 'unload']  # success, no restore


@pytest.mark.parametrize('kind', BRANCHES)
def test_star_unload_requires_imported_data(tmp_path, kind):
    b = Backend(tmp_path)
    _wire_unload(b, kind)
    setattr(b.fea, BRANCHES[kind][1], False)
    with pytest.raises(ZemaxError) as exc:
        b.run_star_operation(unload_request(kind))
    assert exc.value.code == 'MISSING_FEA_DATA'
    assert b.events == []


@pytest.mark.parametrize('kind', BRANCHES)
def test_star_unload_rejects_when_flag_not_cleared(tmp_path, kind):
    b = Backend(tmp_path)
    _wire_unload(b, kind, clears=False)
    b.run_star_operation(unload_request(kind))
    with pytest.raises(ZemaxError) as exc:
        list(b.flow)
    assert exc.value.code == 'SETTING_REJECTED'
    assert b.events == ['checkpoint', 'unload', 'restore']


@pytest.mark.parametrize('kind', BRANCHES)
def test_star_unload_cancel_restores_at_boundary(tmp_path, kind):
    b = Backend(tmp_path)
    _wire_unload(b, kind)
    b.run_star_operation(unload_request(kind)); next(b.flow)
    b.task['cancel_requested'] = True
    with pytest.raises(Cancelled): next(b.flow)
    assert b.events[-1] == 'restore'


@pytest.mark.parametrize('kind', BRANCHES)
def test_star_unload_native_failure_restores_and_preserves_error(tmp_path, kind):
    b = Backend(tmp_path); b.restore_fails = True
    _wire_unload(b, kind, raises=True)
    b.run_star_operation(unload_request(kind))
    with pytest.raises(ZemaxError) as exc:
        list(b.flow)
    assert exc.value.code == 'STAR_RESTORE_FAILED'
    assert exc.value.details['original_error']['code'] == 'NATIVE_UNLOAD'
    assert b.events == ['checkpoint', 'unload', 'restore']


@pytest.mark.parametrize('payload', [
    dict(kind='unload_deformation', surface=0),
    dict(kind='unload_temperature'),
    dict(kind='unload_scan', surface=1),
])
def test_star_unload_parameter_contract(payload):
    with pytest.raises(ValidationError): RunStar(request=payload)
