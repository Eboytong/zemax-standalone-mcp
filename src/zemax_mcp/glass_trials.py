"""Catalog-bound glass trials with common native optimization and matrix references."""
import math
from pathlib import Path
from typing import Annotated,Literal

from pydantic import Field,model_validator

from .detectors import check_setting_value
from .errors import ZemaxError
from .glass_reference import glass_contributions
from .schema import FiniteFloat,PositiveIndex,Request


class GlassGroup(Request):
    first_surface: PositiveIndex
    last_surface: PositiveIndex

    @model_validator(mode='after')
    def interval(self):
        if self.last_surface<=self.first_surface:raise ValueError('镜片出面须位于入面之后。')
        return self


class GlassVariable(Request):
    surface: PositiveIndex
    cell: Literal['radius','thickness']
    minimum: FiniteFloat
    maximum: FiniteFloat

    @model_validator(mode='after')
    def interval(self):
        if self.minimum>=self.maximum:raise ValueError('变量下界须小于上界。')
        if self.cell=='radius' and self.minimum<=0<=self.maximum:raise ValueError('半径范围须保持同号并避开零。')
        return self


class GlassObjective(Request):
    metric: Literal['rms_spot','rms_wavefront','effective_focal_length']
    target: FiniteFloat = 0
    weight: Annotated[FiniteFloat,Field(gt=0,le=1e6)] = 1


class GlassTrials(Request):
    kind: Literal['glass_trials']
    groups: Annotated[list[GlassGroup],Field(min_length=1,max_length=30)]
    target_group: Annotated[int,Field(strict=True,ge=0)] = 0
    catalogs: Annotated[list[Annotated[str,Field(min_length=1,max_length=100)]],Field(min_length=1,max_length=10)]
    nd_tolerance: Annotated[FiniteFloat,Field(gt=0,le=2)] = .1
    vd_tolerance: Annotated[FiniteFloat,Field(gt=0,le=200)] = 20
    max_relative_cost: Annotated[FiniteFloat,Field(gt=0)] | None = None
    max_candidates: Annotated[int,Field(strict=True,ge=1,le=30)] = 5
    blue_wavelength: PositiveIndex = 1
    reference_wavelength: PositiveIndex = 2
    red_wavelength: PositiveIndex = 3
    field: PositiveIndex = 2
    rings: Annotated[int,Field(strict=True,ge=1,le=10)] = 3
    mtf_frequency: Annotated[FiniteFloat,Field(gt=0)] = 10
    variables: Annotated[list[GlassVariable],Field(min_length=1,max_length=20)]
    objectives: Annotated[list[GlassObjective],Field(min_length=1,max_length=3)]
    algorithm: Literal['DampedLeastSquares','OrthogonalDescent'] = 'DampedLeastSquares'
    cycles: Literal['Fixed_1_Cycle','Fixed_5_Cycles','Fixed_10_Cycles','Fixed_50_Cycles'] = 'Fixed_10_Cycles'
    budget_per_candidate_seconds: Annotated[FiniteFloat,Field(gt=0,le=3600)] = 120
    save_candidates: bool = True

    @model_validator(mode='after')
    def contract(self):
        if self.target_group>=len(self.groups):raise ValueError('target_group为groups的从0开始编号。')
        if len(set(c.casefold().removesuffix('.agf') for c in self.catalogs))!=len(self.catalogs):raise ValueError('目录重复。')
        if len({(v.surface,v.cell) for v in self.variables})!=len(self.variables):raise ValueError('变量重复。')
        if len({v.metric for v in self.objectives})!=len(self.objectives):raise ValueError('目标指标重复。')
        if len({self.blue_wavelength,self.reference_wavelength,self.red_wavelength})!=3:raise ValueError('三个参考波长须互异。')
        spans=[set(range(g.first_surface,g.last_surface)) for g in self.groups]
        if any(a&c for i,a in enumerate(spans) for c in spans[i+1:]):raise ValueError('玻璃内部段归属不得重叠。')
        return self


def catalog_filter(candidate,baseline,q,wavelengths):
    reasons=[]
    for key,limit in [('nd',q.nd_tolerance),('vd',q.vd_tolerance)]:
        if not math.isfinite(candidate[key]) or abs(candidate[key]-baseline[key])>limit:reasons.append(key+'_range')
    if candidate['exclude_substitution']:reasons.append('excluded_by_catalog')
    if any(not math.isfinite(candidate[k]) for k in ['minimum_wavelength_um','maximum_wavelength_um']) or candidate['minimum_wavelength_um']>min(wavelengths) or candidate['maximum_wavelength_um']<max(wavelengths):reasons.append('wavelength_range')
    if q.max_relative_cost is not None and (candidate['relative_cost'] is None or candidate['relative_cost']>q.max_relative_cost):reasons.append('relative_cost')
    distance=((candidate['nd']-baseline['nd'])/q.nd_tolerance)**2+((candidate['vd']-baseline['vd'])/q.vd_tolerance)**2
    return reasons,distance


def native_value(b,system,code,parameters):
    args=[0.,0.,0.,0.,0.,0.,0.,0.]
    for col,value in parameters.items():args[col-2]=value
    value=float(system.MFE.GetOperandValue(b.native.enum(b.native.api.Editors.MFE.MeritOperandType,code),int(args[0]),int(args[1]),*args[2:]))
    if not math.isfinite(value):raise ZemaxError('INVALID_METRIC','原生评价返回非有限值。',operand=code,value=str(value))
    return value


def common_parameters(system,q):
    fields=system.SystemData.Fields
    if str(fields.Normalization)!='Radial':raise ZemaxError('UNSUPPORTED_FIELD_NORMALIZATION','玻璃试算使用Radial视场归一化。')
    if q.field>int(fields.NumberOfFields):raise ZemaxError('INDEX_OUT_OF_RANGE','评价视场编号越界。')
    maximum=max(math.hypot(float(fields.GetField(i).X),float(fields.GetField(i).Y)) for i in range(1,int(fields.NumberOfFields)+1))
    field=fields.GetField(q.field)
    hx=float(field.X)/maximum if maximum else 0.;hy=float(field.Y)/maximum if maximum else 0.
    return {2:q.rings,3:q.reference_wavelength,4:hx,5:hy}


def performance(b,system,q):
    common=common_parameters(system,q)
    mtf={2:1,3:q.reference_wavelength,4:q.field,5:q.mtf_frequency,6:0,7:0}
    return dict(rms_spot=native_value(b,system,'RSCE',common),rms_wavefront=native_value(b,system,'RWCE',common),
        effective_focal_length=native_value(b,system,'EFFL',{3:q.reference_wavelength}),
        mtf_tangential=native_value(b,system,'MTFT',mtf),mtf_sagittal=native_value(b,system,'MTFS',mtf))


def contributions(b,system,q):
    from System import Array,Double
    if not math.isinf(float(system.LDE.GetSurfaceAt(0).Thickness)) or str(system.SystemData.Fields.GetFieldType())!='Angle':
        raise ZemaxError('UNSUPPORTED_CONTRIBUTION_MODEL','本贡献合同使用无穷远物方和角度视场。')
    count=int(system.SystemData.Wavelengths.NumberOfWavelengths)
    if max(q.blue_wavelength,q.reference_wavelength,q.red_wavelength)>count:raise ZemaxError('INDEX_OUT_OF_RANGE','参考波长编号越界。')
    wavelengths=[float(system.SystemData.Wavelengths.GetWavelength(i).Wavelength) for i in [q.blue_wavelength,q.reference_wavelength,q.red_wavelength]]
    if not wavelengths[0]<wavelengths[1]<wavelengths[2]:raise ZemaxError('INVALID_ARGUMENT','波长须按短波/参考/长波递增。')
    image=int(system.LDE.NumberOfSurfaces)-1;rows=[];indices=[]
    groups=[]
    for g in q.groups:
        if g.last_surface>=image:raise ZemaxError('INDEX_OUT_OF_RANGE','镜片出面须位于像面之前。')
        for i in range(g.first_surface,g.last_surface):
            c=system.LDE.GetSurfaceAt(i).MaterialCell
            if str(c.Solve)!='Fixed':raise ZemaxError('SOLVE_PROTECTED','材料solve须先固定后参与替换试验。',surface=i,solve=str(c.Solve))
        names=[str(system.LDE.GetSurfaceAt(i).Material) for i in range(g.first_surface,g.last_surface)]
        if not names[0] or len(set(names))!=1:raise ZemaxError('INVALID_GLASS_GROUP','镜片内部段须使用同一目录材料。',group=g.model_dump(),materials=names)
        groups.append(g.model_dump()|dict(material=names[0]))
    covered={i for g in q.groups for i in range(g.first_surface,g.last_surface)}
    material_segments={i for i in range(1,image) if str(system.LDE.GetSurfaceAt(i).Material)}
    if covered!=material_segments:raise ZemaxError('INVALID_GLASS_GROUP','groups须完整覆盖系统中的玻璃段。',uncovered=sorted(material_segments-covered),extra=sorted(covered-material_segments))
    for i in range(image):
        row=system.LDE.GetSurfaceAt(i)
        if i:
            if str(row.Type)!='Standard':raise ZemaxError('UNSUPPORTED_CONTRIBUTION_MODEL','当前玻璃贡献使用居中Standard曲面。',surface=i,type=str(row.Type))
            transform=system.LDE.GetGlobalMatrix(i)
            if not transform[0] or any(abs(a-c)>1e-10 for a,c in zip(transform[1:10],[1,0,0,0,1,0,0,0,1])) or any(abs(v)>1e-9 for v in transform[10:12]):
                raise ZemaxError('UNSUPPORTED_CONTRIBUTION_MODEL','玻璃贡献需要同轴曲面。',surface=i)
            radius=float(row.Radius)
            rows.append(dict(curvature=0 if math.isinf(radius) else 1/radius,thickness=float(row.Thickness)))
        values=Array[Double]([0.]*count);n=int(system.LDE.GetIndex(i,count,values))
        if n!=count or any(not math.isfinite(float(v)) or float(v)<=0 for v in values):raise ZemaxError('INVALID_RESULT_DATA','GetIndex返回无效折射率或波长数量。',surface=i)
        indices.append([float(v) for v in values])
    if any(abs(indices[i][q.reference_wavelength-1]-1)>1e-10 for i in [0,image-1]):
        raise ZemaxError('UNSUPPORTED_CONTRIBUTION_MODEL','矩阵贡献采用空气起止。')
    fields=system.SystemData.Fields
    if any(abs(float(fields.GetField(i).X))>1e-12 for i in range(1,int(fields.NumberOfFields)+1)):raise ZemaxError('UNSUPPORTED_CONTRIBUTION_MODEL','色差参考采用Y方向视场。')
    angle=max(float(fields.GetField(i).Y) for i in range(1,int(fields.NumberOfFields)+1))
    result=glass_contributions(rows,[[n[w-1] for n in indices] for w in [q.blue_wavelength,q.reference_wavelength,q.red_wavelength]],groups,int(system.LDE.StopSurface),angle)
    result.update(wavelengths_um=wavelengths,rows=rows,native_indices=indices,
        native_reference=dict(petzval_curvature=native_value(b,system,'PETC',{3:q.reference_wavelength}),
            effective_focal_length=native_value(b,system,'EFFL',{3:q.reference_wavelength}),
            axial_color=native_value(b,system,'AXCL',{2:q.blue_wavelength,3:q.red_wavelength,4:0}),
            lateral_color=native_value(b,system,'LACL',{2:q.blue_wavelength,3:q.red_wavelength})))
    return result


def discover(b,q,baseline_name):
    from .materials import owned_catalog,choose_catalog
    loaded=list(dict.fromkeys(str(v) for v in b.system.SystemData.MaterialCatalogs.GetCatalogsInUse() if str(v).strip()))
    providers=[c for c in loaded if baseline_name in [str(v) for v in b.system.SystemData.MaterialCatalogs.GetMaterialsInCatalog(c)]]
    if len(providers)!=1:raise ZemaxError('AMBIGUOUS_MATERIAL','原材料目录身份不唯一。',material=baseline_name,catalogs=providers)
    def read(tool,catalog,material):
        tool.SelectedCatalog=catalog;tool.SelectedMaterial=material
        check_setting_value('SelectedCatalog',catalog.casefold().removesuffix('.agf'),str(tool.SelectedCatalog).casefold().removesuffix('.agf'))
        check_setting_value('SelectedMaterial',material,str(tool.SelectedMaterial))
        raw_cost=str(tool.RelCost)
        try:cost=float(raw_cost)
        except ValueError:cost=None
        if cost is not None and not math.isfinite(cost):cost=None
        return dict(catalog=str(tool.SelectedCatalog),material=str(tool.SelectedMaterial),nd=float(tool.Nd),vd=float(tool.Vd),
            minimum_wavelength_um=float(tool.MinimumWavelength),maximum_wavelength_um=float(tool.MaximumWavelength),
            relative_cost=cost,relative_cost_raw=raw_cost,exclude_substitution=bool(tool.ExcludeSubstitution),status=str(tool.MaterialStatus))
    with owned_catalog(b) as tool:
        baseline=read(tool,choose_catalog(tool.GetAllCatalogs(),providers[0]),baseline_name)
        candidates=[];rejected=[];scanned=0
        wave=[float(b.system.SystemData.Wavelengths.GetWavelength(i).Wavelength) for i in range(1,int(b.system.SystemData.Wavelengths.NumberOfWavelengths)+1)]
        for wanted in q.catalogs:
            catalog=choose_catalog(tool.GetAllCatalogs(),wanted);tool.SelectedCatalog=catalog
            materials=[str(v) for v in tool.GetAllMaterials()]
            if len(materials)>5000:raise ZemaxError('RESOURCE_LIMIT','目录材料数超过单目录5000上限。',catalog=catalog)
            for material in materials:
                candidate=read(tool,catalog,material);scanned+=1
                reasons,distance=catalog_filter(candidate,baseline,q,wave)
                if candidate['material'].casefold()==baseline_name.casefold():reasons.append('original_material_control')
                candidate.update(distance=distance)
                if reasons:rejected.append(dict(catalog=catalog,material=material,reasons=reasons))
                else:candidates.append(candidate)
    candidates.sort(key=lambda v:(v['distance'],v['catalog'],v['material']))
    return dict(baseline=baseline,selected=candidates[:q.max_candidates],passing_count=len(candidates),scanned=scanned,rejected=rejected,
        selection='ascending squared normalized Nd/Vd distance; requested cap applied after catalog filters')


def run_glass_trials(b,q):
    from .coating_optimization import operand
    from .evaluation import Cancelled
    b._require_sequential(focused=True);b._require_work()
    def flow(task):
        system=None;cleanup_errors=[];copies_created=0;copies_closed=0;operation_error=None
        task['payload']=dict(analysis_kind=q.kind,series=[],grids=[],computation_method='native glass discovery, bounded common native optimization, canonical matrix contribution',
            resources=[],units=dict(rms_spot='lens units',rms_wavefront='waves',effective_focal_length='lens units',mtf='dimensionless'))
        task['restoration']=dict(required=False,restored=True,reason='each trial uses a fresh owned copy; source read-only')
        def close():
            nonlocal system,copies_closed
            if system is None:return
            try:
                if system.Close(False) is False:raise RuntimeError('Close(False) returned false')
                copies_closed+=1
            except Exception as exc:
                b.requires_reconnect=True
                cleanup_errors.append(str(exc))
            finally:system=None
        try:
            b._cancel_boundary(task);system=b.system.CopySystem()
            if system is None:raise ZemaxError('COPY_FAILED','无法创建贡献计算副本。')
            copies_created+=1
            data=contributions(b,system,q);task['payload']['contributions']=data;close()
            if cleanup_errors:raise ZemaxError('CLEANUP_FAILED','贡献计算副本关闭失败。',cleanup_errors=cleanup_errors)
            original=data['groups'][q.target_group]['material'];discovery=discover(b,q,original)
            task['payload']['discovery']=discovery
            candidates=[discovery['baseline']]+discovery['selected']
            if not discovery['selected']:task['payload']['selection_state']='no_replacement_candidates; baseline control retained'
            for index,candidate in enumerate(candidates):
                b._cancel_boundary(task);row=dict(index=index,identity=candidate,control=index==0)
                try:
                    system=b.system.CopySystem()
                    if system is None:raise ZemaxError('COPY_FAILED','无法创建玻璃试验副本。')
                    copies_created+=1
                    catalogs=system.SystemData.MaterialCatalogs
                    loaded=[str(v) for v in catalogs.GetCatalogsInUse() if str(v).strip()]
                    canonical=candidate['catalog'].casefold().removesuffix('.agf')
                    if not any(c.casefold().removesuffix('.agf')==canonical for c in loaded):catalogs.AddCatalog(candidate['catalog'].removesuffix('.AGF'))
                    loaded=list(dict.fromkeys(str(v) for v in catalogs.GetCatalogsInUse() if str(v).strip()))
                    group=q.groups[q.target_group]
                    for i in range(group.first_surface,group.last_surface):
                        s=system.LDE.GetSurfaceAt(i);s.Material=candidate['material'];check_setting_value('Material',candidate['material'],str(s.Material))
                    names={str(system.LDE.GetSurfaceAt(i).Material) for i in range(1,int(system.LDE.NumberOfSurfaces)-1)}-{''}
                    for material in names:
                        providers=[c for c in loaded if material in [str(v) for v in catalogs.GetMaterialsInCatalog(c)]]
                        if len(providers)!=1:raise ZemaxError('AMBIGUOUS_MATERIAL','候选副本的材料目录身份不唯一。',material=material,catalogs=providers)
                    # Fix only existing Variable solves; preserve other solves and protect requested variables.
                    for i in range(int(system.LDE.NumberOfSurfaces)):
                        s=system.LDE.GetSurfaceAt(i)
                        for c in [s.RadiusCell,s.ThicknessCell]:
                            if str(c.Solve)=='Variable':b._set_variable_mode(c,False)
                    mfe=system.MFE;mfe.RemoveOperandsAt(1,int(mfe.NumberOfOperands));common=common_parameters(system,q)
                    codes={'rms_spot':'RSCE','rms_wavefront':'RWCE','effective_focal_length':'EFFL'}
                    for objective in q.objectives:
                        operand(b,mfe,codes[objective.metric],{3:q.reference_wavelength} if objective.metric=='effective_focal_length' else common,objective.target,objective.weight)
                    for variable in q.variables:
                        if variable.surface>=int(system.LDE.NumberOfSurfaces)-1:raise ZemaxError('INDEX_OUT_OF_RANGE','变量面须位于像面之前。')
                        s=system.LDE.GetSurfaceAt(variable.surface);cell=s.RadiusCell if variable.cell=='radius' else s.ThicknessCell
                        b._guard_cell(cell,False);value=float(cell.DoubleValue)
                        if not variable.minimum<=value<=variable.maximum:raise ZemaxError('INVALID_ARGUMENT','起始变量超出请求边界。',variable=variable.model_dump(),value=value)
                        b._set_variable_mode(cell,True)
                        codes_bounds=('CVGT','CVLT') if variable.cell=='radius' else ('CTGT','CTLT')
                        targets=sorted((1/variable.minimum,1/variable.maximum)) if variable.cell=='radius' else (variable.minimum,variable.maximum)
                        for code,target in zip(codes_bounds,targets):
                            operand(b,mfe,code,{2:variable.surface},target,10000)
                    system.UpdateStatus()
                    for i in range(group.first_surface,group.last_surface):check_setting_value('Material',candidate['material'],str(system.LDE.GetSurfaceAt(i).Material))
                    row['actual_settings']=dict(configuration=int(system.MCE.CurrentConfiguration),algorithm=q.algorithm,cycles=q.cycles,number_of_cores=1,
                        optimization_budget_seconds=q.budget_per_candidate_seconds,field=q.field,rings=q.rings,reference_wavelength=q.reference_wavelength,
                        mtf=dict(sampling=1,grid=0,data_type=0,frequency=q.mtf_frequency),
                        merit_operands=[dict(index=i,type=str(mfe.GetOperandAt(i).Type),target=float(mfe.GetOperandAt(i).Target),weight=float(mfe.GetOperandAt(i).Weight)) for i in range(1,int(mfe.NumberOfOperands)+1)])
                    row['before']=performance(b,system,q);row['merit_before']=float(mfe.CalculateMeritFunction())
                    def start(_):
                        tool=system.Tools.OpenLocalOptimization()
                        try:
                            b.native.set_enum(tool,'Algorithm',q.algorithm);b.native.set_enum(tool,'Cycles',q.cycles);tool.NumberOfCores=1
                            check_setting_value('Variables',len(q.variables),int(tool.Variables))
                            def collect(child):
                                if not tool.Succeeded:raise ZemaxError('NATIVE_OPTIMIZATION_FAILED',str(tool.ErrorMessage))
                                return dict(succeeded=True,merit=float(tool.CurrentMeritFunction))
                            return b._start_task('glass_native_optimization',tool,dict(algorithm=str(tool.Algorithm),cycles=str(tool.Cycles),number_of_cores=1,variables=int(tool.Variables)),collector=collect,budget_seconds=q.budget_per_candidate_seconds)
                        except Exception:tool.Close();raise
                    optimized=yield from b._child_job(task,start,None)
                    row['native_optimization']=optimized;row['after']=performance(b,system,q);row['merit_after']=float(mfe.CalculateMeritFunction())
                    row['variables']=[]
                    for v in q.variables:
                        s=system.LDE.GetSurfaceAt(v.surface);actual=float(s.Radius if v.cell=='radius' else s.Thickness)
                        if not math.isfinite(actual) or not v.minimum<=actual<=v.maximum:raise ZemaxError('GLASS_BOUNDS_VIOLATED','优化候选超出请求变量边界。',variable=v.model_dump(),actual=actual)
                        row['variables'].append(v.model_dump()|dict(actual=actual))
                    row['contributions_after']=contributions(b,system,q)
                    if q.save_candidates:
                        path=Path(b.directory)/(task['task_id']+f'_glass_{index}.zos');system.SaveAs(str(path));row['saved_model']=str(path)
                    row['state']='succeeded'
                except Cancelled:raise
                except Exception as exc:
                    row.update(state='failed',error=b._evaluation_error(exc))
                    if b.requires_reconnect:raise
                finally:
                    close();row['copy_closed']=not cleanup_errors
                if cleanup_errors:raise ZemaxError('CLEANUP_FAILED','玻璃试验副本关闭失败。',cleanup_errors=cleanup_errors,operation_error=row.get('error'))
                task['rows'].append(row);yield
            valid=[r for r in task['rows'] if r['state']=='succeeded' and math.isfinite(r['merit_after'])]
            if not valid:raise ZemaxError('NO_VALID_CANDIDATE','原材料及替换候选均未形成有效结果。')
            best=min(valid,key=lambda v:v['merit_after'])
            task['summary']=dict(candidate_count=len(candidates),succeeded=len(valid),failed=len(candidates)-len(valid),
                best_index=best['index'],best_identity=best['identity'],best_model=best.get('saved_model'),best_merit=best['merit_after'])
            control=next((r for r in valid if r['control']),None)
            for row in valid:
                row['change_from_optimized_control']={k:row['after'][k]-control['after'][k] for k in row['after']} if control else None
            task['payload']['series']=[dict(series=0,description='Glass trials native merit',x_label='candidate',x_unit='index',y_unit='native merit',labels=['before','after'],x=[r['index'] for r in valid],y=[[r['merit_before'],r['merit_after']] for r in valid])]
        except BaseException as exc:operation_error=exc;raise
        finally:
            close();task['payload']['resources']=dict(copies_created=copies_created,copies_closed=copies_closed,all_copies_closed=copies_created==copies_closed,cleanup_errors=cleanup_errors)
            if cleanup_errors:raise ZemaxError('CLEANUP_FAILED','玻璃试验副本关闭失败。',cleanup_errors=cleanup_errors,operation_error=b._evaluation_error(operation_error) if operation_error else None)
    return b._composite(q.kind,q.model_dump(),flow)
