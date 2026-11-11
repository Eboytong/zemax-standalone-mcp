"""Two native Huygens paths, unit-power PSFs and finite image-plane pinholes."""
import math
import time
from pathlib import Path
from typing import Annotated,Literal

from pydantic import Field,model_validator

from .data import unwrap
from .detectors import check_setting_value
from .errors import ZemaxError
from .files import input_path
from .schema import Request,FiniteFloat,PositiveIndex

ImageSampling=Literal['S_64x64','S_128x128','S_256x256']
PupilSampling=Literal['S_64x64','S_128x128','S_256x256','S_512x512']


def size(s):return int(s.split('_')[1].split('x')[0])


class ConfocalPath(Request):
    model: Annotated[str,Field(min_length=1,max_length=32767)]
    wavelength: PositiveIndex = 1
    configuration: PositiveIndex = 1


class ConfocalResponse(Request):
    kind: Literal['confocal_response']
    illumination: ConfocalPath
    detection: ConfocalPath
    offsets_mm: Annotated[list[FiniteFloat],Field(min_length=5,max_length=101)]
    pinhole_diameters_um: Annotated[list[Annotated[FiniteFloat,Field(gt=0)]],Field(min_length=1,max_length=10)]
    detection_magnification: FiniteFloat | None = None
    pupil_sampling: PupilSampling = 'S_128x128'
    image_sampling: ImageSampling = 'S_128x128'
    image_delta_um: Annotated[FiniteFloat,Field(gt=0)] = 2
    window_check: bool = True
    budget_seconds: Annotated[FiniteFloat,Field(gt=0,le=3600)] = 600

    @model_validator(mode='after')
    def contract(self):
        if len(set(self.offsets_mm))!=len(self.offsets_mm):raise ValueError('轴向偏移不得重复。')
        if len(set(self.pinhole_diameters_um))!=len(self.pinhole_diameters_um):raise ValueError('针孔直径不得重复。')
        if self.detection_magnification==0:raise ValueError('检测倍率须非零。')
        n=size(self.image_sampling);points=len(set(self.offsets_mm)|{0.})
        if 2*points*n*n*(5 if self.window_check else 1)>8_000_000:raise ValueError('PSF网格计算总量超过8000000点；减小扫描点数或像面网格。')
        return self


def disk_primitive(x,y,r):
    """Signed circle area in the rectangle from the origin to (x,y)."""
    sign=(1 if x>=0 else -1)*(1 if y>=0 else -1)
    x=min(abs(x),r);y=min(abs(y),r)
    if x*x+y*y<=r*r:return sign*x*y
    start=min(x,math.sqrt(max(0.,r*r-y*y)))
    def integral(t):return .5*(t*math.sqrt(max(0.,r*r-t*t))+r*r*math.asin(min(1.,t/r)))
    return sign*(start*y+integral(x)-integral(start))


def disk_pixel_area(x0,x1,y0,y1,r):
    return max(0.,disk_primitive(x1,y1,r)-disk_primitive(x0,y1,r)-disk_primitive(x1,y0,r)+disk_primitive(x0,y0,r))


def grid_metrics(g,diameters):
    nx,ny=g['nx'],g['ny'];dx,dy=g['dx'],g['dy'];values=g['values']
    if dx<=0 or dy<=0 or len(values)!=ny or any(len(row)!=nx for row in values):raise ZemaxError('INVALID_PSF_GRID','PSF尺寸或采样间隔无效。')
    if any(v is None or not math.isfinite(v) or v<0 for row in values for v in row):raise ZemaxError('INVALID_PSF_GRID','PSF包含非有限或负强度。')
    total=math.fsum(v for row in values for v in row)*dx*dy
    if total<=0:raise ZemaxError('EMPTY_PSF','PSF积分为零。')
    fx=-g['min_x']/dx;fy=-g['min_y']/dy;ix=int(math.floor(fx));iy=int(math.floor(fy))
    if not 0<=ix<nx-1 or not 0<=iy<ny-1:raise ZemaxError('PSF_AXIS_OUTSIDE_GRID','光轴不在PSF网格内部。')
    tx=fx-ix;ty=fy-iy
    axis=sum(values[iy+j][ix+i]*((1-tx) if i==0 else tx)*((1-ty) if j==0 else ty) for i in (0,1) for j in (0,1))
    fractions=[]
    edges=(g['min_x']-dx/2,g['min_x']+(nx-.5)*dx,g['min_y']-dy/2,g['min_y']+(ny-.5)*dy)
    for diameter in diameters:
        r=diameter/2
        if not edges[0]<=-r or not edges[1]>=r or not edges[2]<=-r or not edges[3]>=r:
            raise ZemaxError('PINHOLE_OUTSIDE_GRID','完整针孔须位于计算窗口内。',diameter_um=diameter,edges_um=edges)
        integral=0.
        for y in range(max(0,math.ceil((-r-g['min_y'])/dy-.5)),min(ny,math.floor((r-g['min_y'])/dy+.5)+1)):
            cy=g['min_y']+y*dy
            for x in range(max(0,math.ceil((-r-g['min_x'])/dx-.5)),min(nx,math.floor((r-g['min_x'])/dx+.5)+1)):
                cx=g['min_x']+x*dx
                integral+=values[y][x]*disk_pixel_area(cx-dx/2,cx+dx/2,cy-dy/2,cy+dy/2,r)
        fractions.append(dict(diameter_um=diameter,raw_integral_um2=integral,fraction=integral/total))
    return dict(raw_total_um2=total,raw_axis=axis,axis_density_per_um2=axis/total,pinholes=fractions,
                window_edges_um=edges,normalization='unit power over the sampled physical window')


def half_width(x,y):
    peak=max(y)
    if peak<=0:return dict(state='zero_response',fwhm_mm=None,left_mm=None,right_mm=None)
    index=y.index(peak);half=peak/2
    def crossing(indices):
        for a,b in indices:
            if y[b]<=half<=y[a] and y[a]!=y[b]:return x[a]+(x[b]-x[a])*(half-y[a])/(y[b]-y[a])
        return None
    left=crossing((i,i-1) for i in range(index,0,-1));right=crossing((i,i+1) for i in range(index,len(x)-1))
    return dict(state='bracketed' if left is not None and right is not None else 'range_incomplete',
        peak_offset_mm=x[index],peak=peak,left_mm=left,right_mm=right,
        fwhm_mm=right-left if left is not None and right is not None else None)


def prepare(b,system,path,branch,offsets):
    if not system.LoadFile(str(path),False):raise ZemaxError('MODEL_LOAD_FAILED','共焦模型副本加载失败。',path=str(path))
    if str(system.Mode)!='Sequential' or str(system.SystemData.Units.LensUnits)!='Millimeters':raise ZemaxError('UNSUPPORTED_MODEL','共焦模型须为毫米单位顺序系统。')
    if branch.configuration>int(system.MCE.NumberOfConfigurations):raise ZemaxError('INDEX_OUT_OF_RANGE','共焦配置编号越界。')
    system.MCE.SetCurrentConfiguration(branch.configuration)
    check_setting_value('Configuration',branch.configuration,int(system.MCE.CurrentConfiguration))
    if branch.wavelength>int(system.SystemData.Wavelengths.NumberOfWavelengths):raise ZemaxError('INDEX_OUT_OF_RANGE','共焦波长编号越界。')
    field=system.SystemData.Fields.GetField(1)
    if float(field.X)!=0 or float(field.Y)!=0:raise ZemaxError('UNSUPPORTED_FIELD','点样品使用第一视场的轴上位置。')
    if any(abs(float(getattr(field,k)))>1e-12 for k in ['VDX','VDY','VCX','VCY','VAN']):raise ZemaxError('UNSUPPORTED_PUPIL','共焦点样品使用零渐晕变换的圆瞳。')
    if bool(system.SystemData.Aperture.AFocalImageSpace):raise ZemaxError('UNSUPPORTED_MODEL','共焦两路径须为有焦系统。')
    for i in range(1,int(system.LDE.NumberOfSurfaces)-1):
        row=system.LDE.GetSurfaceAt(i)
        if str(row.Type) not in {'Standard','EvenAspheric','Paraxial'} or str(row.Material)=='MIRROR':raise ZemaxError('UNSUPPORTED_MODEL','共焦首批模型采用居中透射Standard/EvenAspheric/Paraxial光路。',surface=i,type=str(row.Type))
        td=row.TiltDecenterData
        if any(abs(float(getattr(td,k)))>1e-12 for k in ['BeforeSurfaceDecenterX','BeforeSurfaceDecenterY','BeforeSurfaceTiltX','BeforeSurfaceTiltY','BeforeSurfaceTiltZ','AfterSurfaceDecenterX','AfterSurfaceDecenterY','AfterSurfaceTiltX','AfterSurfaceTiltY','AfterSurfaceTiltZ']):raise ZemaxError('UNSUPPORTED_MODEL','共焦模型曲面须居中。',surface=i)
    pupil=system.LDE.GetPupil()
    if str(pupil[6])!='None' or float(pupil[7])!=0:raise ZemaxError('UNSUPPORTED_PUPIL','共焦模型使用均匀圆瞳。')
    return dict(path=str(path),configuration=int(system.MCE.CurrentConfiguration),wavelength_um=float(system.SystemData.Wavelengths.GetWavelength(branch.wavelength).Wavelength),
        first_order=list(map(float,system.LDE.GetFirstOrderData())),pupil=dict(entrance_diameter=float(pupil[2]),entrance_position=float(pupil[3]),exit_diameter=float(pupil[4]),exit_position=float(pupil[5])))


def cone(b,system,wavelength,parent):
    """Actual object launch cone; check circular boundary and interior transmission."""
    from System import Int32,Double
    points=[(0.,0.)]+[(r*math.cos(k*math.pi/4),r*math.sin(k*math.pi/4)) for r in (.5,1.) for k in range(8)]
    directions=None
    for target in (0,int(system.LDE.NumberOfSurfaces)-1):
        tool=system.Tools.OpenBatchRayTrace()
        try:
            data=tool.CreateNormUnpol(len(points),b.native.api.Tools.RayTrace.RaysType.Real,target)
            for x,y in points:
                if not data.AddRay(wavelength,0,0,x,y,b.native.enum(b.native.api.Tools.RayTrace.OPDMode,'None')):raise ZemaxError('RAY_REJECTED','共焦孔径见证被拒绝。')
            if not tool.Run():raise ZemaxError('TASK_START_FAILED',str(tool.ErrorMessage))
            while tool.IsRunning:b._cancel_boundary(parent);yield
            tool.WaitForCompletion();b._cancel_boundary(parent)
            if not tool.Succeeded:raise ZemaxError('RAY_TRACE_FAILED',str(tool.ErrorMessage))
            data.StartReadingResults();rows=[]
            while True:
                result=data.ReadNextResult(*([Int32(0)]*3+[Double(0)]*11))
                if not result[0]:break
                if result[2] or result[3]:raise ZemaxError('UNSUPPORTED_PUPIL','共焦圆瞳见证发生追迹错误或截断。',surface=target,error=int(result[2]),vignette=int(result[3]))
                rows.append([float(v) for v in result[7:10]])
            if len(rows)!=len(points):raise ZemaxError('INCOMPLETE_RAYS','共焦圆瞳见证数量不符。')
            if target==0:directions=rows
        finally:b._release_owned(tool)
    if max(abs(directions[0][i]-(1 if i==2 else 0)) for i in range(3))>1e-8:raise ZemaxError('UNSUPPORTED_PUPIL','物方收集锥须以正Z轴为中心。')
    cosines=[v[2] for v in directions[-8:]]
    if max(cosines)-min(cosines)>1e-7:raise ZemaxError('UNSUPPORTED_PUPIL','物方孔径锥未形成圆形边界。',cosines=cosines)
    cosine=sum(cosines)/len(cosines)
    if not 0<cosine<1:raise ZemaxError('INVALID_COLLECTION_CONE','有限物距收集锥无效。')
    return dict(cos_half_angle=cosine,solid_angle_sr=2*math.pi*(1-cosine),isotropic_fraction=(1-cosine)/2,
                angular_radius_deg=math.degrees(math.acos(cosine)),witnesses=len(points),definition='native object-space launch cone, uniform isotropic point emitter')


def run_confocal_response(b,q):
    from .analyses import scalar_settings
    from .imaging import checked,check
    b._require_work()
    paths=[input_path(s.model,{'.zos','.zmx'}) for s in [q.illumination,q.detection]]
    offsets=sorted(set(q.offsets_mm)|{0.});order=[0.]+[v for v in offsets if v!=0.]
    def flow(task):
        systems=[];cleanup=[];error=None;started=time.monotonic();cases=[]
        task['payload']=dict(analysis_kind=q.kind,series=[],grids=[],models=[],cases=cases,
            sample='on-axis isotropic point fluorescence; constant incident power',
            coordinates='positive sample shift increases illumination image gap and decreases detection object gap',
            units=dict(offset='mm',pinhole='micrometers',density='1/micrometers^2',response='relative'))
        task['restoration']=dict(required=False,restored=True,reason='two owned input-model copies; source remains unchanged')
        try:
            rows=[]
            for j,(branch,path) in enumerate(zip([q.illumination,q.detection],paths)):
                system=b.system.CopySystem()
                if system is None:raise ZemaxError('COPY_FAILED','共焦模型副本创建失败。')
                systems.append(system)
                metadata=prepare(b,system,path,branch,offsets);task['payload']['models'].append(metadata)
                row=system.LDE.GetSurfaceAt(int(system.LDE.NumberOfSurfaces)-2 if j==0 else 0)
                b._guard_cell(row.ThicknessCell)
                base=float(row.Thickness)
                if not math.isfinite(base) or min(base+z*(1 if j==0 else -1) for z in offsets)<=0:raise ZemaxError('INVALID_SAMPLE_RANGE','样品偏移须保持两侧空气间隔为有限正数。',branch=j)
                if j==0 and str(row.Material) not in {'','-'}:raise ZemaxError('UNSUPPORTED_MEDIUM','样品平面前使用空气。')
                rows.append((row,base))
            geometry=[[(float(s.LDE.GetSurfaceAt(i).Radius),float(s.LDE.GetSurfaceAt(i).Thickness),str(s.LDE.GetSurfaceAt(i).Material))
                for i in range(int(s.LDE.NumberOfSurfaces))] for s in systems]
            mag=task['payload']['models'][1]['first_order'][4]
            if q.detection_magnification is not None:check_setting_value('detection_magnification',q.detection_magnification,mag)
            task['payload']['nominal_detection_magnification']=mag
            for z in order:
                b._cancel_boundary(task)
                if time.monotonic()-started>q.budget_seconds:raise ZemaxError('BUDGET_EXCEEDED','共焦扫描预算已用完。')
                case=dict(offset_mm=z,paths=[]);cases.append(case)
                for j,(system,branch,(row,base)) in enumerate(zip(systems,[q.illumination,q.detection],rows)):
                    row.Thickness=base+z*(1 if j==0 else -1);system.UpdateStatus()
                    check_setting_value('sample_gap',base+z*(1 if j==0 else -1),float(row.Thickness))
                    moving=int(system.LDE.NumberOfSurfaces)-2 if j==0 else 0
                    for i,(radius,thickness,material) in enumerate(geometry[j]):
                        current=system.LDE.GetSurfaceAt(i)
                        if float(current.Radius)!=radius or str(current.Material)!=material or (i!=moving and float(current.Thickness)!=thickness):
                            raise ZemaxError('DEPENDENT_MODEL_CHANGE','样品扫描触发其他曲面参数变化。',branch=j,surface=i)
                    result=dict(actual_gap_mm=float(row.Thickness),first_order=list(map(float,system.LDE.GetFirstOrderData())))
                    if j==1:result['collection']=yield from cone(b,system,branch.wavelength,task)
                    for larger in ([False,True] if q.window_check else [False]):
                        sampling=q.image_sampling if not larger else 'S_'+str(2*size(q.image_sampling))+'x'+str(2*size(q.image_sampling))
                        def start(_):
                            analyses=system.Analyses
                            factory=getattr(analyses,'New_Analysis_SettingsFirst',analyses.New_Analysis)
                            tool=factory(b.native.api.Analysis.AnalysisIDM.HuygensPsf)
                            try:
                                s=unwrap(tool.GetSettings())
                                desired=dict(PupilSampleSize=q.pupil_sampling,ImageSampleSize=sampling,Type='Linear',Normalize=False,UseCentroid=False,UsePolarization=False,ImageDelta=q.image_delta_um,Configuration=branch.configuration)
                                s.Field.SetFieldNumber(1);s.Wavelength.SetWavelengthNumber(branch.wavelength)
                                for key,value in desired.items():checked(b.native,s,key,value)
                                for key,value in desired.items():check(b.native,s,key,value)
                                check_setting_value('Field',1,int(s.Field.GetFieldNumber()));check_setting_value('Wavelength',branch.wavelength,int(s.Wavelength.GetWavelengthNumber()))
                                settings=dict(kind='huygens_psf',requested=dict(field=1,wavelength=branch.wavelength,normalize=False),native=scalar_settings(s))
                                return b._start_task('confocal_huygens_psf',tool,settings,analysis=True,collector=b._collect_general_analysis,budget_seconds=min(60.,max(.001,q.budget_seconds-(time.monotonic()-started))))
                            except Exception:b._release_owned(tool);raise
                        native=yield from b._child_job(task,start,None)
                        if len(native.get('grids',[]))!=1:raise ZemaxError('INVALID_PSF_GRID','Huygens PSF须返回一个网格。')
                        grid=native['grids'][0];metrics=grid_metrics(grid,q.pinhole_diameters_um if j==1 else [])
                        result['wide' if larger else 'primary']=metrics|dict(task_id=native['task']['task_id'],actual_settings=native['task']['settings'])
                        if not larger:
                            grid=dict(grid,grid=len(task['payload']['grids']),description=f'{"illumination" if j==0 else "detection"} z={z:g} mm, unit captured power',
                                values=[[v/metrics['raw_total_um2'] for v in line] for line in grid['values']],value_unit='1/micrometers^2')
                            result['grid']=grid['grid'];task['payload']['grids'].append(grid)
                    case['paths'].append(result)
                task['progress']=int(100*len(cases)/len(order));yield
            cases.sort(key=lambda c:c['offset_mm']);baseline=next(c for c in cases if c['offset_mm']==0)
            curves=[]
            for i,diameter in enumerate(q.pinhole_diameters_um):
                quantities={}
                for mode in (['primary','wide'] if q.window_check else ['primary']):
                    raw=[c['paths'][0][mode]['axis_density_per_um2']*c['paths'][1][mode]['pinholes'][i]['fraction']*c['paths'][1]['collection']['isotropic_fraction'] for c in cases]
                    at_zero=raw[offsets.index(0.)]
                    if at_zero<=0:raise ZemaxError('ZERO_REFERENCE','共焦零离焦参考响应为零。')
                    relative=[v/at_zero for v in raw];quantities[mode]=dict(relative=relative,width=half_width(offsets,relative))
                data=quantities['primary'];curve=dict(diameter_um=diameter,**data)
                if q.window_check:
                    wide=quantities['wide'];difference=max(abs(a-b) for a,b in zip(data['relative'],wide['relative']))
                    w0,w1=data['width']['fwhm_mm'],wide['width']['fwhm_mm'];delta=abs(w0-w1)/w1 if w0 is not None and w1 else None
                    curve['window_check']=dict(max_response_difference=difference,fwhm_relative_difference=delta,wide=wide,
                        state='converged' if difference<=.005 and delta is not None and delta<=.01 else 'refine_window_or_scan')
                curves.append(curve)
                for k,c in enumerate(cases):
                    illum=c['paths'][0]['primary']['axis_density_per_um2'];fraction=c['paths'][1]['primary']['pinholes'][i]['fraction']
                    task['rows'].append(dict(offset_mm=c['offset_mm'],pinhole_diameter_um=diameter,illumination_density_per_um2=illum,
                        detection_pinhole_fraction=fraction,isotropic_collection_fraction=c['paths'][1]['collection']['isotropic_fraction'],
                        relative_response=data['relative'][k],normalized_to_peak=data['relative'][k]/max(data['relative'])))
            task['payload']['series']=[dict(series=0,description='Point fluorescence confocal response',x_label='sample offset',x_unit='mm',y_unit='relative to zero offset',
                labels=[f'{d:g} um pinhole' for d in q.pinhole_diameters_um],x=offsets,y=[[c['relative'][i] for c in curves] for i in range(len(offsets))])]
            task['summary']=dict(curves=curves,offset_count=len(offsets),nominal_detection_magnification=mag,
                normalization='each physical PSF window has unit captured power; response includes native object launch solid angle; relative to zero offset',
                collection_scope='uniform isotropic emitter into unobscured circular object launch cone; normalized optical transfer per collected power',
                window_check=q.window_check,elapsed_seconds=time.monotonic()-started)
        except BaseException as exc:error=exc;raise
        finally:
            for system in reversed(systems):
                try:
                    if system.Close(False) is False:raise RuntimeError('Close(False) returned false')
                except Exception as exc:cleanup.append(str(exc));b.requires_reconnect=True
            task['payload']['resources']=dict(copies_created=len(systems),copies_closed=len(systems)-len(cleanup),all_copies_closed=not cleanup,cleanup_errors=cleanup)
            if cleanup:raise ZemaxError('CLEANUP_FAILED','共焦模型副本关闭失败。',cleanup_errors=cleanup,operation_error=b._evaluation_error(error) if error else None)
    return b._composite(q.kind,q.model_dump(),flow,require_sequential=False)
