"""Auditable native merit programs evaluated on owned optical-system copies."""
import math
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .data import unwrap
from .detectors import check_setting_value
from .errors import ZemaxError
from .schema import Request, FiniteFloat, PositiveIndex
from .wizard_models import SequentialWizard, WIZARD_FIELDS


class OpdTarget(Request):
    kind: Literal['opd']
    reference: Literal['chief_ray', 'mean', 'mean_remove_tilt'] = 'mean_remove_tilt'
    configuration: PositiveIndex = 1
    wavelength: PositiveIndex = 1
    hx: Annotated[FiniteFloat, Field(ge=-1, le=1)] = 0
    hy: Annotated[FiniteFloat, Field(ge=-1, le=1)] = 0
    rings: Annotated[int, Field(strict=True, ge=2, le=32)] = 4
    arms: Annotated[int, Field(strict=True, ge=8, le=128)] = 16
    obscuration: Annotated[FiniteFloat, Field(ge=0, lt=1)] = 0
    target_waves: FiniteFloat = 0
    scale_waves: Annotated[FiniteFloat, Field(gt=0)] = 1
    weight: Annotated[FiniteFloat, Field(gt=0, le=1e9)] = 1


class MeritConstraint(Request):
    operand: Literal['CTGT', 'CTLT', 'CVGT', 'CVLT', 'ETGT', 'ETLT', 'EFFL']
    surface: PositiveIndex | None = None
    wavelength: PositiveIndex = 1
    target: FiniteFloat
    scale: Annotated[FiniteFloat, Field(gt=0)] = 1
    weight: Annotated[FiniteFloat, Field(gt=0, le=1e9)] = 1

    @model_validator(mode='after')
    def identity(self):
        if self.operand == 'EFFL' and self.surface is not None:
            raise ValueError('EFFL使用波长选择。')
        if self.operand != 'EFFL' and self.surface is None:
            raise ValueError('几何约束需要曲面编号。')
        return self


class MeritProgram(Request):
    apply: bool = False
    wizard: SequentialWizard | None = None
    targets: Annotated[list[OpdTarget], Field(max_length=30)] = Field(default_factory=list)
    constraints: Annotated[list[MeritConstraint], Field(max_length=200)] = Field(default_factory=list)

    @model_validator(mode='after')
    def useful(self):
        if not self.wizard and not self.targets and not self.constraints:
            raise ValueError('至少提供向导、波前目标或约束。')
        return self


def gauss_nodes(count):
    """Gauss-Legendre nodes and weights on [0,1], using Newton iteration."""
    pairs = []
    for i in range(1, count + 1):
        x = math.cos(math.pi * (i - .25) / (count + .5))
        for _ in range(50):
            p0, p1 = 1., x
            for j in range(2, count + 1):
                p0, p1 = p1, ((2*j-1)*x*p1-(j-1)*p0)/j
            derivative = count*(x*p1-p0)/(x*x-1)
            delta = p1/derivative
            x -= delta
            if abs(delta) < 1e-15:
                break
        pairs.append(((x+1)/2, 1/((1-x*x)*derivative*derivative)))
    return sorted(pairs)


def pupil_nodes(q):
    """Equal-angle complete annulus; u=r^2 has uniform area measure."""
    return [dict(px=math.sqrt(q.obscuration**2+(1-q.obscuration**2)*u)*math.cos(2*math.pi*j/q.arms),
                 py=math.sqrt(q.obscuration**2+(1-q.obscuration**2)*u)*math.sin(2*math.pi*j/q.arms),
                 area_weight=w/q.arms)
            for u, w in gauss_nodes(q.rings) for j in range(q.arms)]


def native_rows_steps(b, system):
    rows = []
    for i in range(1, int(system.MFE.NumberOfOperands)+1):
        row = system.MFE.GetOperandAt(i)
        rows.append(dict(operand=i, type=str(row.Type), target=float(row.Target),
            weight=float(row.Weight), value=float(row.Value), contribution=float(row.Contribution),
            parameters={str(j):dict(header=str(row.GetCellAt(j).Header), value=b._cell_value(row.GetCellAt(j)))
                        for j in range(2, 10) if row.GetCellAt(j).IsActive}))
        if i % 16 == 0:yield
    return rows


def drain(steps):
    while True:
        try:next(steps)
        except StopIteration as done:return done.value


def native_rows(b, system):
    return drain(native_rows_steps(b, system))


def build(b, system, q):
    return drain(build_steps(b, system, q))


def build_steps(b, system, q):
    from .coating_optimization import operand
    from .analyses import scalar_settings, native_setting
    from .wizards import conditions, check_value
    mfe = system.MFE
    mfe.RemoveOperandsAt(1, int(mfe.NumberOfOperands))
    settings = None
    if q.wizard:
        wizard = unwrap(mfe.SEQOptimizationWizard2)
        wizard.CommonSettings.ResetSettings()
        values = {native:getattr(q.wizard, key) for key, native in WIZARD_FIELDS['sequential'].items()
                  if key in q.wizard.model_fields_set}
        for a, c in [('UseGaussianQuadrature', 'UseRectangularArray'),
                     ('OptimizeForBestNominalPerformance', 'OptimizeForManufacturingYield')]:
            if values.get(a) is True and c not in values:values[c] = False
            if values.get(c) is True and a not in values:values[a] = False
        conditions('sequential', scalar_settings(wizard)|values, values, system)
        for name in sorted(values, key=lambda n:0 if isinstance(values[n],bool) else 1):
            native_setting(b.native, wizard, name, values[name])
        for name, value in values.items():check_value(b.native, wizard, name, value)
        settings = scalar_settings(wizard)
        conditions('sequential', settings, values, system)
        wizard.CommonSettings.Apply()
    groups = []
    for index, target in enumerate(q.targets):
        if target.configuration > int(system.MCE.NumberOfConfigurations):
            raise ZemaxError('INDEX_OUT_OF_RANGE', '目标配置超出范围。', target=index)
        if target.wavelength > int(system.SystemData.Wavelengths.NumberOfWavelengths):
            raise ZemaxError('INDEX_OUT_OF_RANGE', '目标波长超出范围。', target=index)
        operand(b, mfe, 'CONF', {2:target.configuration})
        code = dict(chief_ray='OPDC', mean='OPDM', mean_remove_tilt='OPDX')[target.reference]
        nodes = pupil_nodes(target)
        start = int(mfe.NumberOfOperands)+1
        for node_index, node in enumerate(nodes, 1):
            number = operand(b, mfe, code, {3:target.wavelength, 4:target.hx, 5:target.hy,
                6:node['px'], 7:node['py']}, target.target_waves,
                node['area_weight']*target.weight/target.scale_waves**2)
            row = mfe.GetOperandAt(number)
            for column, expected in {3:target.wavelength, 4:target.hx, 5:target.hy, 6:node['px'], 7:node['py']}.items():
                cell = row.GetCellAt(column)
                if not cell.IsActive:
                    raise ZemaxError('UNSUPPORTED_INTERFACE', 'OPD参数列不可用。', operand=code, column=column)
                check_setting_value('OPD parameter '+str(column), expected, b._cell_value(cell))
            if node_index % 16 == 0:yield
        groups.append(dict(index=index, source='native '+code, request=target.model_dump(),
                           start=start, count=len(nodes), nodes=nodes, unit='waves'))
        separator = mfe.AddOperand()
        separator.ChangeType(b.native.enum(b.native.api.Editors.MFE.MeritOperandType, 'BLNK'))
    operand(b, mfe, 'CONF', {2:int(system.MCE.CurrentConfiguration)})
    constraint_rows = []
    for constraint in q.constraints:
        if constraint.surface and constraint.surface >= int(system.LDE.NumberOfSurfaces)-1:
            raise ZemaxError('INDEX_OUT_OF_RANGE', '几何约束曲面须位于像面之前。')
        if constraint.wavelength > int(system.SystemData.Wavelengths.NumberOfWavelengths):
            raise ZemaxError('INDEX_OUT_OF_RANGE', '约束波长超出范围。')
        parameters = {3:constraint.wavelength} if constraint.operand == 'EFFL' else {2:constraint.surface}
        number = operand(b, mfe, constraint.operand, parameters,
                         constraint.target, constraint.weight/constraint.scale**2)
        constraint_rows.append(dict(operand=number, request=constraint.model_dump(),
            unit='inverse lens units' if constraint.operand.startswith('CV') else 'lens units'))
    return settings, groups, constraint_rows


def run_program(b, q):
    b._require_sequential(focused=True)
    b._require_work()
    def flow(task):
        system = None
        original_error = None
        task['payload'] = dict(applied=False, source='ZOS-API native MFE', series=[], grids=[])
        try:
            yield
            b._cancel_boundary(task)
            system = b.system.CopySystem()
            if system is None:raise ZemaxError('COPY_FAILED', '评价函数工作副本创建失败。')
            def advance(steps):
                while True:
                    b._cancel_boundary(task)
                    try:next(steps)
                    except StopIteration as done:return done.value
                    yield
            settings, groups, constraint_rows = yield from advance(build_steps(b, system, q))
            merit = float(system.MFE.CalculateMeritFunction())
            if not math.isfinite(merit):raise ZemaxError('INVALID_RESULT_DATA', '原生评价函数返回非有限值。')
            task['rows'] = yield from advance(native_rows_steps(b, system))
            for group in groups:
                values = [task['rows'][i-1]['value'] for i in range(group['start'], group['start']+group['count'])]
                if any(not math.isfinite(v) for v in values):
                    raise ZemaxError('INVALID_RESULT_DATA', 'OPD组包含无效光线。', group=group['index'])
                goal = group['request']
                mse = sum(n['area_weight']*(v-goal['target_waves'])**2 for n,v in zip(group['nodes'],values))
                group.update(rms_residual_waves=math.sqrt(mse), normalized_contribution=goal['weight']*mse/goal['scale_waves']**2)
            for constraint in constraint_rows:
                row = task['rows'][constraint['operand']-1]
                value, target = row['value'], constraint['request']['target']
                code = constraint['request']['operand']
                residual = max(0.,target-value) if code.endswith('GT') else max(0.,value-target) if code.endswith('LT') else abs(value-target)
                constraint.update(value=value, violation=residual,
                    normalized_contribution=constraint['request']['weight']*(residual/constraint['request']['scale'])**2)
            task['payload'].update(wizard_settings=settings, groups=groups, constraints=constraint_rows,
                native_merit=merit, native_weight_definition='area_weight * requested_weight / scale^2; native merit uses its own total-weight normalization')
            yield
            b._cancel_boundary(task)
            if q.apply:
                path = Path(b.directory)/(task['task_id']+'_merit.zos')
                system.SaveAs(str(path))
                b._mutate('merit_program')
                snapshot, source, work = b.last_checkpoint, b.source_path, b.work_path
                try:
                    if not b.system.LoadFile(str(path), False):raise ZemaxError('LOAD_FAILED', '评价函数模型应用失败。')
                    b.system.SaveAs(str(work))
                    task['payload']['applied'] = True
                    task['payload']['checkpoint'] = snapshot
                    task['context'] = b.context()
                except Exception:
                    b._restore_model(task, snapshot, source, work)
                    raise
            task['summary'] = dict(applied=q.apply, operand_count=len(task['rows']), native_merit=merit,
                target_count=len(groups), constraint_count=len(constraint_rows))
        except BaseException as exc:
            original_error = exc
            raise
        finally:
            if system is not None:
                try:
                    if system.Close(False) is False:raise RuntimeError('Close(False) returned false')
                    task['payload']['copy_closed'] = True
                except Exception as exc:
                    b.requires_reconnect = True
                    task['payload']['copy_closed'] = False
                    raise ZemaxError('CLEANUP_FAILED', '评价函数副本关闭失败。', reason=str(exc),
                        operation_error=b._evaluation_error(original_error) if original_error else None) from exc
    return b._composite('merit_program', q.model_dump(), flow)
