"""Biocular matching queries through native BIOC/BIOD operands."""
import math
from typing import Annotated,Literal
from pydantic import Field,model_validator
from .schema import Request,PositiveIndex,FiniteFloat
from .errors import ZemaxError
from .ray_diagrams import native_query

class BiocularConvergence(Request):
    kind: Literal['biocular_dipvergence_convergence']
    left_configuration: PositiveIndex = 1
    right_configuration: PositiveIndex = 2
    wavelength: PositiveIndex = 1
    scan_axis: Literal['X','Y'] = 'Y'
    use_angles: bool = True
    minimum: FiniteFloat = -5
    maximum: FiniteFloat = 5
    offsets: Annotated[list[FiniteFloat],Field(min_length=1,max_length=6)] = Field(default_factory=lambda:[0.])
    points: Annotated[int,Field(strict=True,ge=2,le=1001)] = 21
    convergence_offset_mrad: FiniteFloat = 0

    @model_validator(mode='after')
    def scan_domain(self):
        offsets=[x for x in self.offsets if x!=-99]
        if not offsets:raise ValueError('至少需要一个活动偏移；−99禁用该槽。')
        if self.use_angles:
            if any(abs(x)>=90 for x in [self.minimum,self.maximum,*offsets]):raise ValueError('角度须在−90与90度之间。')
        elif max(abs(self.minimum),abs(self.maximum))**2+max(abs(x)for x in offsets)**2>=1:
            raise ValueError('方向余弦必须满足X²+Y²<1。')
        return self

def validation_rays(b,parent,configuration,rows,q,right,configure=None):
    from types import SimpleNamespace
    from .models import BatchRays
    from .speos import OwnedCopyTool
    copy=b.system.CopySystem()
    if copy is None:raise ZemaxError('COPY_FAILED','双目验证副本创建失败。')
    owned=OwnedCopyTool(copy)
    metadata=dict(configuration=configuration,system_id=int(copy.SystemID),closed=False)
    parent['payload'].setdefault('validation_copies',[]).append(metadata)
    original=None
    try:
        if not copy.MCE.SetCurrentConfiguration(configuration)or int(copy.MCE.CurrentConfiguration)!=configuration:
            raise ZemaxError('SETTING_REJECTED','双目验证副本配置未采用。',configuration=configuration)
        if configure is not None:configure(copy)
        rays=[]
        for row in rows:
            if q.use_angles:tx,ty=math.tan(math.radians(row['x'])),math.tan(math.radians(row['y']))
            else:
                n=math.sqrt(1-row['x']**2-row['y']**2);tx,ty=row['x']/n,row['y']/n
            if right:
                tx=math.tan(math.atan(tx)+row['raw_convergence_mrad']/1000)
                ty=math.tan(math.atan(ty)+row['dipvergence_mrad']/1000)
            n=1/math.sqrt(1+tx*tx+ty*ty)
            rays.append(dict(x=0.,y=0.,z=0.,l=tx*n,m=ty*n,n=n,wavelength=q.wavelength))
        req=BatchRays(input_mode='Direct',start_surface=int(copy.LDE.StopSurface),target_surface=int(copy.LDE.NumberOfSurfaces)-1,rays=rays)
        def release(tool):
            owned.tool=tool;owned.tool_closed=False;b._release_owned(tool);owned.tool_closed=True
        owner=SimpleNamespace(system=copy,native=b.native,_cancel_boundary=b._cancel_boundary,_release_owned=release)
        def launch(_):return b._composite('biocular_validation',dict(configuration=configuration,analysis_system_id=int(copy.SystemID)),lambda t:b._extended_trace_flow.__func__(owner,t,req,req.target_surface))
        result=yield from b._child_job(parent,launch,None)
        return result['rows']
    except BaseException as exc:
        original=exc
        raise
    finally:
        try:b._release_owned(owned);metadata['closed']=True
        except Exception as cleanup:
            b.requires_reconnect=True;metadata['cleanup_error']=str(cleanup)
            if isinstance(original,ZemaxError):original.details['cleanup_error']=str(cleanup)
            elif original is None:raise
            else:raise ZemaxError('CLEANUP_FAILED','双目验证副本未确认关闭。',original_error=b._evaluation_error(original),cleanup_error=str(cleanup))from original


def run_biocular(b,q):
    b._require_sequential();b._require_work()
    count=int(b.system.MCE.NumberOfConfigurations)
    if max(q.left_configuration,q.right_configuration)>count:raise ZemaxError('INDEX_OUT_OF_RANGE','双目配置编号越界。',configuration_count=count)
    if q.wavelength>b.system.SystemData.Wavelengths.NumberOfWavelengths:raise ZemaxError('INDEX_OUT_OF_RANGE','波长编号越界。',wavelength=q.wavelength)
    owner=b.native.api.Editors.MFE.MeritOperandType
    codes={key:b.native.enum(owner,name)for key,name in [('dipvergence_mrad','BIOD'),('raw_convergence_mrad','BIOC')]}
    def flow(task):
        configuration=int(b.system.MCE.CurrentConfiguration);offsets=[x for x in q.offsets if x!=-99]
        task['payload']=dict(analysis_kind=q.kind,computation_method='native_BIOC_BIOD',
            actual_settings=dict(request=q.model_dump(),active_offsets=offsets,configuration=configuration,settings_source='explicit native BIOC/BIOD arguments'),
            scan_unit='degrees'if q.use_angles else'direction cosine',value_unit='milliradians',
            series=[],resource_ownership='native optical system; no independent analysis/tool instance',
            native_assumptions='chief rays launched from STOP center; same image coordinate must represent the same source point in both configurations')
        original=None
        try:
            for offset_index,offset in enumerate(offsets):
                for index in range(q.points):
                    value=q.minimum+(q.maximum-q.minimum)*index/(q.points-1)
                    x,y=(value,offset)if q.scan_axis=='X'else(offset,value)
                    args=[q.left_configuration,q.right_configuration,float(q.wavelength),0. if q.use_angles else 1.,x,y,0.,0.]
                    row=dict(index=len(task['rows']),offset_index=offset_index,offset=offset,scan_value=value,x=x,y=y,native_arguments=args)
                    for key,code in codes.items():
                        b._cancel_boundary(task);row[key]=native_query(b,code,args);yield
                    row.update(convergence_mrad=row['raw_convergence_mrad']-q.convergence_offset_mrad,state='pending_validation')
                    task['rows'].append(row)
                rows=[r for r in task['rows']if r['offset_index']==offset_index]
                left=yield from validation_rays(b,task,q.left_configuration,rows,q,False)
                right=yield from validation_rays(b,task,q.right_configuration,rows,q,True)
                for row,l,r in zip(rows,left,right):
                    row['validation']=dict(left=l,right=r)
                    valid=l['state']==r['state']=='succeeded'
                    if valid:
                        residual=max(abs(l['position'][i]-r['position'][i])for i in (0,1))
                        tolerance=1e-5+1e-6*max(abs(v)for ray in (l,r)for v in ray['position'][:2])
                        row['validation'].update(residual=residual,tolerance=tolerance)
                        valid=residual<=tolerance
                    row['state']='succeeded'if valid else'invalid'
                    row['raw_dipvergence_mrad']=row['dipvergence_mrad']
                    if not valid:row['dipvergence_mrad']=row['convergence_mrad']=None
                task['payload']['series'].append(dict(series=offset_index,description='Biocular offset '+str(offset),
                    labels=['Dipvergence (mrad)','Convergence (mrad)'],x_label=q.scan_axis+' field',x_unit=task['payload']['scan_unit'],
                    y_label='Relative eye angle',y_unit='milliradians',value_units=['milliradians']*2,
                    x=[r['scan_value']for r in rows],y=[[r['dipvergence_mrad'],r['convergence_mrad']]for r in rows]))
            task['summary']=dict(valid=sum(r['state']=='succeeded'for r in task['rows']),invalid=sum(r['state']=='invalid'for r in task['rows']))
            if not task['summary']['valid']:raise ZemaxError('NO_VALID_BIOCULAR_POINTS','双目光线未取得有效且匹配的像点。',summary=task['summary'])
        except BaseException as exc:
            original=exc
            raise
        finally:
            if int(b.system.MCE.CurrentConfiguration)!=configuration:
                if not b.system.MCE.SetCurrentConfiguration(configuration)or int(b.system.MCE.CurrentConfiguration)!=configuration:
                    b.requires_reconnect=True;raise ZemaxError('RESTORE_FAILED','双目查询后当前配置未恢复。',configuration=configuration,original_error=b._evaluation_error(original)if original else None)
    return b._composite(q.kind,q.model_dump(),flow)
