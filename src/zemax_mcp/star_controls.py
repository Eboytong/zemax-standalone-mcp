"""Checked STAR controls using the installed 2024 R2 member contracts."""
from .errors import ZemaxError
from .detectors import checked_setting, check_setting_value

CONTROL_KINDS = {'rigid_body', 'coordinate_transform', 'define_component', 'remove_component',
                 'component_rbm', 'thermal_controls', 'volume_controls', 'update_mode'}
MATRIX_FIELDS = ('R11','R12','R13','R21','R22','R23','R31','R32','R33')


def transform_values(obj):
    return dict(offset=[float(getattr(obj, name)) for name in ('XOffset','YOffset','ZOffset')],
                rotation_matrix=[float(getattr(obj, name)) for name in MATRIX_FIELDS])


def rigid_body_state(obj):
    point = obj.GetReferencePoint()
    return dict(enabled=bool(obj.IsEnabled), reference_point=[float(getattr(point,k)) for k in ('X','Y','Z')],
                used_weights=bool(obj.UsedWeights), transform=transform_values(obj.Transform))


def coordinate_state(obj):
    return dict(enabled=bool(obj.IsEnabled), default_frame=bool(obj.IsInDefaultFrameOfReference()),
                **transform_values(obj.Transform))


def component_state(obj):
    if not obj.IsPartOfAComponent(): return dict(in_component=False)
    members = [int(x) for x in obj.ListOfSurfacesInComponent]
    count = int(obj.NumberOfSurfacesInComponent)
    if count != len(members):
        raise ZemaxError('INVALID_RESULT_DATA', 'STAR component member count differs from native list.',
                         count=count, members=members)
    result = dict(in_component=True, first_surface=int(obj.FirstSurfaceInComponent),
                  last_surface=int(obj.LastSurfaceInComponent), members=members,
                  adjust_index_data_with_rbm=bool(obj.AdjustIndexDataWithComponentRBM),
                  rbms_removed=bool(obj.ComponentRBMsAreRemoved),
                  coordinate_breaks=bool(obj.CRBMsAreInCoordinateBreaks))
    try: result['transform'] = transform_values(obj.Transform)
    except Exception as exc: result['transform_error'] = str(exc)
    return result


def component_inventory(backend):
    groups = {}
    for number in range(1, backend.system.LDE.NumberOfSurfaces-1):
        data = backend._row(number).STARData.ComponentRBMs
        if data.IsPartOfAComponent():
            state = component_state(data)
            groups[state['first_surface']] = state['members']
    return groups


def check_mode(backend, requested, write=False):
    owner = backend.system.STARSubsystem
    expected = backend.native.enum(backend.native.api.STARUpdateMode, requested)
    if write: backend.native.set_enum(owner, 'UpdateMode', requested)
    if not owner.UpdateMode.Equals(expected):
        raise ZemaxError('SETTING_REJECTED', 'STAR update mode was not adopted.',
                         requested=requested, actual=str(owner.UpdateMode))


def prepare_control(backend, q):
    backend._require_star()
    context = {}
    if q.kind == 'update_mode': return context
    surface = q.first_surface if q.kind in {'define_component','remove_component'} else q.surface
    row = backend._row(surface)
    if q.kind in {'define_component','remove_component','component_rbm'}:
        owner = row.STARData.ComponentRBMs
        context.update(owner=owner, before_components=component_inventory(backend),
                       surface_count_before=int(backend.system.LDE.NumberOfSurfaces))
        if q.kind == 'define_component':
            if q.last_surface >= backend.system.LDE.NumberOfSurfaces-1:
                raise ZemaxError('INDEX_OUT_OF_RANGE', 'STAR component must precede the image surface.')
            occupied = [n for group in context['before_components'].values()
                        for n in group if q.first_surface <= n <= q.last_surface]
            if occupied:
                raise ZemaxError('RELATION_PROTECTED', 'STAR component overlaps an existing group.', surfaces=occupied)
        else:
            state = component_state(owner)
            if not state['in_component']:
                raise ZemaxError('MISSING_COMPONENT', 'Selected surface is not part of a STAR component.')
            context['before'] = state
            if q.kind == 'remove_component' and state['first_surface'] != q.first_surface:
                raise ZemaxError('INVALID_ARGUMENT', 'RemoveComponent requires the native first surface.',
                                 requested=q.first_surface, actual=state['first_surface'])
            if q.kind == 'component_rbm' and ((q.action == 'remove_from_fea' and state['rbms_removed']) or
                                            (q.action == 'add_coordinate_breaks' and state['coordinate_breaks'])):
                raise ZemaxError('CONDITION_NOT_MET', 'Requested STAR component RBM action is already applied.')
    else:
        data_kind = 'deformation' if q.kind == 'rigid_body' else 'temperature' if q.kind == 'thermal_controls' else q.data_kind
        branch = backend._star_branch(surface, data_kind)
        context['branch'] = branch
        if q.kind == 'rigid_body' and not branch.FEAData.AreDeformationsImported:
            raise ZemaxError('MISSING_FEA_DATA', 'Rigid-body extraction requires imported deformation data.')
        if q.kind == 'thermal_controls' and q.working_wavelength is not None:
            if q.working_wavelength > backend.system.SystemData.Wavelengths.NumberOfWavelengths:
                raise ZemaxError('INDEX_OUT_OF_RANGE', 'STAR working wavelength exceeds the system count.')
    return context


def apply_control(backend, q, context, task):
    def boundary(): backend._cancel_boundary(task)
    if q.kind == 'update_mode':
        if q.mode is not None:
            check_mode(backend, q.mode, write=True)
            yield
        boundary()
        if q.manual_update:
            backend.system.STARSubsystem.DoManualUpdate()
            yield
        boundary()
        return dict(update_mode=str(backend.system.STARSubsystem.UpdateMode), manual_update_executed=q.manual_update)
    if q.kind == 'rigid_body':
        owner = context['branch'].RBMs
        if q.reference_point:
            p = q.reference_point
            owner.SetReferencePoint(p.x, p.y, p.z)
            yield
        boundary()
        if q.enabled is not None:
            (owner.Enable if q.enabled else owner.Disable)()
            yield
        boundary()
        state = rigid_body_state(owner)
        if q.enabled is not None: check_setting_value('enabled', q.enabled, state['enabled'])
        if q.reference_point:
            for requested, actual in zip((q.reference_point.x,q.reference_point.y,q.reference_point.z),state['reference_point']):
                check_setting_value('reference_point', requested, actual)
        return state
    if q.kind == 'coordinate_transform':
        owner = context['branch'].CoordinateTransform
        target_enabled = bool(owner.IsEnabled) if q.enabled is None else q.enabled
        if q.reset:
            owner.ResetToDefaultFrameOfReference()
            yield
        else:
            if q.offset is not None or q.rotation_matrix is not None:
                owner.Enable()
                yield
            boundary()
            if q.offset is not None:
                owner.SetDecenter(q.offset.x, q.offset.y, q.offset.z)
                yield
            boundary()
            if q.rotation_matrix is not None:
                owner.SetRotationMatrix(*q.rotation_matrix)
                yield
        boundary()
        (owner.Enable if target_enabled else owner.Disable)()
        yield
        boundary()
        state = coordinate_state(owner)
        check_setting_value('enabled', target_enabled, state['enabled'])
        if q.reset: check_setting_value('default_frame', True, state['default_frame'])
        for key, values in [('offset', [q.offset.x,q.offset.y,q.offset.z] if q.offset else None),
                            ('rotation_matrix', q.rotation_matrix)]:
            if values is not None:
                for expected, actual in zip(values, state[key]): check_setting_value(key, expected, actual)
        return state
    if q.kind == 'thermal_controls':
        owner = context['branch']
        if q.fit_type is not None:
            owner.SetThermalFEAFitType(q.fit_type)
            yield
        boundary()
        if q.working_wavelength is not None:
            owner.SetWorkingWavelength(q.working_wavelength)
            yield
        boundary()
        state = dict(fit_type=int(owner.GetThermalFEAFitType()), working_wavelength=int(owner.GetWorkingWavelength()),
                     primary_wavelength=float(owner.PrimaryWavelengthValue))
        for key in ('fit_type','working_wavelength'):
            if getattr(q,key) is not None: check_setting_value(key, getattr(q,key), state[key])
        return state
    if q.kind == 'volume_controls':
        owner = context['branch']
        if q.grin_step is not None:
            checked_setting(backend.native, owner, 'GRINStep', q.grin_step)
            yield
        boundary()
        if q.fit_grin_step is not None:
            checked_setting(backend.native, owner.Fits, 'GRINStep', q.fit_grin_step)
            yield
        boundary()
        state = dict(grin_step=float(owner.GRINStep), fit_grin_step=float(owner.Fits.GRINStep),
                     unit_source='native GRINStep members; physical step convention requires native acceptance')
        for key in ('grin_step','fit_grin_step'):
            if getattr(q,key) is not None: check_setting_value(key, getattr(q,key), state[key])
        return state
    owner = context['owner']
    if q.kind == 'define_component':
        owner.SetSurfacesInComponent(q.first_surface, q.last_surface)
        yield
        boundary()
        owner = backend._row(q.first_surface).STARData.ComponentRBMs
    elif q.kind == 'remove_component':
        owner.RemoveComponent(q.first_surface)
        yield
        boundary()
    if q.kind != 'remove_component':
        if q.adjust_index_data_with_rbm is not None:
            checked_setting(backend.native, owner, 'AdjustIndexDataWithComponentRBM', q.adjust_index_data_with_rbm)
            yield
        boundary()
        if q.kind == 'component_rbm' and q.action != 'configure':
            if q.action == 'remove_from_fea': owner.RemoveComponentRBMsFromFEADataSets()
            else:
                backend._engineering_mapping_valid = False
                owner.AddComponentRBMsAsCoordinateBreaks()
            yield
            boundary()
            owner = backend._row(int(owner.FirstSurfaceInComponent)).STARData.ComponentRBMs
    state = component_state(owner)
    groups = component_inventory(backend)
    if q.kind == 'define_component':
        expected = {**context['before_components'], q.first_surface:list(range(q.first_surface,q.last_surface+1))}
    elif q.kind == 'remove_component':
        expected = {k:v for k,v in context['before_components'].items() if k != q.first_surface}
    else: expected = context['before_components'] if q.action != 'add_coordinate_breaks' else None
    if expected is not None and groups != expected:
        raise ZemaxError('SETTING_REJECTED', 'STAR component membership differs from requested final groups.',
                         requested=expected, actual=groups)
    if q.kind != 'remove_component':
        if not state['in_component']:
            raise ZemaxError('SETTING_REJECTED', 'STAR component creation or selection was not adopted.')
        if q.adjust_index_data_with_rbm is not None:
            check_setting_value('adjust_index_data_with_rbm',q.adjust_index_data_with_rbm,state['adjust_index_data_with_rbm'])
        if q.kind == 'component_rbm':
            if q.action == 'remove_from_fea': check_setting_value('rbms_removed',True,state['rbms_removed'])
            if q.action == 'add_coordinate_breaks':
                check_setting_value('coordinate_breaks',True,state['coordinate_breaks'])
                if len(groups) != len(context['before_components']) or backend.system.LDE.NumberOfSurfaces <= context['surface_count_before']:
                    raise ZemaxError('SETTING_REJECTED', 'STAR coordinate-break topology change was not confirmed.')
    return dict(component=state, groups=groups, surface_count_before=context['surface_count_before'],
                surface_count_after=int(backend.system.LDE.NumberOfSurfaces))


def run_control(backend, q):
    context = prepare_control(backend, q)
    def flow(task):
        backend._cancel_boundary(task)
        source, work = backend.source_path, backend.work_path
        mode_before = str(backend.system.STARSubsystem.UpdateMode)
        before_context = backend.context()
        backend._mutate('star_' + q.kind)
        snapshot = backend.last_checkpoint
        task['baseline'] = dict(path=snapshot, context=before_context, star_update_mode=mode_before)
        task['payload'] = dict(operation=q.kind, cancellation='cooperative between native calls',
                               resource_ownership='STAR objects owned by the optical system; no separate native tool created')
        try:
            actual = yield from apply_control(backend, q, context, task)
            task['progress'] = 90
            yield
            backend._cancel_boundary(task)
            expected_mode = q.mode if q.kind == 'update_mode' and q.mode is not None else mode_before
            check_mode(backend, expected_mode)
            task['payload'].update(actual=actual, final_context=backend.context(), star_update_mode=expected_mode)
        except Exception as original:
            try:
                backend._restore_model(task, snapshot, source, work)
                check_mode(backend, mode_before, write=True)
            except Exception as restore:
                backend.requires_reconnect = True
                task['restoration'] = dict(restored=False,checkpoint=snapshot,error=backend._evaluation_error(restore))
                raise ZemaxError('STAR_RESTORE_FAILED','STAR control failed and restoration was not confirmed.',
                                 original_error=backend._evaluation_error(original),restoration_error=backend._evaluation_error(restore),
                                 checkpoint=snapshot) from original
            raise
    return backend._composite('star_operation',q.model_dump(),flow)
