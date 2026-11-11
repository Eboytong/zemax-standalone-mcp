"""Sample native sag in a declared aperture and evaluate manufacturing limits."""
import math
import time
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .errors import ZemaxError
from .schema import FiniteFloat, PositiveIndex, Request


class SphereReference(Request):
    kind: Literal['vertex_sphere', 'specified_sphere'] = 'vertex_sphere'
    radius: FiniteFloat | None = None
    vertex_sag: FiniteFloat = 0

    @model_validator(mode='after')
    def contract(self):
        if (self.kind == 'specified_sphere') != (self.radius is not None):
            raise ValueError('specified_sphere需要radius；vertex_sphere采用原生顶点半径。')
        return self


class ManufacturingLimits(Request):
    max_abs_sag: Annotated[FiniteFloat, Field(ge=0)] | None = None
    max_slope_rad: Annotated[FiniteFloat, Field(ge=0, lt=math.pi/2)] | None = None
    max_abs_curvature: Annotated[FiniteFloat, Field(ge=0)] | None = None
    max_abs_departure: Annotated[FiniteFloat, Field(ge=0)] | None = None
    min_center_thickness: FiniteFloat | None = None
    min_edge_thickness: FiniteFloat | None = None


class ManufacturingGeometry(Request):
    kind: Literal['manufacturing_geometry']
    surface: PositiveIndex
    back_surface: PositiveIndex | None = None
    aperture_radius: Annotated[FiniteFloat, Field(gt=0)]
    center_x: FiniteFloat = 0
    center_y: FiniteFloat = 0
    sampling: Literal['radial', 'grid'] = 'radial'
    samples: Annotated[int, Field(strict=True, ge=5, le=101)] = 21
    meridians: Annotated[int, Field(strict=True, ge=4, le=64)] = 16
    derivative_step: Annotated[FiniteFloat, Field(gt=0)] | None = None
    reference: SphereReference = Field(default_factory=SphereReference)
    limits: ManufacturingLimits = Field(default_factory=ManufacturingLimits)
    refine: bool = True
    budget_seconds: Annotated[FiniteFloat, Field(gt=0, le=120)] = 120

    @model_validator(mode='after')
    def contract(self):
        if self.samples % 2 != 1:
            raise ValueError('samples必须为奇数。')
        if self.back_surface is not None and self.back_surface <= self.surface:
            raise ValueError('back_surface必须位于前表面之后。')
        if self.back_surface is None and (self.limits.min_center_thickness is not None or
                                         self.limits.min_edge_thickness is not None):
            raise ValueError('厚度阈值需要back_surface。')
        if self.derivative_step is not None and self.derivative_step > self.aperture_radius/10:
            raise ValueError('derivative_step必须不大于有效口径半径的十分之一。')
        return self


class InvalidSag(ValueError):
    pass


def sphere_sag(radius, x, y):
    if radius == 0:
        return 0.
    c = 1/radius
    root = 1-c*c*(x*x+y*y)
    if root < 0:
        raise InvalidSag('reference_sphere_domain')
    return c*(x*x+y*y)/(1+math.sqrt(root))


def differential(sag, x, y, h):
    """Fourth-order axial stencils and centered mixed derivative, local units."""
    z = sag(x, y)
    xm2, xm, xp, xp2 = [sag(x+k*h, y) for k in (-2,-1,1,2)]
    ym2, ym, yp, yp2 = [sag(x, y+k*h) for k in (-2,-1,1,2)]
    dx = (xm2-8*xm+8*xp-xp2)/(12*h)
    dy = (ym2-8*ym+8*yp-yp2)/(12*h)
    dxx = (-xp2+16*xp-30*z+16*xm-xm2)/(12*h*h)
    dyy = (-yp2+16*yp-30*z+16*ym-ym2)/(12*h*h)
    dxy = (sag(x+h,y+h)-sag(x+h,y-h)-sag(x-h,y+h)+sag(x-h,y-h))/(4*h*h)
    w = math.sqrt(1+dx*dx+dy*dy)
    mean = ((1+dy*dy)*dxx-2*dx*dy*dxy+(1+dx*dx)*dyy)/(2*w**3)
    gaussian = (dxx*dyy-dxy*dxy)/w**4
    disc = math.sqrt(max(0, mean*mean-gaussian))
    return dict(sag=z, slope_x=dx, slope_y=dy, slope_rad=math.atan(math.hypot(dx,dy)),
                principal_curvature_min=mean-disc, principal_curvature_max=mean+disc)


def sample_points(q, n):
    a = q.aperture_radius
    if q.sampling == 'radial':
        yield dict(x=q.center_x,y=q.center_y,radius=0.,edge=False)
        for i in range(1,n):
            r = a*i/(n-1)
            for j in range(q.meridians):
                angle = 2*math.pi*j/q.meridians
                yield dict(x=q.center_x+r*math.cos(angle),y=q.center_y+r*math.sin(angle),
                           radius=r,edge=i==n-1,meridian=j)
    else:
        for iy in range(n):
            y = -a+2*a*iy/(n-1)
            for ix in range(n):
                x = -a+2*a*ix/(n-1)
                r = math.hypot(x,y)
                if r <= a*(1+1e-12):
                    yield dict(x=x+q.center_x,y=y+q.center_y,radius=r,edge=abs(r-a)<a*1e-12,
                               ix=ix,iy=iy)
        # A circular edge is sampled explicitly between the rectangular grid nodes.
        for j in range(q.meridians):
            angle = 2*math.pi*j/q.meridians
            yield dict(x=q.center_x+a*math.cos(angle),y=q.center_y+a*math.sin(angle),
                       radius=a,edge=True,meridian=j)


def transform(lde, surface):
    data = lde.GetGlobalMatrix(surface)
    if not data[0]:
        raise ZemaxError('INVALID_RESULT_DATA','原生曲面坐标变换不可用。',surface=surface)
    return [list(data[1+3*i:4+3*i]) for i in range(3)], list(data[10:13])


def global_point(matrix, point):
    r,t = matrix
    return [sum(r[i][j]*point[j] for j in range(3))+t[i] for i in range(3)]


def paired_thickness(sag, x, y, front_sag, front, back):
    """Intersect the same physical line, parallel to the front local +Z axis."""
    rf,tf = front
    rb,tb = back
    point = global_point(front, [x,y,front_sag])
    local = [sum(rb[k][i]*(point[k]-tb[k]) for k in range(3)) for i in range(3)]
    direction = [sum(rb[k][i]*rf[k][2] for k in range(3)) for i in range(3)]
    if abs(direction[2]) < 1e-8:
        raise InvalidSag('back_surface_parallel_to_measurement_axis')
    distance = -local[2]/direction[2]
    for _ in range(30):
        bx,by,bz = [local[i]+distance*direction[i] for i in range(3)]
        residual = bz-sag(bx,by)
        if abs(residual) < 1e-10:
            return distance
        step = max(1e-5,abs(distance)*1e-5)
        plus = [local[i]+(distance+step)*direction[i] for i in range(3)]
        minus = [local[i]+(distance-step)*direction[i] for i in range(3)]
        derivative = direction[2]-(sag(plus[0],plus[1])-sag(minus[0],minus[1]))/(2*step)
        if abs(derivative)<1e-10:
            break
        distance -= residual/derivative
    raise InvalidSag('back_surface_intersection_not_converged')


METRICS = {
    'max_abs_sag': ('sag','abs_max'), 'max_slope_rad': ('slope_rad','max'),
    'max_abs_curvature': ('abs_curvature','max'), 'max_abs_departure': ('departure','abs_max'),
    'min_center_thickness': ('thickness','center'), 'min_edge_thickness': ('thickness','edge_min')}


def summarize(rows):
    result = {}
    for name,(field,mode) in METRICS.items():
        candidates = [r for r in rows if r.get(field) is not None and
                      (mode!='center' or r['radius']==0) and (mode!='edge_min' or r['edge'])]
        if not candidates:
            result[name] = dict(value=None,status='unavailable')
            continue
        key = (lambda r:abs(r[field])) if mode=='abs_max' else (lambda r:r[field])
        row = (min if mode in {'center','edge_min'} else max)(candidates,key=key)
        result[name] = dict(value=key(row),x=row['x'],y=row['y'],sample=row['index'],
                            status='sampled',signed_value=row[field])
    return result


def run_manufacturing_geometry(b, q):
    b._require_sequential()
    row = b._row(q.surface)
    supported = {'Standard','EvenAspheric','ExtendedPolynomial'}
    kind = str(row.Type)
    if kind not in supported:
        raise ZemaxError('UNSUPPORTED_SURFACE_TYPE','制造几何适配支持Standard、EvenAspheric、ExtendedPolynomial。',surface_type=kind)
    radius = float(row.Radius) if q.reference.kind=='vertex_sphere' else q.reference.radius
    if math.isinf(radius):
        radius = 0.
    lde = b.system.LDE
    front = transform(lde,q.surface)
    back = None
    if q.back_surface is not None:
        other = b._row(q.back_surface)
        if str(other.Type) not in supported:
            raise ZemaxError('UNSUPPORTED_SURFACE_TYPE','后表面缺少已登记的制造几何适配。',surface_type=str(other.Type))
        back = transform(lde,q.back_surface)
    unit = str(b.system.SystemData.Units.LensUnits)
    h = q.derivative_step or q.aperture_radius*1e-3

    def native_sag(surface):
        cache = {}
        def sag(x,y):
            key = (x,y)
            if key not in cache:
                try:
                    ok,z,_ = lde.GetSag(surface,x,y)
                except Exception as exc:
                    raise ZemaxError('NATIVE_ERROR','GetSag调用失败。',surface=surface,x=x,y=y,
                                     native_type=type(exc).__name__,native_message=str(exc)) from exc
                if not ok or not math.isfinite(z):
                    raise InvalidSag('native_sag_domain')
                cache[key] = float(z)
            return cache[key]
        return sag

    sag = native_sag(q.surface)
    back_sag = native_sag(q.back_surface) if back else None
    actual = dict(surface_type=kind,reference_radius=radius,reference_vertex_sag=q.reference.vertex_sag,
                  derivative_step=h,units=unit,front_transform=front,back_transform=back,
                  native_semi_diameter=float(row.SemiDiameter),configuration=int(b.system.MCE.CurrentConfiguration))

    def flow(task):
        started = time.monotonic()
        task['payload'] = dict(analysis_kind=q.kind,actual_settings=actual,
            computation_method='native LDE.GetSag and GetGlobalMatrix; finite-difference differential geometry',
            coordinates='front surface local X/Y/Z; thickness along front local +Z to physical back surface',
            extrema_scope='sampled aperture disk and explicitly sampled circular rim',units=dict(length=unit,
                slope='radians',curvature='1/'+unit),thresholds=[],series=[],grids=[])
        coarse = None
        levels = [q.samples,2*q.samples-1] if q.refine else [q.samples]
        for level,n in enumerate(levels):
            rows = []
            sampling_request = q.model_copy(update={'meridians':q.meridians*(2 if level else 1)})
            step = h/(2 if level else 1)
            points = list(sample_points(sampling_request,n))
            for i,point in enumerate(points):
                b._cancel_boundary(task)
                if time.monotonic()-started > q.budget_seconds:
                    raise ZemaxError('BUDGET_EXCEEDED','制造几何采样超过时间预算。',completed_samples=len(rows))
                item = dict(index=i,**point,status='valid')
                try:
                    item['sag'] = sag(point['x'],point['y'])
                    item.update(differential(sag,point['x'],point['y'],step))
                    item['abs_curvature'] = max(abs(item['principal_curvature_min']),abs(item['principal_curvature_max']))
                    item['departure'] = item['sag']-sphere_sag(radius,point['x'],point['y'])-q.reference.vertex_sag
                    if back:
                        item['thickness'] = paired_thickness(back_sag,point['x'],point['y'],item['sag'],front,back)
                except InvalidSag as exc:
                    item.update(status='invalid',reason=str(exc))
                rows.append(item)
                task['rows'] = rows
                task['progress'] = 100*(level+i/len(points))/len(levels)
                if i%8==0:
                    yield
            metrics = summarize(rows)
            if coarse is None:
                coarse = metrics
        if not any(r.get('sag') is not None for r in rows):
            raise ZemaxError('NO_RESULT_DATA','有效口径内没有可读取的原生矢高。')
        invalid = sum(r['status']!='valid' for r in rows)
        task['summary'] = dict(metrics=metrics,sample_count=len(rows),invalid_count=invalid,
                              sampling=q.sampling,samples_per_axis=n,meridians=sampling_request.meridians,
                              final_derivative_step=step)
        task['payload']['convergence'] = dict(refined=q.refine,coarse=coarse,
            absolute_change={name:abs(v['value']-coarse[name]['value']) if v['value'] is not None and
                             coarse[name]['value'] is not None else None for name,v in metrics.items()})
        for name,limit in q.limits.model_dump(exclude_none=True).items():
            metric = metrics[name]
            value = metric['value']
            passed = None if value is None or invalid else (value>=limit if name.startswith('min_') else value<=limit)
            task['payload']['thresholds'].append(dict(metric=name,limit=limit,actual=value,
                state='unverified' if passed is None else ('satisfied' if passed else 'violated'),
                x=metric.get('x'),y=metric.get('y')))
        rim = [r for r in rows if r['edge'] and r.get('sag') is not None]
        rim.sort(key=lambda r:math.atan2(r['y']-q.center_y,r['x']-q.center_x))
        if rim:
            task['payload']['series'] = [dict(series=0,description='Aperture rim geometry',x_label='azimuth',
                x_unit='degrees',y_unit=unit,labels=['sag','sphere departure','axial thickness'],
                x=[math.degrees(math.atan2(r['y']-q.center_y,r['x']-q.center_x)) for r in rim],
                y=[[r.get('sag'),r.get('departure'),r.get('thickness')] for r in rim])]
        if q.sampling=='grid':
            for field in ('sag','departure','slope_rad','abs_curvature','thickness'):
                if not any(r.get(field) is not None for r in rows):
                    continue
                values = [[None]*n for _ in range(n)]
                for r in rows:
                    if 'ix' in r:
                        values[r['iy']][r['ix']] = r.get(field)
                task['payload']['grids'].append(dict(grid=len(task['payload']['grids']),description=field,
                    nx=n,ny=n,min_x=q.center_x-q.aperture_radius,min_y=q.center_y-q.aperture_radius,
                    dx=2*q.aperture_radius/(n-1),dy=2*q.aperture_radius/(n-1),values=values,
                    x_label='local X',y_label='local Y',x_unit=unit,y_unit=unit,
                    value_label=field,value_unit='rad' if field=='slope_rad' else '1/'+unit if field=='abs_curvature' else unit,
                    array_order='values[y][x]'))
        task['restoration'] = dict(required=False,reason='read-only native geometry queries')
    return b._composite('manufacturing_geometry',q.model_dump()|dict(actual=actual),flow)
