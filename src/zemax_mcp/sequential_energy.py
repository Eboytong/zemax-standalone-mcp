"""Per-surface cumulative polarized ray intensity and loss accounting."""
import math
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .schema import Request, Index, PositiveIndex, FiniteFloat


class EnergyRay(Request):
    wavelength: PositiveIndex = 1
    hx: FiniteFloat | None = None
    hy: FiniteFloat | None = None
    px: FiniteFloat | None = None
    py: FiniteFloat | None = None
    x: FiniteFloat | None = None
    y: FiniteFloat | None = None
    z: FiniteFloat | None = None
    l: FiniteFloat | None = None
    m: FiniteFloat | None = None
    n: FiniteFloat | None = None
    weight: Annotated[FiniteFloat, Field(gt=0)] = 1


class EnergyPolarization(Request):
    jx: Annotated[FiniteFloat, Field(ge=0)] = 1
    jy: Annotated[FiniteFloat, Field(ge=0)] = 0
    x_phase: FiniteFloat = 0
    y_phase: FiniteFloat = 0

    @model_validator(mode='after')
    def normalized(self):
        if self.jx == self.jy == 0 or not math.isclose(self.jx*self.jx+self.jy*self.jy,1,rel_tol=1e-8,abs_tol=1e-8):
            raise ValueError('Jones幅度须满足jx²+jy²=1。')
        return self


class SequentialEnergyBudget(Request):
    kind: Literal['sequential_energy_budget']
    rays: Annotated[list[EnergyRay], Field(min_length=1,max_length=10000)]
    input_mode: Literal['Normalized','Direct'] = 'Normalized'
    start_surface: Index = 1
    first_surface: PositiveIndex = 1
    last_surface: PositiveIndex | None = None
    polarization: EnergyPolarization = Field(default_factory=EnergyPolarization)
    input_power_w: Annotated[FiniteFloat, Field(gt=0)] | None = None

    @model_validator(mode='after')
    def ray_frame(self):
        normalized=('hx','hy','px','py');direct=('x','y','z','l','m','n')
        required=normalized if self.input_mode=='Normalized' else direct
        forbidden=direct if self.input_mode=='Normalized' else normalized
        for i,ray in enumerate(self.rays):
            if any(getattr(ray,k) is None for k in required) or any(getattr(ray,k) is not None for k in forbidden):
                raise ValueError(f'rays[{i}]的坐标字段与input_mode不符。')
        if self.first_surface <= self.start_surface and self.input_mode=='Direct':
            raise ValueError('Direct追迹首个统计面须位于start_surface之后。')
        return self


def summarize_surface(surface, rows, weights, input_total, previous_total):
    states={name:sum(r.get('state')==name for r in rows) for name in ('succeeded','vignetted','error','missing')}
    success=[(r,weights[i]) for i,r in enumerate(rows) if r.get('state')=='succeeded' and isinstance(r.get('intensity'),(int,float)) and math.isfinite(r['intensity'])]
    output=math.fsum(weight*row['intensity'] for row,weight in success)
    base=previous_total if previous_total is not None else input_total
    return dict(surface=surface,**states,weighted_intensity_in=base,weighted_intensity_out=output,
        cumulative_throughput=output/input_total if input_total else None,
        surface_retention=output/base if base else None,
        surface_loss_fraction=1-output/base if base else None,
        intensity_scope='native polarized cumulative ray intensity after the target surface; successful rays only')


def run_energy_budget(b,q):
    from .models import BatchRays, Ray, DirectRay, RayPolarization
    b._require_sequential(focused=True);b._require_work()
    total_surfaces=int(b.system.LDE.NumberOfSurfaces)
    last=q.last_surface if q.last_surface is not None else total_surfaces-1
    if not q.first_surface<=last<total_surfaces:raise ValueError('last_surface须在像面或其前且不小于first_surface。')
    if q.input_mode=='Direct' and q.start_surface>=q.first_surface:raise ValueError('start_surface必须早于统计范围。')
    for ray in q.rays:
        if ray.wavelength>int(b.system.SystemData.Wavelengths.NumberOfWavelengths):raise ValueError('光线波长编号越界。')
    def flow(task):
        task['payload']=dict(analysis_kind=q.kind,computation_method='native polarized batch ray tracing terminated at each sequential surface; normalized rays use a paired native unpolarized trace for vignetting codes',
            units=dict(intensity='relative',power='W' if q.input_power_w else None),series=[],grids=[],surfaces=[],child_tasks=[])
        weights=[float(r.weight) for r in q.rays];input_total=math.fsum(weights);previous=None;closed_children=0
        try:
            for surface in range(q.first_surface,last+1):
                b._cancel_boundary(task)
                rays=[]
                for r in q.rays:
                    if q.input_mode=='Normalized':rays.append(Ray(wavelength=r.wavelength,hx=r.hx,hy=r.hy,px=r.px,py=r.py))
                    else:rays.append(DirectRay(wavelength=r.wavelength,x=r.x,y=r.y,z=r.z,l=r.l,m=r.m,n=r.n))
                req=BatchRays(rays=rays,input_mode=q.input_mode,start_surface=q.start_surface,
                    polarization=RayPolarization(jx=q.polarization.jx,jy=q.polarization.jy,x_phase=q.polarization.x_phase,y_phase=q.polarization.y_phase),
                    target_surface=surface)
                result=yield from b._child_job(task,b.run_batch_ray_trace,req)
                closed_children+=1
                rows=result['rows']
                if len(rows)!=len(q.rays):raise ValueError(f'面{surface}原生结果数与输入光线数不符。')
                if q.input_mode=='Normalized':
                    geometry=yield from b._child_job(task,b.run_batch_ray_trace,req.model_copy(update={'polarization':None}))
                    closed_children+=1
                    if len(geometry['rows'])!=len(q.rays):raise ValueError(f'面{surface}几何追迹结果数与输入光线数不符。')
                    for polarized,unpolarized in zip(rows,geometry['rows']):
                        if unpolarized.get('state')=='error' and polarized.get('state')!='error':
                            polarized.update(state='error',error_code=unpolarized.get('error_code'),vignette_code=unpolarized.get('vignette_code'))
                        elif unpolarized.get('vignette_code'):
                            polarized.update(state='vignetted',vignette_code=unpolarized['vignette_code'])
                        else:
                            polarized['vignette_code']=0
                row=summarize_surface(surface,rows,weights,input_total,previous)
                if q.input_power_w is not None:
                    scale=q.input_power_w/input_total
                    row.update(input_power_w=row['weighted_intensity_in']*scale,output_power_w=row['weighted_intensity_out']*scale,
                        lost_power_w=(row['weighted_intensity_in']-row['weighted_intensity_out'])*scale)
                row['ray_start']=len(task['rows'])
                for i,ray in enumerate(rows):
                    task['rows'].append(dict(surface=surface,ray_id=i,weight=weights[i],**ray))
                row['ray_count']=len(rows);task['payload']['surfaces'].append(row);previous=row['weighted_intensity_out']
                task['progress']=int(100*(surface-q.first_surface+1)/(last-q.first_surface+1));yield
            task['payload']['resources']=dict(child_tasks_closed=True,closed_child_tasks=closed_children,
                source_model_unchanged=True,restoration='not required; analysis is read-only')
            task['payload']['series']=[dict(series=0,description='Weighted cumulative throughput by sequential surface',
                x_label='surface',x_unit='surface index',y_unit='fraction',
                labels=['cumulative throughput','surface retention'],
                x=[r['surface'] for r in task['payload']['surfaces']],
                y=[[r['cumulative_throughput'],r['surface_retention']] for r in task['payload']['surfaces']])]
            task['summary']=dict(first_surface=q.first_surface,last_surface=last,ray_count=len(q.rays),
                input_weight=input_total,input_power_w=q.input_power_w,
                final_throughput=task['payload']['surfaces'][-1]['cumulative_throughput'],
                identified_vignetting_surfaces=sorted({r['vignette_code'] for r in task['rows'] if r.get('vignette_code',0)>0}),
                attenuating_surfaces=[r['surface'] for r in task['payload']['surfaces'] if r['surface_loss_fraction'] and r['surface_loss_fraction']>0])
        finally:
            task['payload'].setdefault('resources',dict(child_tasks_closed=True,closed_child_tasks=closed_children,
                source_model_unchanged=True,restoration='not required; analysis is read-only'))
    return b._composite(q.kind,q.model_dump(),flow)

