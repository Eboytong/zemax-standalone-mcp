"""STAR data access and cooperative, checkpointed import/fit operations."""
from pathlib import Path
import shutil
import uuid

from .errors import ZemaxError
from .detectors import checked_setting, check_setting_readback
from .star_models import StarRead

BRANCHES = {
    'deformation': ('Deformations', 'AreDeformationsImported', 'ImportDeformations',
                    'ApplyDeformations', 'RemoveDeformations', 'IsSurfaceDeformationEnabled'),
    'temperature': ('Temperatures', 'AreTemperaturesImported', 'ImportTemperatures',
                    'ApplyTemperatures', 'RemoveTemperatures', 'IsTemperatureProfileEnabled'),
    'direct_index': ('DirectIndex', 'IsDirectIndexImported', 'ImportDirectIndex',
                     'ApplyIndex', 'RemoveIndex', None),
}
FIT_FIELDS = dict(grid_1='Grid1', grid_2='Grid2', grid_3='Grid3', mba_max_level='MBAMaxLevel',
                  mba_tolerance='MBATol', mba_min_fill='MBAMinFill')
FIT_RESULT_FIELDS = ('Points', 'FitLevels', 'FitAccuracy', 'FitFill', 'FitNorm', 'FitAverage', 'FitRMS', 'FitPV')
STAR_LICENSE_REQUIREMENT = 'Ansys Zemax OpticStudio Enterprise-level license'
STAR_LICENSE_SOURCE = 'OpticStudio User Manual 2024 R2, The STAR Tab, printed p.1708'


def read_fields(obj, names):
    values = {}
    for name in names:
        try:
            values[name] = getattr(obj, name)
        except Exception as exc:
            values.setdefault('unavailable_fields', {})[name] = str(exc)
    return values


def fit_enabled(branch, data_kind):
    field = BRANCHES[data_kind][5]
    return bool(getattr(branch.Fits, field)) if field else bool(branch.FEAData.IsDirectIndexApplied())


def check_deformation_option(native, fits, option, write=False):
    expected = native.enum(native.api.Editors.LDE.STARDeformationOption, option)
    if write:
        native.set_enum(fits, 'Options', option)
    if not fits.Options.Equals(expected):
        raise ZemaxError('SETTING_REJECTED', 'STAR deformation option was not adopted.',
                         requested=option, actual=str(fits.Options))


class StarMixin:
    def _require_star(self):
        self._require_sequential()
        if not bool(self.native.application.IsSTARModuleEnabled):
            raise ZemaxError('FEATURE_UNAVAILABLE', '当前原生应用未启用 STAR。', feature='STAR', enabled=False,
                             required_license=STAR_LICENSE_REQUIREMENT,
                             requirement_source=STAR_LICENSE_SOURCE,
                             next_action='Check Enterprise-level license availability, then verify IsSTARModuleEnabled in a new native application.')

    def _star_branch(self, surface, data_kind):
        self._require_star()
        return getattr(self._row(surface).STARData, BRANCHES[data_kind][0])

    def get_star_data(self, req):
        branch = self._star_branch(req.surface, req.data_kind)
        data = branch.FEAData
        count = int(data.NumberOfDataPoints)
        if req.start > count:
            raise ZemaxError('INDEX_OUT_OF_RANGE', 'STAR point page starts beyond the native data.',
                             start=req.start, total=count)
        fits = branch.Fits
        settings = read_fields(fits.Settings, ('Type', *FIT_FIELDS.values()))
        result = dict(surface=req.surface, data_kind=req.data_kind, imported=bool(getattr(data, BRANCHES[req.data_kind][1])),
                      filename=str(data.Filename), total=count, local_coordinates=bool(branch.IsDataLocalCS()),
                      enabled=fit_enabled(branch, req.data_kind), fit_settings=settings,
                      coordinate_unit=str(self.system.SystemData.Units.LensUnits),
                      temperature_unit='Celsius', index_unit='dimensionless',
                      unit_definition='FEA input coordinates and displacements must match lens units; no unit conversion applied',
                      point_source='native GetFEAPointsSafe; complete native array is materialized before output pagination')
        names = ('FitResultsDX', 'FitResultsDY', 'FitResultsDZ', 'FitResultsAverage') if req.data_kind == 'deformation' else ('FitResultsIndex',)
        result['fit_results'] = {}
        for name in names:
            try: result['fit_results'][name] = read_fields(getattr(fits, name), FIT_RESULT_FIELDS)
            except Exception as exc: result['fit_results'][name] = dict(error=str(exc))
        if req.data_kind == 'deformation':
            result['deformation_option'] = str(fits.Options)
            result['rigid_body'] = dict(enabled=bool(branch.RBMs.IsEnabled), used_weights=bool(branch.RBMs.UsedWeights),
                                       decenter=read_fields(branch.RBMs.Decenters, ('X', 'Y', 'Z')))
        result['coordinate_transform'] = dict(enabled=bool(branch.CoordinateTransform.IsEnabled),
                                              transform=read_fields(branch.CoordinateTransform.Transform,
                                                ('XOffset', 'YOffset', 'ZOffset', 'R11', 'R12', 'R13', 'R21', 'R22', 'R23', 'R31', 'R32', 'R33')))
        from .star_controls import rigid_body_state, coordinate_state, component_state
        readers = dict(subsystem=lambda:dict(update_mode=str(self.system.STARSubsystem.UpdateMode)),
                       coordinate_transform=lambda:coordinate_state(branch.CoordinateTransform),
                       component=lambda:component_state(self._row(req.surface).STARData.ComponentRBMs))
        if req.data_kind == 'deformation': readers['rigid_body'] = lambda:rigid_body_state(branch.RBMs)
        if req.data_kind == 'temperature':
            readers['thermal'] = lambda:dict(fit_type=int(branch.GetThermalFEAFitType()),
                working_wavelength=int(branch.GetWorkingWavelength()),primary_wavelength=float(branch.PrimaryWavelengthValue))
        if req.data_kind in {'temperature','direct_index'}:
            readers['volume'] = lambda:dict(grin_step=float(branch.GRINStep),fit_grin_step=float(branch.Fits.GRINStep),
                unit_source='native GRINStep members; physical step convention requires native acceptance')
        result['controls'] = {}
        for name, reader in readers.items():
            try: result['controls'][name] = reader()
            except Exception as exc: result['controls'][name] = dict(read_error=str(exc))
        if req.include_points:
            points = data.GetFEAPointsSafe() if count else []
            actual = int(points.Length) if hasattr(points, 'Length') else len(points)
            if actual != count:
                raise ZemaxError('INVALID_RESULT_DATA', 'STAR point array differs from native count.', expected=count, actual=actual)
            end = min(count, req.start + req.count)
            columns = ('X', 'Y', 'Z', 'DX', 'DY', 'DZ') if req.data_kind == 'deformation' else ('X', 'Y', 'Z', 'T', 'Index') if req.data_kind == 'temperature' else ('X', 'Y', 'Z', 'Index')
            result.update(rows=[dict(index=i, **{name: float(getattr(points[i], name)) for name in columns}) for i in range(req.start, end)],
                          next_start=end if end < count else None)
        if req.sample_points:
            if not result['imported']:
                raise ZemaxError('MISSING_FEA_DATA', 'Fit sampling requires imported STAR data.', data_kind=req.data_kind)
            samples = []
            for i, point in enumerate(req.sample_points):
                row = dict(index=i, **point.model_dump())
                if req.data_kind == 'deformation':
                    method = fits.GetFittedDeformationRBMremoved if req.remove_rigid_body else fits.GetFittedDeformation
                    value = method(point.x, point.y)
                    row.update(dx=float(value.DX), dy=float(value.DY), dz=float(value.DZ))
                else:
                    row['index'] = i
                    row['refractive_index'] = float(fits.GetFittedIndex(point.x, point.y, point.z))
                    if req.data_kind == 'temperature':
                        row['temperature'] = float(fits.GetFittedTemperature(point.x, point.y, point.z))
                samples.append(row)
            result.update(fit_evaluations=samples, remove_rigid_body=req.remove_rigid_body,
                          fit_evaluation_source='native fitted-data GetFitted* methods; native coordinate convention retained')
        return result

    def _run_star_unload(self, q, data_kind):
        imported_attr = BRANCHES[data_kind][1]
        probe = self._star_branch(q.surface, data_kind).FEAData
        if not bool(getattr(probe, imported_attr)):
            raise ZemaxError('MISSING_FEA_DATA', 'No STAR data is loaded to unload.', data_kind=data_kind)

        def read_state(data):
            return dict(imported=bool(getattr(data, imported_attr)),
                        total=int(data.NumberOfDataPoints), filename=str(data.Filename))

        def flow(task):
            self._cancel_boundary(task)
            source, work = self.source_path, self.work_path
            baseline_context = self.context()
            self._mutate('star_' + q.kind)
            snapshot = self.last_checkpoint
            task['baseline'] = dict(path=snapshot, context=baseline_context)
            task['payload'] = dict(operation=q.kind, data_kind=data_kind,
                                   cancellation='cooperative between native calls; an active unload call completes before cancellation',
                                   resource_ownership='STAR data objects owned by the optical system; no standalone native tool created')
            try:
                data = self._star_branch(q.surface, data_kind).FEAData
                before = read_state(data)
                src_file = Path(before['filename']) if before['filename'] else None
                exists_before = src_file.exists() if src_file else None
                task['payload']['before'] = before
                data.UnloadData()
                task['progress'] = 60
                yield
                self._cancel_boundary(task)
                after = read_state(data)
                exists_after = src_file.exists() if src_file else None
                task['payload']['after'] = after
                task['payload']['source_file'] = dict(
                    path=(str(src_file) if src_file else None),
                    exists_before=exists_before, exists_after=exists_after,
                    no_source_delete_performed=True)
                if after['imported']:
                    raise ZemaxError('SETTING_REJECTED', 'Native STAR unload did not clear the imported flag.',
                                     data_kind=data_kind, before=before, after=after)
                # Detailed STAR read is best-effort; unavailability is recorded, not fatal.
                try:
                    task['payload']['detail'] = self.get_star_data(StarRead(surface=q.surface, data_kind=data_kind))
                except Exception as detail_error:
                    task['payload']['detail_unavailable'] = self._evaluation_error(detail_error)
                task['payload']['final_context'] = self.context()
            except Exception as original:
                try: self._restore_model(task, snapshot, source, work)
                except Exception as restore:
                    raise ZemaxError('STAR_RESTORE_FAILED', 'STAR unload failed and baseline restoration failed.',
                                     original_error=self._evaluation_error(original), restoration_error=self._evaluation_error(restore),
                                     checkpoint=snapshot) from original
                raise
        return self._composite('star_operation', q.model_dump(), flow)

    def run_star_operation(self, req):
        q = req.request
        from .star_controls import CONTROL_KINDS, run_control
        if q.kind in CONTROL_KINDS: return run_control(self, q)
        data_kind = q.kind.split('_', 1)[1]
        if q.kind.startswith('unload_'):
            return self._run_star_unload(q, data_kind)
        branch = self._star_branch(q.surface, data_kind)
        source_file = None
        if q.kind.startswith('import_'):
            source_file = Path(q.path)
            if not source_file.is_absolute() or not source_file.is_file():
                raise ZemaxError('INVALID_INPUT_FILE', 'STAR import requires an existing absolute file path.', path=q.path)
            actual_unit = str(self.system.SystemData.Units.LensUnits)
            if actual_unit != q.length_unit:
                raise ZemaxError('UNIT_MISMATCH', 'FEA file length unit must match current lens units.',
                                 requested=q.length_unit, actual=actual_unit)
        elif not bool(getattr(branch.FEAData, BRANCHES[data_kind][1])):
            raise ZemaxError('MISSING_FEA_DATA', 'Import the requested STAR data before fitting.', data_kind=data_kind)

        def flow(task):
            self._cancel_boundary(task)
            source, work = self.source_path, self.work_path
            baseline_context = self.context()
            self._mutate('star_' + q.kind)
            snapshot = self.last_checkpoint
            task['baseline'] = dict(path=snapshot, context=baseline_context)
            task['payload'] = dict(operation=q.kind, data_kind=data_kind,
                                   cancellation='cooperative between native calls; an active import/refit call completes before cancellation')
            try:
                if source_file is not None:
                    staged = self.directory / ('star_input_' + uuid.uuid4().hex) / source_file.name
                    staged.parent.mkdir()
                    shutil.copyfile(source_file, staged)
                    task['payload']['source_resource'] = dict(source=str(source_file), staged=str(staged),
                                                             length_unit=q.length_unit, coordinate_system=q.coordinate_system)
                    branch = self._star_branch(q.surface, data_kind)
                    (branch.SetDataIsLocal if q.coordinate_system == 'local' else branch.SetDataIsGlobal)()
                    if bool(branch.IsDataLocalCS()) != (q.coordinate_system == 'local'):
                        raise ZemaxError('SETTING_REJECTED', 'STAR coordinate system was not adopted.')
                    self._cancel_boundary(task)
                    getattr(branch.FEAData, BRANCHES[data_kind][2])(str(staged))
                    if not bool(getattr(branch.FEAData, BRANCHES[data_kind][1])) or int(branch.FEAData.NumberOfDataPoints) <= 0:
                        raise ZemaxError('STAR_IMPORT_FAILED', 'Native STAR import did not adopt a nonempty data set.')
                    filename = str(branch.FEAData.Filename)
                    if str(Path(filename).resolve()).casefold() != str(staged.resolve()).casefold():
                        raise ZemaxError('SETTING_REJECTED', 'STAR import file did not match on readback.', requested=str(staged), actual=filename)
                else:
                    branch = self._star_branch(q.surface, data_kind)
                    fits = branch.Fits
                    if q.settings:
                        for field, name in FIT_FIELDS.items():
                            value = getattr(q.settings, field)
                            if value is not None: checked_setting(self.native, fits.Settings, name, value)
                    if q.deformation_option is not None:
                        check_deformation_option(self.native, fits, q.deformation_option, write=True)
                    task['progress'] = 25
                    yield
                    self._cancel_boundary(task)
                    fits.Refit()
                    task['progress'] = 75
                    yield
                    self._cancel_boundary(task)
                    if q.apply != 'keep':
                        getattr(fits, BRANCHES[data_kind][3 if q.apply == 'enable' else 4])()
                        if fit_enabled(branch, data_kind) != (q.apply == 'enable'):
                            raise ZemaxError('SETTING_REJECTED', 'STAR fitted-data enable state was not adopted.')
                    if q.settings:
                        for field, name in FIT_FIELDS.items():
                            value = getattr(q.settings, field)
                            if value is not None: check_setting_readback(fits.Settings, name, value)
                    if q.deformation_option is not None:
                        check_deformation_option(self.native, fits, q.deformation_option)
                task['progress'] = 90
                yield
                self._cancel_boundary(task)
                task['payload']['actual'] = self.get_star_data(StarRead(surface=q.surface, data_kind=data_kind))
                task['payload']['final_context'] = self.context()
                task['payload']['resource_ownership'] = 'STAR data objects are owned by the optical system; no standalone native tool created'
            except Exception as original:
                try: self._restore_model(task, snapshot, source, work)
                except Exception as restore:
                    raise ZemaxError('STAR_RESTORE_FAILED', 'STAR operation failed and baseline restoration failed.',
                                     original_error=self._evaluation_error(original), restoration_error=self._evaluation_error(restore),
                                     checkpoint=snapshot) from original
                raise
        return self._composite('star_operation', q.model_dump(), flow)
