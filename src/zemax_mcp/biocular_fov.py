"""STOP-launched FOV masks and topologically separated sampled boundaries."""
import math
from typing import Annotated,Literal
from pydantic import Field,model_validator
from .schema import Request,PositiveIndex,Index,FiniteFloat
from .errors import ZemaxError
from .biocular import validation_rays

class BiocularFov(Request):
    kind: Literal['biocular_field_of_view']
    configurations: Annotated[list[Index],Field(min_length=1,max_length=4)] = Field(default_factory=lambda:[1])
    wavelength: PositiveIndex = 1
    use_angles: bool = True
    left: FiniteFloat = -10
    right: FiniteFloat = 10
    bottom: FiniteFloat = -10
    top: FiniteFloat = 10
    x_points: Annotated[int,Field(strict=True,ge=2,le=257)] = 41
    y_points: Annotated[int,Field(strict=True,ge=2,le=257)] = 41
    refinement_steps: Annotated[int,Field(strict=True,ge=0,le=24)] = 12

    @model_validator(mode='after')
    def domain(self):
        if not any(self.configurations):raise ValueError('至少选择一个配置；0禁用槽。')
        if self.left>=self.right or self.bottom>=self.top:raise ValueError('视场边界必须严格递增。')
        if self.use_angles:
            if max(abs(x)for x in [self.left,self.right,self.bottom,self.top])>=90:raise ValueError('角度须在−90和90之间。')
        elif max(abs(self.left),abs(self.right))**2+max(abs(self.bottom),abs(self.top))**2>=1:raise ValueError('方向余弦须满足X²+Y²<1。')
        if self.x_points*self.y_points*sum(c>0 for c in self.configurations)>100000:raise ValueError('初始网格总采样上限100000。')
        return self


def transition_edges(mask):
    ny=len(mask);nx=len(mask[0]);edges={}
    for j in range(ny):
        for i in range(nx):
            for k in [(i+1,j),(i,j+1)]:
                x,y=k
                if x<nx and y<ny and mask[j][i]!=mask[y][x]:edges[((i,j),k)]=None
    return edges


def boundary_segments(mask,xs,ys,points,centers):
    ny=len(ys);nx=len(xs);segments=[]
    def key(a,b):return tuple(sorted((a,b)))
    def point(a):return (xs[a[0]],ys[a[1]])
    for j in range(ny-1):
        for i in range(nx-1):
            corners=[(i,j),(i+1,j),(i+1,j+1),(i,j+1)]
            crossings={k:points[key(corners[k],corners[(k+1)%4])]for k in range(4)if key(corners[k],corners[(k+1)%4])in points}
            if len(crossings)==2:segments.append((*crossings.values(),'aperture'))
            elif len(crossings)==4:
                center=centers[(i,j)]
                for k,(x,y)in enumerate(corners):
                    if mask[y][x]!=center:segments.append((crossings[(k-1)%4],crossings[k],'aperture'))
    perimeter=[(i,0)for i in range(nx)]+[(nx-1,j)for j in range(1,ny)]+[(i,ny-1)for i in range(nx-2,-1,-1)]+[(0,j)for j in range(ny-2,0,-1)]
    for a,b in zip(perimeter,perimeter[1:]+perimeter[:1]):
        pa,pb=mask[a[1]][a[0]],mask[b[1]][b[0]]
        if pa and pb:segments.append((point(a),point(b),'scan_border'))
        elif pa!=pb:
            cross=points[key(a,b)];segments.append((point(a)if pa else point(b),cross,'scan_border'))
    return segments


def stitch_segments(segments):
    adjacency={}
    for i,(a,b,source)in enumerate(segments):
        adjacency.setdefault(a,[]).append((i,b));adjacency.setdefault(b,[]).append((i,a))
    remaining=set(range(len(segments)));curves=[]
    while remaining:
        first=min(remaining);start=segments[first][0];p=start;points=[p];sources=[]
        while True:
            candidates=[v for v in adjacency[p]if v[0]in remaining]
            if not candidates:break
            index,p=min(candidates);remaining.remove(index);sources.append(segments[index][2]);points.append(p)
            if p==start:break
        curves.append(dict(points=points,closed=points[-1]==start,scan_limited='scan_border'in sources))
    return curves


def fixed_apertures(system):
    for i in range(int(system.LDE.StopSurface)+1,int(system.LDE.NumberOfSurfaces)):
        row=system.LDE.GetSurfaceAt(i)
        if str(row.ApertureData.CurrentType)=='None'and str(row.SemiDiameterCell.GetSolveData().Type)not in ('Fixed','Variable'):
            raise ZemaxError('PRECONDITION_FAILED','FOV要求STOP之后使用固定口径。',surface=i,solve=str(row.SemiDiameterCell.GetSolveData().Type))


def run_fov(b,q):
    b._require_sequential();b._require_work()
    if max(q.configurations)>b.system.MCE.NumberOfConfigurations:raise ZemaxError('INDEX_OUT_OF_RANGE','FOV配置编号越界。')
    if q.wavelength>b.system.SystemData.Wavelengths.NumberOfWavelengths:raise ZemaxError('INDEX_OUT_OF_RANGE','FOV波长编号越界。')
    def flow(task):
        unit='degrees'if q.use_angles else'direction cosine';xs=[q.left+(q.right-q.left)*i/(q.x_points-1)for i in range(q.x_points)];ys=[q.bottom+(q.top-q.bottom)*j/(q.y_points-1)for j in range(q.y_points)]
        task['payload']=dict(analysis_kind=q.kind,computation_method='native_STOP_direct_trace_and_refined_marching_squares',
            actual_settings=dict(request=q.model_dump(),configuration=int(b.system.MCE.CurrentConfiguration),settings_source='explicit copied configuration and native direct-ray arguments'),
            grids=[],series=[],contours=[],sample_resolution=dict(dx=xs[1]-xs[0],dy=ys[1]-ys[0],refinement_steps=q.refinement_steps),
            validity_scope='sampled regions and transitions; sub-grid holes/islands require finer initial sampling')
        launched=0
        def trace(configuration,coordinates,role):
            nonlocal launched
            b._cancel_boundary(task)
            if launched+len(coordinates)>250000:raise ZemaxError('SAMPLING_BUDGET_EXCEEDED','FOV采样超过250000条。',requested=launched+len(coordinates),launched=launched)
            passed=[]
            for start in range(0,len(coordinates),10000):
                b._cancel_boundary(task);chunk=coordinates[start:start+10000]
                data=yield from validation_rays(b,task,configuration,[dict(x=x,y=y)for x,y in chunk],q,False,configure=fixed_apertures)
                launched+=len(chunk)
                for (x,y),ray in zip(chunk,data):
                    valid=ray['state']=='succeeded';passed.append(valid)
                    task['rows'].append(dict(index=len(task['rows']),configuration=configuration,x=x,y=y,role=role,passed=valid,ray=ray))
            return passed
        for configuration in [c for c in q.configurations if c]:
            coarse=yield from trace(configuration,[(x,y)for y in ys for x in xs],'grid')
            mask=[coarse[j*q.x_points:(j+1)*q.x_points]for j in range(q.y_points)]
            edges=transition_edges(mask);brackets={}
            for a,bp in edges:
                brackets[(a,bp)]=[(xs[a[0]],ys[a[1]]),(xs[bp[0]],ys[bp[1]]),mask[a[1]][a[0]]]
            for iteration in range(q.refinement_steps):
                coordinates=[((a[0]+c[0])/2,(a[1]+c[1])/2)for a,c,passed in brackets.values()]
                if not coordinates:break
                flags=yield from trace(configuration,coordinates,'boundary_refinement')
                for bracket,point,flag in zip(brackets.values(),coordinates,flags):bracket[0 if flag==bracket[2]else 1]=point
            points={key:((a[0]+c[0])/2,(a[1]+c[1])/2)for key,(a,c,flag)in brackets.items()}
            ambiguous=[(i,j)for j in range(q.y_points-1)for i in range(q.x_points-1)if mask[j][i]==mask[j+1][i+1]and mask[j][i+1]==mask[j+1][i]and mask[j][i]!=mask[j][i+1]]
            centers={}
            if ambiguous:
                values=yield from trace(configuration,[((xs[i]+xs[i+1])/2,(ys[j]+ys[j+1])/2)for i,j in ambiguous],'ambiguous_cell_center')
                centers=dict(zip(ambiguous,values))
            contours=stitch_segments(boundary_segments(mask,xs,ys,points,centers))
            for contour in contours:
                contour['configuration']=configuration;task['payload']['contours'].append(contour)
                task['payload']['series'].append(dict(series=len(task['payload']['series']),description='FOV config '+str(configuration),labels=['Y ('+unit+')'],x_label='STOP X',x_unit=unit,y_label='STOP Y',y_unit=unit,value_units=[unit],aspect='equal',x=[p[0]for p in contour['points']],y=[[p[1]]for p in contour['points']]))
            task['payload']['grids'].append(dict(configuration=configuration,nx=q.x_points,ny=q.y_points,min_x=q.left,min_y=q.bottom,dx=xs[1]-xs[0],dy=ys[1]-ys[0],x_label='STOP X',y_label='STOP Y',x_unit=unit,y_unit=unit,value_unit='unvignetted fraction',values=[[int(v)for v in row]for row in mask],invalid_count=0,array_order='values[y][x]'))
        task['summary']=dict(launched=launched,passed=sum(r['passed']for r in task['rows']),failed=sum(not r['passed']for r in task['rows']))
    return b._composite(q.kind,q.model_dump(),flow)
