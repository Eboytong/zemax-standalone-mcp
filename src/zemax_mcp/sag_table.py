"""Manufacturing sag tables from formal native BFSD/GetSag/SSLP queries."""
import math
from contextlib import contextmanager
from typing import Annotated,Literal
from pydantic import Field,model_validator
from .schema import Request,PositiveIndex,FiniteFloat
from .errors import ZemaxError

class SagTable(Request):
    kind: Literal['sag_table']
    surface: PositiveIndex
    best_fit_sphere: Literal['MinimumVolume','MinimumRMS','MinimumRMSWithOffset'] = 'MinimumVolume'
    reverse: bool = False
    minimum_radius: Annotated[FiniteFloat,Field(ge=0)] = 0
    maximum_radius: Annotated[FiniteFloat,Field(ge=0)] = 0
    samples: Annotated[int,Field(strict=True,ge=2,le=10001)] = 51

    @model_validator(mode='after')
    def range(self):
        if self.reverse and self.best_fit_sphere!='MinimumVolume':
            raise ValueError('reverse仅适用于MinimumVolume。')
        if (self.reverse or self.best_fit_sphere!='MinimumVolume') and (self.minimum_radius or self.maximum_radius):
            raise ValueError('其他准则及反向球面使用原生全口径拟合；半径范围须同时为0。')
        if self.maximum_radius==0 and self.minimum_radius!=0:
            raise ValueError('自动半径范围要求minimum_radius与maximum_radius同时为0。')
        if self.maximum_radius and self.maximum_radius<=self.minimum_radius:
            raise ValueError('maximum_radius须大于minimum_radius。')
        return self

QUANTITIES=['curvature','radius','vertex_offset','maximum_removal_depth','removal_volume',
            'maximum_slope_difference','rms_removal_depth','rms_slope_difference']

def sphere_at(curvature,y):
    root=1-(curvature*y)**2
    if root<0:raise ZemaxError('INVALID_RESULT_DATA','BFS球面在请求半径处没有实数矢高。',curvature=curvature,y=y)
    root=math.sqrt(root)
    if root==0:raise ZemaxError('INVALID_RESULT_DATA','BFS球面在请求半径处斜率无限。',curvature=curvature,y=y)
    return curvature*y*y/(1+root),curvature*y/root


def removal_orientation(summary, samples):
    """Orient removal depth from the native fitted blank and its physical offset."""
    witnesses = []
    for y, sag in samples:
        signed = float(sag) - sphere_at(summary['curvature'], y)[0] - summary['vertex_offset']
        witnesses.append(dict(y=y, signed_depth=signed))
    if not witnesses or any(not math.isfinite(w['signed_depth']) for w in witnesses):
        raise ZemaxError('INVALID_RESULT_DATA', '制造方向缺少有限径向见证。', witnesses=witnesses)
    tolerance = 1e-8 + 1e-6 * abs(summary['maximum_removal_depth'])
    minimum = min(w['signed_depth'] for w in witnesses)
    maximum = max(w['signed_depth'] for w in witnesses)
    if minimum >= -tolerance:
        direction = 1
    elif maximum <= tolerance:
        direction = -1
    else:
        raise ZemaxError('INVALID_RESULT_DATA', '原生制造拟合球在径向见证中交叉曲面，无法确定单一材料去除方向。',
                         witnesses=witnesses, tolerance=tolerance, summary=summary)
    return dict(direction=direction, witnesses=witnesses, tolerance=tolerance,
                source='native BFSD fitted sphere/vertex offset and native GetSag radial witnesses',
                formula='direction*(surface_sag-sphere_sag-native_vertex_offset)',
                coordinate_system='original local surface coordinates; no coordinate-axis reversal',
                zero_depth_state='both directions equivalent within tolerance' if max(abs(minimum), abs(maximum)) <= tolerance else None)

def surface_context(row):
    from .modeling import APERTURE
    aperture=row.ApertureData
    kind=str(aperture.CurrentType)
    settings=getattr(aperture.CurrentTypeSettings,'_S_'+kind)if kind!='None'else None
    return dict(surface_type=str(row.Type),aperture=dict(type=kind,
        pickup_from=int(aperture.PickupFrom)if aperture.IsPickedUp else None,
        **({key:getattr(settings,name)for key,name in APERTURE.items()if hasattr(settings,name)}if settings is not None else{})))


def check_rotational_section(b,surface,lo,hi,task,metadata):
    """Reject a witnessed asymmetric sag; retain the limited scope of sampled checks."""
    for fraction in (.27,.61,.97):
        radius=lo+(hi-lo)*fraction
        reference=None
        for angle in range(0,360,45):
            b._cancel_boundary(task)
            theta=math.radians(angle);x=radius*math.sin(theta);y=radius*math.cos(theta)
            try:ok,sag,alternate=b.system.LDE.GetSag(surface,x,y)
            except Exception as exc:
                raise ZemaxError('NATIVE_ERROR','旋转对称条件的GetSag查询失败。',surface=surface,x=x,y=y,
                    native_exception=str(exc),native_exception_type=type(exc).__name__)from exc
            if not ok or not math.isfinite(sag):
                raise ZemaxError('INVALID_RESULT_DATA','旋转对称条件检查未取得有效矢高。',surface=surface,x=x,y=y,
                    native_success=bool(ok),native_sag=str(sag))
            if reference is None:reference=float(sag)
            error=abs(float(sag)-reference);tolerance=1e-8+1e-6*abs(reference)
            sample=dict(radius=radius,angle_degrees=angle,x=x,y=y,sag=float(sag),
                positive_y_sag=reference,error=error,tolerance=tolerance)
            metadata['samples'].append(sample)
            if error>tolerance:
                metadata['state']='asymmetry_detected'
                raise ZemaxError('UNSUPPORTED_MODEL','SagTable要求绕局部顶点轴旋转对称；已检测到不同方位的矢高不一致。',
                    surface=surface,witness=sample,requirement_source='OpticStudio2024R2 Sag Table: Y-section only; rotationally symmetric surfaces')
            yield
    metadata['state']='sampled_meridians_agree'


@contextmanager
def slope_query_system(b,surface,task,context):
    """Keep native aperture clipping out of the full-blank slope evaluation."""
    if context['aperture']['type']=='None':
        yield b.system
        return
    from .speos import OwnedCopyTool
    copy=b.system.CopySystem()
    if copy is None:raise ZemaxError('COPY_FAILED','SagTable斜率副本创建失败。')
    owned=OwnedCopyTool(copy);original=None
    info=dict(source_aperture=context['aperture'],copy_aperture=None,closed=False)
    task['payload']['slope_query_copy']=info
    try:
        info.update(source_system_id=int(b.system.SystemID),analysis_system_id=int(copy.SystemID))
        configuration=int(b.system.MCE.CurrentConfiguration)
        if int(copy.MCE.CurrentConfiguration)!=configuration:
            if not copy.MCE.SetCurrentConfiguration(configuration):
                raise ZemaxError('SETTING_REJECTED','SagTable斜率副本未采用当前配置。',configuration=configuration)
        if int(copy.MCE.CurrentConfiguration)!=configuration:
            raise ZemaxError('SETTING_REJECTED','SagTable斜率副本配置回读不一致。',configuration=configuration)
        info['configuration']=configuration
        aperture=copy.LDE.GetSurfaceAt(surface).ApertureData
        aperture.SetPickupNone()
        setting=aperture.CreateApertureTypeSettings(b.native.enum(b.native.api.Editors.LDE.SurfaceApertureTypes,'None'))
        changed=aperture.ChangeApertureTypeSettings(setting)
        info['copy_aperture']=str(aperture.CurrentType)
        if changed and info['copy_aperture']=='FloatingAperture':
            # A stop can restore its automatic aperture when None is requested.
            # In the owned slope copy, a checked circle beyond the sampled blank
            # is equivalent for every query in this task's explicit radial domain.
            bounds=task['payload'].get('actual_settings',{}).get('effective_radius_range')
            if bounds and len(bounds)==2 and math.isfinite(bounds[1]) and bounds[1]>0:
                radius=bounds[1]+max(bounds[1],1.)*1e-6
                circle=aperture.CreateApertureTypeSettings(b.native.enum(b.native.api.Editors.LDE.SurfaceApertureTypes,'CircularAperture'))
                values=circle._S_CircularAperture
                values.MinimumRadius=0.
                values.MaximumRadius=radius
                values.ApertureXDecenter=0.
                values.ApertureYDecenter=0.
                changed=aperture.ChangeApertureTypeSettings(circle)
                info.update(copy_aperture=str(aperture.CurrentType),
                    unclipped_method='enclosing_circle_after_native_None_became_FloatingAperture',
                    queried_radius_range=bounds,requested_copy_radius=radius)
                if changed and info['copy_aperture']=='CircularAperture':
                    adopted=aperture.CurrentTypeSettings._S_CircularAperture
                    actual=dict(minimum_radius=float(adopted.MinimumRadius),maximum_radius=float(adopted.MaximumRadius),
                                x_decenter=float(adopted.ApertureXDecenter),y_decenter=float(adopted.ApertureYDecenter))
                    info['actual_copy_circle']=actual
                    if actual!=dict(minimum_radius=0.,maximum_radius=radius,x_decenter=0.,y_decenter=0.):
                        raise ZemaxError('SETTING_REJECTED','SagTable斜率副本包围孔径回读不一致。',requested_radius=radius,actual=actual)
                else:
                    raise ZemaxError('SETTING_REJECTED','SagTable斜率副本未采用包围孔径。',actual=info['copy_aperture'],native_return=bool(changed))
        if not changed or info['copy_aperture']!='None':
            if info.get('unclipped_method') is None:
                raise ZemaxError('SETTING_REJECTED','SagTable斜率副本未清除孔径。',
                    original_aperture=context['aperture'],actual=info['copy_aperture'],native_return=bool(changed))
        yield copy
    except BaseException as exc:
        original=exc
        raise
    finally:
        try:b._release_owned(owned);info['closed']=True
        except Exception as cleanup:
            b.requires_reconnect=True;info['cleanup_error']=str(cleanup)
            if isinstance(original,ZemaxError):original.details['cleanup_error']=str(cleanup)
            elif original is None:raise
            else:raise ZemaxError('CLEANUP_FAILED','SagTable斜率副本关闭失败。',
                original_error=dict(type=type(original).__name__,message=str(original)),cleanup_error=str(cleanup))from original


def run_sag_table(b,q):
    b._require_sequential();b._require_work()
    row=b._row(q.surface)
    lo=q.minimum_radius;hi=q.maximum_radius or float(row.SemiDiameter)
    if hi<=lo or not math.isfinite(hi):raise ZemaxError('INVALID_SETTING','有效半径范围必须正且递增。',minimum=lo,maximum=hi)
    context=surface_context(row)
    native=b.native.api.Editors.MFE.MeritOperandType
    bfs=b.native.enum(native,'BFSD');slope=b.native.enum(native,'SSLP')
    criterion_curve=q.reverse or q.best_fit_sphere!='MinimumVolume'
    def query(code,args,allow_infinite=False,system=None):
        try:value=float((system if system is not None else b.system).MFE.GetOperandValue(code,*args))
        except Exception as exc:raise ZemaxError('NATIVE_ERROR','SagTable原生查询失败。',operand=str(code),arguments=args,native_exception=str(exc),native_exception_type=type(exc).__name__)from exc
        if allow_infinite and math.isinf(value):return None
        if not math.isfinite(value):raise ZemaxError('INVALID_RESULT_DATA','SagTable原生查询返回非有限值。',operand=str(code),arguments=args,value=str(value))
        return value
    def flow(task):
        unit=task['context']['lens_units'];summary={};args=[]
        symmetry=dict(method='native GetSag at3 radii and8 meridians',state='pending',samples=[],
            assumed_geometry='rotationally symmetric sag about local vertex axis',
            check_scope='finite sampled witness check; agreement does not classify every unsampled point')
        task['payload']=dict(analysis_kind=q.kind,computation_method='native_BFSD_GetSag_SSLP',
            actual_settings=dict(request=q.model_dump(),effective_radius_range=[lo,hi],criterion=q.best_fit_sphere,reverse=q.reverse,
                configuration=task['context']['configuration'],settings_source='explicit formal native query arguments',**context),
            units=dict(length=unit,slope='dimensionless',curvature='1/'+unit,volume=unit+'^3'),
            native_query_arguments=args,summary=summary,series=[],
            statistics_sampling=dict(source='native BFSD; summary independent of requested row samples',
                documented_slope_sampling='1000 equally spaced Y points in OpticStudio 2024 R2 help',
                observed_reference=dict(intervals=1000,nodes=1001,
                    coordinates='Y_i = minimum_radius + i*(maximum_radius-minimum_radius)/1000, i=0..1000',
                    rms='sqrt(sum(Y_i*value_i^2)/sum(Y_i))',
                    removal_volume='2*pi*delta_Y*sum(Y_i*removal_depth_i)',
                    validation_scope='positive/negative rotational EvenAspheric and annular range; native518',
                    evidence='verification/development/MF-01/progress519-statistics.json')),
            coordinate_definition='original local surface coordinates x=0,y=positive radial coordinate; manufacturing removal direction recorded separately',
            rotational_symmetry_check=symmetry,
            aperture_interpretation='rows and BFSD summary use the full rotational radial interval; aperture clipping/decenters do not define an area integration mask',
            resource_ownership='native query only; when aperture is present an owned unclipped slope copy is closed before completion',
            slope_definition='native SSLP query slope on full radial blank; aperture-present models use an owned unclipped copy and retain active-model SSLP values',
            scope_status='MinimumVolume native operand path; dedicated SagTable dialog options/readback remain under investigation')
        task['phase']='checking_rotational_section'
        yield from check_rotational_section(b,q.surface,lo,hi,task,symmetry)
        task['phase']='querying_best_fit_sphere'
        if criterion_curve:
            task['payload'].update(computation_method='native_SSAG_GetSag_SSLP_sphere_reconstruction',
                statistics_sampling=dict(source='unavailable for selected criterion; BFSD is MinimumVolume only'),
                scope_status='formal SSAG criterion curve; manufacturing vertex offset and summary unavailable',
                manufacturing_state='unavailable',
                manufacturing_limitation='SSAG removed-sag data piston does not identify the physical manufacturing vertex offset')
            if q.best_fit_sphere!='MinimumVolume':
                task['payload']['manufacturing_state']='not_applicable'
                task['payload']['manufacturing_limitation']='SagTable removal depth/volume summaries apply to MinimumVolume; slope summaries use explicit native SSLP radial sampling'
            ssag=b.native.enum(native,'SSAG')
            flag=3 if q.reverse else {'MinimumRMS':1,'MinimumRMSWithOffset':2}[q.best_fit_sphere]
            probes=[]
            for fraction in (0.,.2,.5,1.):
                b._cancel_boundary(task);y=hi*fraction
                try:ok,sag,unused=b.system.LDE.GetSag(q.surface,0.,y)
                except Exception as exc:raise ZemaxError('NATIVE_ERROR','准则球面识别GetSag失败。',surface=q.surface,y=y,native_exception=str(exc))from exc
                if not ok or not math.isfinite(sag):
                    raise ZemaxError('INVALID_RESULT_DATA','准则球面识别未取得有效矢高。',surface=q.surface,y=y,native_sag=str(sag))
                parameters=[q.surface,1,0.,y,0.,2.,float(flag),0.]
                removed=query(ssag,parameters)
                probes.append((y,float(sag),removed))
                args.append(dict(operand='SSAG',arguments=parameters,value=removed))
                yield
            from .sag_fit import infer_removed_sphere
            fit=infer_removed_sphere(probes,atol=1e-10,rtol=1e-9)
            fixed_offset=q.best_fit_sphere=='MinimumRMS'
            offset_state='fixed_zero_by_criterion'if fixed_offset else'unavailable'
            task['payload']['sphere_reconstruction']=dict(**fit,samples=probes,
                source='formal SSAG BFS flag; reconstructed sphere checked against four native coordinates',
                physical_vertex_offset_state=offset_state)
            summary.update(curvature=fit['curvature'],radius=fit['radius'],vertex_offset=0. if fixed_offset else None,
                vertex_offset_state=offset_state,data_piston=fit['data_piston'])
            if fixed_offset:
                summary['vertex_offset_source']='OpticStudio2024R2 Sag Table: Minimum RMS (No Offset) constrains coincident vertices'
                task['payload']['scope_status']='formal SSAG criterion curve; physical vertex offset fixed zero by MinimumRMS definition'
            if fit['radius'] is None:summary['radius_state']='infinite'
            if not q.reverse:
                dsag=b.native.enum(native,'DSAG');raw={}
                task['payload']['native_bfs_fit']=raw
                raw.update(operand='DSAG',sampling=1,off_axis=0,remove=2,bfs=flag,
                    parameter_columns=['Surf','unused','Data','Samp','Off-axis','Remove','BFS','unused'],
                    offset_definition='OpticStudio2024R2 DSAG Data10: Z Offset of the best-fit sphere vertex from the local coordinate system',
                    offset_interpretation='raw native convention; conversion to SagTable manufacturing vertex_offset unconfirmed',
                    source='formal native operand; separate from SSAG curve reconstruction')
                for data,key in [(9,'radius'),(10,'vertex_z_offset')]:
                    b._cancel_boundary(task)
                    parameters=[q.surface,0,data,1,0,2,flag,0.]
                    value=query(dsag,parameters,allow_infinite=key=='radius')
                    raw[key]=value
                    if key=='radius'and value is None:raw['radius_state']='infinite'
                    args.append(dict(operand='DSAG',quantity=key,arguments=parameters,value=value))
                    yield
                reference=fit['radius'];actual=raw['radius']
                error=abs(actual-reference)if actual is not None and reference is not None else None
                raw['curve_radius_check']=dict(reference_source='four-point SSAG sphere reconstruction',
                    reference=reference,absolute_error=error,absolute_tolerance=5e-6,
                    passed=(actual is None and reference is None)or(error is not None and error<=5e-6))
        for index,key in enumerate([]if criterion_curve else QUANTITIES):
            b._cancel_boundary(task)
            parameters=[q.surface,index,lo,hi,0.,0.,0.,0.]
            summary[key]=query(bfs,parameters,allow_infinite=key=='radius')
            if key=='radius' and summary[key] is None:summary['radius_state']='infinite'
            args.append(dict(operand='BFSD',quantity=key,arguments=parameters))
            yield
        if summary['curvature']==0:summary['curvature_state']='planar'
        direction = 1
        if not criterion_curve:
            samples = [(sample['radius'], sample['sag']) for sample in symmetry['samples'] if sample['angle_degrees'] == 0]
            orientation = removal_orientation(summary, samples)
            task['payload']['manufacturing_direction'] = orientation
            direction = orientation['direction']
        with slope_query_system(b,q.surface,task,context)as slope_system:
            task['phase']='sampling_rows'
            for i in range(q.samples):
                b._cancel_boundary(task);y=lo+(hi-lo)*i/(q.samples-1)
                try:ok,sag,alternate=b.system.LDE.GetSag(q.surface,0.,y)
                except Exception as exc:raise ZemaxError('NATIVE_ERROR','GetSag查询失败。',surface=q.surface,y=y,native_exception=str(exc))from exc
                if not ok or not math.isfinite(sag):raise ZemaxError('INVALID_RESULT_DATA','GetSag未返回有效矢高。',surface=q.surface,y=y,native_success=bool(ok),native_sag=str(sag))
                parameters=[q.surface,1,0.,y,0.,0.,0.,3.]
                active_slope=query(slope,parameters)
                actual_slope=active_slope if slope_system is b.system else query(slope,parameters,system=slope_system)
                bfs_sag,bfs_slope=sphere_at(summary['curvature'],y)
                signed_depth = float(sag)-bfs_sag-summary.get('vertex_offset',0.) if not criterion_curve else None
                if signed_depth is not None and direction*signed_depth < -orientation['tolerance']:
                    raise ZemaxError('INVALID_RESULT_DATA','制造拟合球在输出采样处交叉曲面。',surface=q.surface,y=y,
                        signed_depth=signed_depth,removal_direction=direction,tolerance=orientation['tolerance'])
                task['rows'].append(dict(index=i,y=y,sag=float(sag),bfs_sag=bfs_sag,deviation=float(sag)-bfs_sag,
                    signed_vertex_deviation=signed_depth,
                    removal_depth=None if criterion_curve else direction*signed_depth,slope=actual_slope,bfs_slope=bfs_slope,
                    slope_difference=actual_slope-bfs_slope,native_slope_arguments=parameters,
                    active_model_native_slope=active_slope,
                    slope_source='native_SSLP_active_model'if slope_system is b.system else'native_SSLP_unclipped_copy',state='succeeded'))
                yield
            if criterion_curve:
                sampling=dict(source='explicit native SSLP queries and reconstructed-sphere analytic slope; separate from native BFSD summary',
                    intervals=1000,nodes=1001,completed_nodes=0,
                    coordinates='y_i=lo+i*(hi-lo)/1000,i=0..1000',
                    native_operand='SSLP',native_arguments_template=[q.surface,1,0.,'y_i',0.,0.,0.,3.],
                    maximum='max(abs(surface_slope_i-bfs_slope_i))',
                    rms='sqrt(sum(y_i*(surface_slope_i-bfs_slope_i)^2)/sum(y_i))',
                    aperture_scope='same owned unclipped slope system as row samples',
                    state='running')
                task['payload']['statistics_sampling']=sampling
                weighted=[];weights=[];maximum=0.
                task['phase']='sampling_slope_summary'
                for i in range(1001):
                    b._cancel_boundary(task);y=lo+(hi-lo)*i/1000
                    parameters=[q.surface,1,0.,y,0.,0.,0.,3.]
                    actual_slope=query(slope,parameters,system=slope_system)
                    difference=actual_slope-sphere_at(summary['curvature'],y)[1]
                    weighted.append(y*difference*difference);weights.append(y)
                    maximum=max(maximum,abs(difference));sampling['completed_nodes']=i+1
                    if i%32==0:yield
                summary.update(maximum_slope_difference=maximum,
                    rms_slope_difference=math.sqrt(math.fsum(weighted)/math.fsum(weights)),
                    slope_summary_source='explicit native SSLP radial samples,not native BFSD')
                sampling['state']='succeeded'
        removal_keys=['deviation']if criterion_curve else['deviation','removal_depth']
        for keys,label,units in [(['sag','bfs_sag'],'Sag',[unit,unit]),(removal_keys,'Deviation'if criterion_curve else'Removal',[unit]*len(removal_keys)),
                                  (['slope','bfs_slope','slope_difference'],'Slope',['dimensionless']*3)]:
            task['payload']['series'].append(dict(series=len(task['payload']['series']),description=label,
                labels=[key+' ('+units[j]+')' for j,key in enumerate(keys)],x_label='Local Y',x_unit=unit,
                value_units=units,x=[r['y'] for r in task['rows']],y=[[r[key] for key in keys] for r in task['rows']]))
    return b._composite(q.kind,q.model_dump(),flow)
