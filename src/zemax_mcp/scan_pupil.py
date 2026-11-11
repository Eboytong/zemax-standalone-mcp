"""Owned sequential scanner sweeps and real-ray differential pupil conjugates."""
import math
from pathlib import Path
from typing import Annotated,Literal

from pydantic import Field,model_validator

from .detectors import check_setting_value
from .errors import ZemaxError
from .rays import RaysMixin
from .schema import FiniteFloat,PositiveIndex,Request


class ScannerSpacing(Request):
    surface: PositiveIndex
    values: Annotated[list[FiniteFloat],Field(min_length=1,max_length=20)]


class ScanPupil(Request):
    kind: Literal['scan_pupil']
    start_surface: PositiveIndex
    tilt_surface: PositiveIndex
    mirror_surface: PositiveIndex
    return_surface: PositiveIndex
    pupil_surface: PositiveIndex
    image_surface: PositiveIndex
    axis: Literal['X','Y'] = 'Y'
    angles_deg: Annotated[list[Annotated[FiniteFloat,Field(ge=-15,le=15)]],Field(min_length=1,max_length=61)] = [-1,0,1]
    beam_radius: Annotated[FiniteFloat,Field(gt=0)] = 1
    beam_center_x: FiniteFloat = 0
    beam_center_y: FiniteFloat = 0
    ray_density: Annotated[int,Field(strict=True,ge=3,le=21)] = 9
    wavelength: PositiveIndex = 1
    probe_height: Annotated[FiniteFloat,Field(gt=0,le=1)] = .001
    probe_slope: Annotated[FiniteFloat,Field(gt=0,le=.01)] = .00001
    spacing: ScannerSpacing | None = None
    save_best: bool = True

    @model_validator(mode='after')
    def contract(self):
        if self.tilt_surface!=self.start_surface+1 or self.mirror_surface!=self.tilt_surface+1 or self.return_surface!=self.mirror_surface+1:
            raise ValueError('输入面、前断点、镜面、后断点须按序排列，三个扫描面相邻。')
        if not self.return_surface<self.pupil_surface<=self.image_surface:raise ValueError('目标瞳面及像面须位于后断点之后。')
        if len(set(self.angles_deg))!=len(self.angles_deg):raise ValueError('扫描角不得重复。')
        if self.ray_density%2==0:raise ValueError('ray_density须为奇数。')
        if self.spacing and not self.return_surface<=self.spacing.surface<self.pupil_surface:raise ValueError('间距变量须位于后断点至目标瞳面之前。')
        if self.spacing and len(set(self.spacing.values))!=len(self.spacing.values):raise ValueError('间距采样不得重复。')
        if len(self.spacing.values if self.spacing else [None])*len(set(self.angles_deg)|{0})*self.ray_density**2*3>250000:
            raise ValueError('扫描网格须满足间距数×角度数×ray_density²×3≤250000。')
        return self


def rotate(transform,vector):
    return [sum(transform[1+3*i+j]*vector[j] for j in range(3)) for i in range(3)]


def global_ray(transform,row,parity):
    position=rotate(transform,row['position'])
    return dict(position=[v+transform[10+i] for i,v in enumerate(position)],
        direction=[parity*v for v in rotate(transform,row['direction'])])


def reflect(direction,normal):
    dot=sum(a*c for a,c in zip(direction,normal))
    return [a-2*dot*c for a,c in zip(direction,normal)]


def inverse(matrix):
    n=len(matrix);a=[list(row)+[float(i==j) for j in range(n)] for i,row in enumerate(matrix)]
    for i in range(n):
        pivot=max(range(i,n),key=lambda r:abs(a[r][i]))
        if abs(a[pivot][i])<1e-14:raise ZemaxError('DEGENERATE_PUPIL_PROBES','光线状态矩阵退化。')
        a[i],a[pivot]=a[pivot],a[i];scale=a[i][i];a[i]=[v/scale for v in a[i]]
        for r in range(n):
            if r!=i:
                scale=a[r][i];a[r]=[v-scale*w for v,w in zip(a[r],a[i])]
    return [row[n:] for row in a]


def ray_state(row):
    if row['error_code'] or row.get('vignette_code') or not row.get('direction') or abs(row['direction'][2])<1e-8:
        raise ZemaxError('INVALID_PUPIL_PROBE','差分光线未通过系统或方向退化。',ray=row)
    return row['position'][:2]+[v/row['direction'][2] for v in row['direction'][:2]]


def conjugates(mirror_rows,target_rows):
    def differences(rows):
        states=[ray_state(r) for r in rows]
        return [[(states[1+2*j][i]-states[2+2*j][i])/2 for j in range(4)] for i in range(4)]
    mi=inverse(differences(mirror_rows));output=differences(target_rows)
    matrix=[[sum(output[i][k]*mi[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
    axes=[]
    for axis in range(2):
        a,b,c,d=matrix[axis][axis],matrix[axis][axis+2],matrix[axis+2][axis],matrix[axis+2][axis+2]
        distance=-b/d if abs(d)>1e-12 else None
        cross=max(abs(matrix[i][j]) for i in [axis,axis+2] for j in [1-axis,3-axis])
        axes.append(dict(axis='XY'[axis],a=a,b=b,c=c,d=d,signed_local_z_to_conjugate=distance,
            magnification=a+distance*c if distance is not None else None,cross_axis_max=cross,
            signed_local_z_of_aperture_preimage=b/a if abs(a)>1e-12 else None,
            aperture_preimage_magnification=1/a if abs(a)>1e-12 else None,
            state='coupled' if cross>1e-6 else 'finite' if distance is not None else 'infinite'))
    return dict(matrix=matrix,axes=axes,state_order=['x','y','l/n','m/n'],
        definition='central real-ray differential map from mirror outgoing local plane to target outgoing local plane; target conjugate of mirror z=-B/D; aperture preimage at mirror-side z=B/A and magnification 1/A')


def footprint(rows):
    good=[r for r in rows if not r.get('error_code') and not r.get('vignette_code') and r.get('position')]
    center=[sum(r['position'][i] for r in good)/len(good) for i in range(2)] if good else None
    return dict(requested=len(rows),passed=len(good),throughput=len(good)/len(rows) if rows else None,
        vignetted=sum(bool(r.get('vignette_code')) for r in rows),errors=sum(bool(r.get('error_code')) for r in rows),
        center=center,rms_radius=math.sqrt(sum(sum((r['position'][i]-center[i])**2 for i in range(2)) for r in good)/len(good)) if good else None)


class RayOwner(RaysMixin):
    def __init__(self,backend,system):
        self.system=system;self.native=backend.native;self._cancel_boundary=backend._cancel_boundary;self._release_owned=backend._release_owned


def run_scan_pupil(b,q):
    from .models import BatchRays
    b._require_sequential();b._require_work()
    def flow(task):
        system=None;error=None
        task['payload']=dict(analysis_kind=q.kind,series=[],grids=[],cases=[],conjugates=[],
            units=dict(position='lens units',angle='degrees',slope='dimensionless'),
            direction_convention='native sequential cosines retained; global physical direction includes mirror parity from input plane',
            input_frame='start surface local, collimated +Z circular grid',ray_samples='equal weight grid points inside disk')
        task['restoration']=dict(required=False,restored=True,reason='owned copy; original source unchanged')
        try:
            system=b.system.CopySystem()
            if system is None:raise ZemaxError('COPY_FAILED','无法创建扫描副本。')
            count=int(system.LDE.NumberOfSurfaces)
            if q.image_surface>=count or q.wavelength>int(system.SystemData.Wavelengths.NumberOfWavelengths):raise ZemaxError('INDEX_OUT_OF_RANGE','扫描目标面或波长编号越界。')
            before=system.LDE.GetSurfaceAt(q.tilt_surface);mirror=system.LDE.GetSurfaceAt(q.mirror_surface);after=system.LDE.GetSurfaceAt(q.return_surface)
            if any(str(row.Type)!='CoordinateBreak' for row in [before,after]) or str(mirror.Type)!='Standard' or str(mirror.Material)!='MIRROR' or not math.isinf(float(mirror.Radius)):
                raise ZemaxError('UNSUPPORTED_SCANNER_MODEL','扫描采用CoordinateBreak/平面MIRROR/CoordinateBreak。')
            if abs(float(before.Thickness))>1e-12 or abs(float(mirror.Thickness))>1e-12:raise ZemaxError('INVALID_SCANNER_PIVOT','断点与镜面须共点，间隔为零。')
            param=3 if q.axis=='X' else 4
            for row in [before,after]:
                for p in [1,2,3,4,5]:
                    cell=b._cell(row,f'parameter_{p}')
                    if p!=param and abs(float(cell.DoubleValue))>1e-12:raise ZemaxError('UNSUPPORTED_SCANNER_MODEL','扫描断点采用指定单轴、零偏心。',surface=int(row.SurfaceNumber),parameter=p)
                b._guard_cell(b._cell(row,f'parameter_{param}'),False)
            for i in range(q.start_surface,q.image_surface+1):
                row=system.LDE.GetSurfaceAt(i)
                if bool(row.TiltDecenterData.BeforeAfterSurfaceEnabled):
                    if any(abs(float(getattr(row.TiltDecenterData,p+n)))>1e-12 for p in ['BeforeSurface','AfterSurface'] for n in ['DecenterX','DecenterY','TiltX','TiltY','TiltZ']):
                        raise ZemaxError('UNSUPPORTED_SCANNER_MODEL','追迹段的坐标变换使用显式CoordinateBreak。',surface=i)
            bc=b._cell(before,f'parameter_{param}');ac=b._cell(after,f'parameter_{param}');base=float(bc.DoubleValue);return_base=float(ac.DoubleValue)
            task['payload']['pivot']=dict(surface=q.mirror_surface,tilt_surface=q.tilt_surface,return_surface=q.return_surface,
                axis=q.axis,nominal_tilt_deg=base,nominal_return_deg=return_base)
            task['payload']['pupil_identity']=dict(surface=q.pupil_surface,is_system_stop=int(system.LDE.StopSurface)==q.pupil_surface,
                aperture_type=str(system.LDE.GetSurfaceAt(q.pupil_surface).ApertureData.CurrentType),semi_diameter=float(system.LDE.GetSurfaceAt(q.pupil_surface).SemiDiameter))
            task['payload']['pupil_identity']['entrance_pupil_definition']='system stop imaged through preceding optics; differential map refers to requested physical pupil surface'
            task['payload']['coordinate_scope']='local differential conjugates; global physical ray coordinates include native transforms and reflection parity'
            spacing_cell=system.LDE.GetSurfaceAt(q.spacing.surface).ThicknessCell if q.spacing else None
            if spacing_cell is not None:b._guard_cell(spacing_cell,False)
            spacings=q.spacing.values if q.spacing else [None];angles=sorted(set(q.angles_deg)|{0.})
            owner=RayOwner(b,system)
            def trace(rays,target):
                req=BatchRays(rays=rays,input_mode='Direct',start_surface=q.start_surface,target_surface=target)
                return b._composite('scan_pupil_rays',dict(target=target,ray_count=len(rays)),lambda child:owner._extended_trace_flow(child,req,target))
            def ray(x=0.,y=0.,sx=0.,sy=0.):
                n=1/math.sqrt(1+sx*sx+sy*sy)
                return dict(x=x+q.beam_center_x,y=y+q.beam_center_y,z=0.,l=sx*n,m=sy*n,n=n,wavelength=q.wavelength)
            beam=[]
            for iy in range(q.ray_density):
                y=-1+2*iy/(q.ray_density-1)
                for ix in range(q.ray_density):
                    x=-1+2*ix/(q.ray_density-1)
                    if 0<x*x+y*y<=1+1e-12:beam.append(ray(x*q.beam_radius,y*q.beam_radius))
            beam.insert(0,ray());probes=[ray()]
            for axis,step in enumerate([q.probe_height,q.probe_height,q.probe_slope,q.probe_slope]):
                for sign in [1,-1]:
                    v=[0.,0.,0.,0.];v[axis]=sign*step;probes.append(ray(*v))
            for candidate,spacing in enumerate(spacings):
                b._cancel_boundary(task)
                if spacing is not None:spacing_cell.DoubleValue=spacing;check_setting_value('Thickness',spacing,float(spacing_cell.DoubleValue))
                reference=None;peak_walk=0.;minimum_throughput=1.
                for angle in [0.]+[v for v in angles if v!=0]:
                    b._cancel_boundary(task);bc.DoubleValue=base+angle;ac.DoubleValue=return_base-angle
                    system.UpdateStatus();check_setting_value('scan tilt',base+angle,float(bc.DoubleValue));check_setting_value('return tilt',return_base-angle,float(ac.DoubleValue))
                    transforms={s:list(system.LDE.GetGlobalMatrix(s)) for s in set([q.start_surface,q.mirror_surface,q.pupil_surface,q.image_surface])}
                    if any(not v[0] for v in transforms.values()):raise ZemaxError('INVALID_TRANSFORM','原生坐标变换无效。')
                    if reference is not None and any(abs(a-c)>1e-9 for a,c in zip(reference['target_transform'][1:],transforms[q.pupil_surface][1:])):
                        raise ZemaxError('SCANNER_FRAME_MOVED','返回断点未保持目标面坐标。')
                    traced={}
                    for target in dict.fromkeys([q.mirror_surface,q.pupil_surface,q.image_surface]):
                        result=yield from b._child_job(task,lambda _:trace(beam,target),None);traced[target]=result['rows']
                    stats={name:footprint(traced[s]) for name,s in [('mirror',q.mirror_surface),('pupil',q.pupil_surface),('image',q.image_surface)]}
                    chief=traced[q.mirror_surface][0]
                    if chief.get('error_code') or chief.get('vignette_code'):raise ZemaxError('CHIEF_RAY_FAILED','镜面主光线未通过。',ray=chief)
                    incident=rotate(transforms[q.start_surface],[0.,0.,1.]);normal=rotate(transforms[q.mirror_surface],[0.,0.,1.])
                    actual=global_ray(transforms[q.mirror_surface],chief,-1)['direction'];expected=reflect(incident,normal)
                    error_max=max(abs(a-c) for a,c in zip(actual,expected))
                    if error_max>1e-7:raise ZemaxError('REFLECTION_REFERENCE_FAILED','镜面物理方向与反射定律不符。',actual=actual,expected=expected,error=error_max)
                    out=traced[q.image_surface][0]
                    image_angle=[math.degrees(math.atan2(v,out['direction'][2])) for v in out['direction'][:2]] if out.get('direction') else None
                    case=dict(candidate=candidate,spacing=spacing,angle_deg=angle,actual_tilt_deg=float(bc.DoubleValue),actual_return_deg=float(ac.DoubleValue),
                        statistics=stats,reflection=dict(actual=actual,expected=expected,max_error=error_max),image_chief_angles_deg=image_angle,
                        pupil_chief_position=traced[q.pupil_surface][0].get('position'),image_chief_position=out.get('position'),target_transform=transforms[q.pupil_surface])
                    if angle==0:
                        reference=case
                        probe_results={}
                        for target in [q.mirror_surface,q.pupil_surface]:
                            result=yield from b._child_job(task,lambda _:trace(probes,target),None);probe_results[target]=result['rows']
                        task['payload']['conjugates'].append(dict(candidate=candidate,spacing=spacing,**conjugates(probe_results[q.mirror_surface],probe_results[q.pupil_surface])))
                    center=stats['pupil']['center'];center0=reference['statistics']['pupil']['center']
                    case['beam_walk']=math.dist(center,center0) if center is not None and center0 is not None else None
                    case['chief_scan_displacement']=[a-c for a,c in zip(case['image_chief_position'][:2],reference['image_chief_position'][:2])] if case['image_chief_position'] and reference['image_chief_position'] else None
                    if case['beam_walk'] is not None:peak_walk=max(peak_walk,case['beam_walk'])
                    minimum_throughput=min(minimum_throughput,stats['pupil']['throughput'])
                    task['payload']['cases'].append(case)
                    for target,rows in traced.items():
                        parity=(-1)**sum(str(system.LDE.GetSurfaceAt(i).Material)=='MIRROR' for i in range(q.start_surface+1,target+1))
                        for row in rows:
                            task['rows'].append(dict(candidate=candidate,spacing=spacing,angle_deg=angle,target_surface=target,
                                **row,global_ray=global_ray(transforms[target],row,parity) if row.get('position') and row.get('direction') else None))
                    yield
                score=(1-minimum_throughput,peak_walk)
                record=dict(candidate=candidate,spacing=spacing,minimum_throughput=minimum_throughput,max_beam_walk=peak_walk,score=list(score))
                task['payload'].setdefault('candidates',[]).append(record)
                best=min(task['payload']['candidates'],key=lambda c:c['score'])
                if best is record and q.save_best:
                    bc.DoubleValue=base;ac.DoubleValue=return_base;system.UpdateStatus()
                    path=Path(b.directory)/(task['task_id']+f'_candidate_{candidate}.zos');system.SaveAs(str(path));record['saved_model']=str(path)
            task['summary']=dict(candidate_count=len(spacings),case_count=len(task['payload']['cases']),best_candidate=best,
                ranking='maximize minimum sampled pupil throughput, then minimize maximum sampled beam walk',ray_count=len(beam))
            for candidate in range(len(spacings)):
                cases=sorted([c for c in task['payload']['cases'] if c['candidate']==candidate],key=lambda c:c['angle_deg'])
                coordinate=0 if q.axis=='Y' else 1
                pairs=[(math.radians(c['angle_deg']),c['chief_scan_displacement'][coordinate]) for c in cases if c['chief_scan_displacement'] and c['angle_deg']]
                denominator=sum(a*a for a,v in pairs)
                slope=sum(a*v for a,v in pairs)/denominator if denominator else None
                for case in cases:
                    displacement=case['chief_scan_displacement']
                    linear=slope*math.radians(case['angle_deg']) if slope is not None else None
                    case['linear_scan_reference']=linear
                    case['scan_distortion']=displacement[coordinate]-linear if displacement and linear is not None else None
                    case['relative_scan_distortion']=case['scan_distortion']/linear if linear and case['scan_distortion'] is not None else None
                task['payload']['candidates'][candidate]['scan_fit']=dict(axis='XY'[coordinate],units='lens units/radian mirror increment',slope=slope,
                    definition='least-squares through zero using all nonzero requested angles; distortion is image chief displacement minus fit')
                task['payload']['series'].append(dict(series=candidate,description=f'Scanner candidate {candidate}',x_label='mirror increment',x_unit='degrees',y_unit='lens units',
                    labels=['beam walk'],x=[c['angle_deg'] for c in cases],y=[[c['beam_walk']] for c in cases]))
        except BaseException as exc:error=exc;raise
        finally:
            closed=False;cleanup=[]
            if system is not None:
                try:
                    if system.Close(False) is False:raise RuntimeError('Close(False) returned false')
                    closed=True
                except Exception as exc:cleanup.append(str(exc));b.requires_reconnect=True
            task['payload']['resources']=dict(copy_closed=closed,cleanup_errors=cleanup)
            if cleanup:raise ZemaxError('CLEANUP_FAILED','扫描工作副本关闭失败。',cleanup_errors=cleanup,operation_error=b._evaluation_error(error) if error else None)
    return b._composite(q.kind,q.model_dump(),flow)
