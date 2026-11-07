"""Geometry in mm, with explicit numerical and representation uncertainty.

This module consumes geometry, not agent declarations or ray-trace outcomes.
"""
import heapq
import math
import time

ALGORITHM_VERSION = 'radial-interval-1/triangle-bvh-1'
TOLERANCE_MM = 1e-6


def _sag(surface, t):
    radius = surface['radius']
    c = 1/radius if radius else 0
    root = 1-(1+surface.get('conic', 0))*c*c*t
    if root < 0:
        raise ValueError('sag_domain')
    return c*t/(1+math.sqrt(root))+surface.get('quadratic',0)*t+sum(a*t**(i+2) for i,a in enumerate(surface.get('coefficients', [])))


def _derivative_bounds(surface, lo, hi):
    c = 1/surface['radius'] if surface['radius'] else 0
    q = (1+surface.get('conic', 0))*c*c
    ends = [1-q*lo, 1-q*hi]
    if min(ends) <= 0:
        return -math.inf, math.inf
    values = [c/(2*math.sqrt(x)) for x in ends]
    lower, upper = min(values)+surface.get('quadratic',0), max(values)+surface.get('quadratic',0)
    for i,a in enumerate(surface.get('coefficients', [])):
        v = [a*(i+2)*x**(i+1) for x in (lo,hi)]
        lower += min(v); upper += max(v)
    return lower, upper


def _radial_minimum(a, b, thickness, radius, deadline, tolerance, inner_radius=0):
    def value(t):
        return thickness+_sag(b,t)-_sag(a,t)
    start,end = inner_radius*inner_radius,radius*radius
    # Validate the complete sag domain, including non-sampled interior.
    for face in (a,b):
        _sag(face, start); _sag(face, end)
    best = min((value(t),t) for t in (start, (start+end)/2, end))
    queue = []
    def add(lo,hi):
        nonlocal best
        mid=(lo+hi)/2
        points=[(value(t),t) for t in (lo,mid,hi)]
        best=min(best,*points)
        da=_derivative_bounds(a,lo,hi); db=_derivative_bounds(b,lo,hi)
        lower_d, upper_d=db[0]-da[1], db[1]-da[0]
        if lower_d>=0: lower=points[0][0]
        elif upper_d<=0: lower=points[2][0]
        else: lower=points[1][0]-max(abs(lower_d),abs(upper_d))*(hi-lo)/2
        # Round-off allowance is distinct from geometric classification tolerance.
        lower -= 32*math.ulp(max(1,abs(points[1][0])))
        heapq.heappush(queue,(lower,lo,hi))
    add(start,end)
    iterations=0
    while queue and queue[0][0] < best[0]-tolerance:
        if time.monotonic()>deadline or iterations>=100000:
            return [queue[0][0],best[0]+32*math.ulp(max(1,abs(best[0])))],math.sqrt(best[1]),False
        lower,lo,hi=heapq.heappop(queue)
        mid=(lo+hi)/2
        if mid==lo or mid==hi:
            heapq.heappush(queue,(lower,lo,hi)); break
        add(lo,mid); add(mid,hi); iterations+=1
    return [min(best[0],queue[0][0]),best[0]+32*math.ulp(max(1,abs(best[0])))],math.sqrt(best[1]),True


def check_radial_pair(front, back, thickness, *, scale_mm=1, budget_seconds=120, minimum_mm=0):
    """Minimum axial separation over optical and declared mechanical overlap.

    Coefficients multiply r**4, r**6, ... in the supplied lens length unit.
    Bounds are calculated before conversion, so inch models retain their shape.
    """
    result=dict(state='unverified', algorithm_version=ALGORITHM_VERSION, issues=[], unit='mm')
    deadline=time.monotonic()+budget_seconds
    try:
        if not math.isfinite(scale_mm) or scale_mm<=0: raise ValueError('unknown_units')
        for f in (front,back):
            numbers=[f['radius'],f.get('conic',0),f.get('quadratic',0),f['semi_diameter'],f['mechanical_semi_diameter'],*f.get('coefficients',[])]
            if not all(math.isfinite(x) for x in numbers): raise ValueError('nonfinite_surface')
            if f['semi_diameter']<=0 or f['mechanical_semi_diameter']<f['semi_diameter']:
                raise ValueError('incomplete_entity_boundary')
        if not math.isfinite(thickness): raise ValueError('nonfinite_thickness')
        radii=[min(f['semi_diameter'] for f in (front,back)),min(f['mechanical_semi_diameter'] for f in (front,back))]
        complete=True
        for name,r in zip(('optical_minimum_mm','minimum_mm'),radii):
            bounds,position,converged=_radial_minimum(front,back,thickness,r,deadline,1e-8/scale_mm)
            result[name]=[x*scale_mm for x in bounds]
            result[name.replace('minimum_mm','position_radius_mm')]=position*scale_mm
            complete &= converged
        low,high=result['minimum_mm']
        result['state']='failed' if high < minimum_mm-TOLERANCE_MM else ('passed' if complete and low >= minimum_mm-TOLERANCE_MM else 'unverified')
        if result['state']!='passed': result['issues'].append('negative_separation' if high < -TOLERANCE_MM else 'boundary_or_precision')
        result['converged']=complete
    except (ValueError,KeyError,TypeError,OverflowError) as exc:
        result['issues'].append(str(exc))
    return result



def selected_radial_gap(front,back,scale_mm,region=None):
    """Signed axial face separation over a coaxial disk or physical annulus."""
    if any(f.get('requires_3d') or 'polynomial'in f for f in (front,back)):
        return dict(reason='selected_boundary_requires_3d_adapter')
    region=region or {}
    rectangle={f'{a}_{end}_mm'for a in 'xy'for end in ['min','max']}
    rectangular=set(region)==rectangle
    if set(region)-{'r_min_mm','r_max_mm'}and not rectangular:
        return dict(reason='engineering_region_adapter_required')
    thickness=(back['z_mm']-front['z_mm'])/scale_mm
    result=check_radial_pair(front,back,thickness,scale_mm=scale_mm,budget_seconds=2)
    if 'minimum_mm'not in result:return dict(reason='selected_boundary_definition_invalid',issues=result['issues'])
    inner=region.get('r_min_mm',0)/scale_mm
    outer=region.get('r_max_mm',min(front['mechanical_semi_diameter'],back['mechanical_semi_diameter'])*scale_mm)/scale_mm
    maximum=min(front['mechanical_semi_diameter'],back['mechanical_semi_diameter'])
    if rectangular:
        if any(region[f'{a}_min_mm']>=region[f'{a}_max_mm']for a in 'xy'):
            return dict(reason='invalid_rectangular_region')
        near=[max(region[f'{a}_min_mm'],0,-region[f'{a}_max_mm'])for a in 'xy']
        far=[max(abs(region[f'{a}_min_mm']),abs(region[f'{a}_max_mm']))for a in 'xy']
        inner=math.hypot(*near)/scale_mm;outer=min(math.hypot(*far)/scale_mm,maximum)
    if not (math.isfinite(inner)and math.isfinite(outer)and 0<=inner<outer<=maximum):
        return dict(reason='engineering_region_outside_boundary')
    bounds,radius,converged=_radial_minimum(front,back,thickness,outer,time.monotonic()+2,1e-8/scale_mm,inner)
    return dict(bounds=[v*scale_mm for v in bounds],position_radius_mm=radius*scale_mm,
                converged=converged,source='native_LDE_selected_radial_boundaries',
                region_mm=dict(region),radial_domain_mm=dict(r_min_mm=inner*scale_mm,r_max_mm=outer*scale_mm))


def _sub(a,b): return tuple(x-y for x,y in zip(a,b))
def _add(a,b): return tuple(x+y for x,y in zip(a,b))
def _mul(a,k): return tuple(x*k for x in a)
def _dot(a,b): return sum(x*y for x,y in zip(a,b))
def _cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def _norm(a): return math.sqrt(_dot(a,a))


def _point_triangle(p,t):
    # Closest point on a triangle (Voronoi regions).
    a,b,c=t; ab=_sub(b,a); ac=_sub(c,a); ap=_sub(p,a)
    d1,d2=_dot(ab,ap),_dot(ac,ap)
    if d1<=0 and d2<=0:return _norm(ap)
    bp=_sub(p,b); d3,d4=_dot(ab,bp),_dot(ac,bp)
    if d3>=0 and d4<=d3:return _norm(bp)
    vc=d1*d4-d3*d2
    if vc<=0 and d1>=0 and d3<=0:return _norm(_sub(p,_add(a,_mul(ab,d1/(d1-d3)))))
    cp=_sub(p,c); d5,d6=_dot(ab,cp),_dot(ac,cp)
    if d6>=0 and d5<=d6:return _norm(cp)
    vb=d5*d2-d1*d6
    if vb<=0 and d2>=0 and d6<=0:return _norm(_sub(p,_add(a,_mul(ac,d2/(d2-d6)))))
    va=d3*d6-d5*d4
    if va<=0 and d4>=d3 and d5>=d6:return _norm(_sub(p,_add(b,_mul(_sub(c,b),(d4-d3)/((d4-d3)+(d5-d6))))))
    n=_cross(ab,ac)
    return abs(_dot(ap,n))/_norm(n)


def _segment_distance(p,q,a,b):
    u,v,w=_sub(q,p),_sub(b,a),_sub(p,a)
    A,B,C,D,E=_dot(u,u),_dot(u,v),_dot(v,v),_dot(u,w),_dot(v,w)
    den=A*C-B*B
    s=max(0,min(1,(B*E-C*D)/den)) if den>1e-30 else 0
    t=(B*s+E)/C if C else 0
    if t<0: t=0; s=max(0,min(1,-D/A)) if A else 0
    if t>1: t=1; s=max(0,min(1,(B-D)/A)) if A else 0
    return _norm(_sub(_add(p,_mul(u,s)),_add(a,_mul(v,t))))


def _ray(p,d,t):
    a,b,c=t; u,v=_sub(b,a),_sub(c,a); h=_cross(d,v); det=_dot(u,h)
    if abs(det)<1e-14:return None
    s=_sub(p,a); x=_dot(s,h)/det
    if x < -1e-12 or x > 1+1e-12:return None
    q=_cross(s,u); y=_dot(d,q)/det
    if y < -1e-12 or x+y > 1+1e-12:return None
    return _dot(v,q)/det


def _triangle_distance(a,b):
    for source,target in ((a,b),(b,a)):
        for i in range(3):
            p,q=source[i],source[(i+1)%3]
            hit=_ray(p,_sub(q,p),target)
            if hit is not None and 0<=hit<=1:return 0
    return min(*(_point_triangle(p,b) for p in a),*(_point_triangle(p,a) for p in b),
               *(_segment_distance(a[i],a[(i+1)%3],b[j],b[(j+1)%3]) for i in range(3) for j in range(3)))


def _adjacent_interference(a,b):
    for source,target in ((a,b),(b,a)):
        for i in range(3):
            hit=_ray(source[i],_sub(source[(i+1)%3],source[i]),target)
            if hit is not None and 1e-9<hit<1-1e-9:return True
    normal=_cross(_sub(a[1],a[0]),_sub(a[2],a[0]));unit=_mul(normal,1/_norm(normal))
    other=_cross(_sub(b[1],b[0]),_sub(b[2],b[0]))
    if _norm(_cross(unit,_mul(other,1/_norm(other))))>1e-10 or any(abs(_dot(_sub(p,a[0]),unit))>1e-9 for p in b):return False
    axis=max(range(3),key=lambda k:abs(unit[k]));axes=[k for k in range(3) if k!=axis]
    poly=[tuple(p[k] for k in axes) for p in a];clip=[tuple(p[k] for k in axes) for p in b]
    def cross(u,v,p):return (v[0]-u[0])*(p[1]-u[1])-(v[1]-u[1])*(p[0]-u[0])
    orientation=1 if cross(clip[0],clip[1],clip[2])>0 else -1
    for i,u in enumerate(clip):
        v=clip[(i+1)%3];output=[]
        for j,p in enumerate(poly):
            q=poly[(j+1)%len(poly)];dp=orientation*cross(u,v,p);dq=orientation*cross(u,v,q)
            if dp>=0:output.append(p)
            if (dp>=0)!=(dq>=0):
                t=dp/(dp-dq);output.append(tuple(p[k]+t*(q[k]-p[k]) for k in range(2)))
        poly=output
        if not poly:return False
    area=abs(sum(p[0]*poly[(i+1)%len(poly)][1]-p[1]*poly[(i+1)%len(poly)][0] for i,p in enumerate(poly)))/2
    return area>1e-12


def _bbox(triangles,ids):
    return tuple((min(triangles[i][j][k] for i in ids for j in range(3)),max(triangles[i][j][k] for i in ids for j in range(3))) for k in range(3))


def _tree(triangles,ids):
    box=_bbox(triangles,ids)
    if len(ids)<=8:return (box,ids,None)
    axis=max(range(3),key=lambda k:box[k][1]-box[k][0])
    ids=sorted(ids,key=lambda i:sum(p[axis] for p in triangles[i]))
    mid=len(ids)//2
    return (box,None,(_tree(triangles,ids[:mid]),_tree(triangles,ids[mid:])))


def _box_distance(a,b):
    return math.sqrt(sum(max(0,a[i][0]-b[i][1],b[i][0]-a[i][1])**2 for i in range(3)))


def _nearest(a,b,ta,tb,deadline, self_test=False,indices=None):
    best=math.inf; location=None; stack=[(ta,tb)]
    while stack:
        if time.monotonic()>deadline:raise TimeoutError('mesh_budget')
        na,nb=stack.pop()
        if _box_distance(na[0],nb[0])>best:continue
        if na[1] is not None and nb[1] is not None:
            for i in na[1]:
                for j in nb[1]:
                    if self_test and i>=j:continue
                    if self_test and set(indices[i]) & set(indices[j]):
                        if _adjacent_interference(a[i],b[j]):return 0,[i,j]
                        continue
                    d=_triangle_distance(a[i],b[j])
                    if d<best:best=d;location=[i,j]
                    if best<=1e-12:return best,location
        elif na[2] is not None:
            stack.extend((n,nb) for n in na[2])
        else:stack.extend((na,n) for n in nb[2])
    return best,location


def _inside(p,triangles):
    votes=[]
    for d in ((1,.371,.153),(.217,1,.419),(.119,.313,1)):
        hits=sorted(h for t in triangles if (h:=_ray(p,d,t)) is not None and h>1e-9)
        unique=[]
        for h in hits:
            if not unique or abs(h-unique[-1])>1e-8:unique.append(h)
        votes.append(len(unique)%2==1)
    return votes[0] if all(v == votes[0] for v in votes) else None


def _contains(p,triangles,tree,deadline):
    votes=[]
    for direction in ((1,.371,.153),(.217,1,.419),(.119,.313,1)):
        hits=[];stack=[tree]
        while stack:
            if time.monotonic()>deadline:raise TimeoutError('mesh_budget')
            node=stack.pop();low,high=0,math.inf
            for k,(a,b) in enumerate(node[0]):
                v,w=(a-p[k])/direction[k],(b-p[k])/direction[k]
                low=max(low,min(v,w));high=min(high,max(v,w))
            if low>high:continue
            if node[2]:stack.extend(node[2])
            else:
                for i in node[1]:
                    hit=_ray(p,direction,triangles[i])
                    if hit is not None and hit>1e-9:hits.append(hit)
        unique=[]
        for hit in sorted(hits):
            if not unique or abs(hit-unique[-1])>1e-8:unique.append(hit)
        votes.append(len(unique)%2==1)
    return votes[0] if all(v == votes[0] for v in votes) else None


def _point_distance(p,triangles,tree,deadline):
    best=math.inf;stack=[tree]
    box=tuple((v,v) for v in p)
    while stack:
        if time.monotonic()>deadline:raise TimeoutError('mesh_budget')
        node=stack.pop()
        if _box_distance(box,node[0])>best:continue
        if node[2]:stack.extend(node[2])
        else:best=min(best,*(_point_triangle(p,triangles[i]) for i in node[1]))
    return best


def _component_samples(vertices,faces):
    vertex_faces={}
    for i,f in enumerate(faces):
        for v in f:vertex_faces.setdefault(v,[]).append(i)
    seen=set();samples=[]
    for i,f in enumerate(faces):
        if i in seen:continue
        samples.append(tuple(vertices[f[0]]));stack=[i];seen.add(i)
        while stack:
            current=stack.pop()
            for v in faces[current]:
                for neighbor in vertex_faces[v]:
                    if neighbor not in seen:seen.add(neighbor);stack.append(neighbor)
    return samples


def check_meshes(meshes, *, budget_seconds=120, minimum_gap_mm=0):
    """Closed oriented triangle solids. Representation errors must be supplied.

    Missing export error certification is an unverified region. Contact and
    containment require topology/relationship review and never silently pass.
    """
    result=dict(state='passed',unit='mm',algorithm_version=ALGORITHM_VERSION,issues=[],pairs=[])
    deadline=time.monotonic()+budget_seconds; prepared=[]
    try:
        if not meshes:raise ValueError('no_entities')
        if sum(len(m['triangles']) for m in meshes)>1000000:raise ValueError('model_capacity')
        for index,m in enumerate(meshes):
            faces=m['triangles']; vertices=m['vertices']; edges={}
            if not faces or len(faces)>250000:raise ValueError('entity_capacity')
            if any(len(p)!=3 or not all(math.isfinite(v) for v in p) for p in vertices):raise ValueError('invalid_vertices')
            for f in faces:
                if len(f)!=3 or any(not isinstance(v,int) or v<0 or v>=len(vertices) for v in f):raise ValueError('invalid_triangle')
                for a,b in zip(f,f[1:]+f[:1]):edges.setdefault(tuple(sorted((a,b))),[]).append((a,b))
            if any(len(e)!=2 or e[0]!=e[1][::-1] for e in edges.values()):raise ValueError('open_or_inconsistent_mesh')
            triangles=[tuple(tuple(vertices[i]) for i in f) for f in faces]
            if any(_norm(_cross(_sub(t[1],t[0]),_sub(t[2],t[0])))<1e-18 for t in triangles):raise ValueError('degenerate_triangle')
            tree=_tree(triangles,list(range(len(faces))))
            distance,where=_nearest(triangles,triangles,tree,tree,deadline,True,faces)
            if distance<=TOLERANCE_MM:
                result['issues'].append(dict(code='self_intersection',entity=index,triangles=where));result['state']='failed'
            error=m.get('error_mm')
            if error is None or not math.isfinite(error) or error<0:
                result['issues'].append(dict(code='uncertified_export_error',entity=index));error=None
            samples=_component_samples(vertices,faces)
            # Additional face centres diagnose coplanar overlaps; components
            # supply the mandatory containment representatives for disjoint meshes.
            samples.extend(_mul(_add(_add(t[0],t[1]),t[2]),1/3) for t in triangles[:32])
            prepared.append((triangles,tree,error,samples))
        for i,(a,ta,ea,sa) in enumerate(prepared):
            for j in range(i+1,len(prepared)):
                b,tb,eb,sb=prepared[j]
                d,where=_nearest(a,b,ta,tb,deadline)
                uncertainty=ea+eb if ea is not None and eb is not None else None
                pair=dict(entities=[i,j],mesh_distance_mm=d,triangles=where,distance_interval_mm=[max(0,d-uncertainty),d+uncertainty] if uncertainty is not None else None)
                # Probe vertices and face centres: catches overlapping coplanar boxes.
                margin=max(TOLERANCE_MM,uncertainty or 0)
                contained=False;ambiguous=False
                for samples,target,tree in ((sa,b,tb),(sb,a,ta)):
                    for p in samples:
                        inside=_contains(p,target,tree,deadline)
                        ambiguous|=inside is None
                        if inside is True and _point_distance(p,target,tree,deadline)>margin:
                            contained=True
                if contained and uncertainty is not None:
                    pair['state']='failed';pair['reason']='penetration_or_containment'
                elif contained or ambiguous:
                    pair['state']='unverified';pair['reason']='containment_or_ray_classification_uncertainty'
                elif uncertainty is not None and d-uncertainty>max(TOLERANCE_MM,minimum_gap_mm):pair['state']='passed'
                elif uncertainty is not None and d+uncertainty<minimum_gap_mm-TOLERANCE_MM:pair['state']='failed'
                else:pair['state']='unverified';pair['reason']='contact_or_representation_uncertainty'
                result['pairs'].append(pair)
                if pair['state']=='failed':result['state']='failed'
                elif pair['state']=='unverified' and result['state']=='passed':result['state']='unverified'
        if result['issues'] and result['state']=='passed':result['state']='unverified'
    except (ValueError,KeyError,TypeError,IndexError,TimeoutError) as exc:
        result['issues'].append(dict(code=str(exc)))
        if result['state']!='failed':result['state']='unverified'
    result['elapsed_seconds']=budget_seconds-max(0,deadline-time.monotonic())
    return result


def check_radial_model(result, faces, scale, budget_seconds=120):
    started=time.monotonic()
    for a,b in zip(faces,faces[1:]):
        if a is None or b is None:continue
        if a.get('requires_3d') or b.get('requires_3d'):
            result['issues'].append(dict(code='transformed_entity_requires_3d',surface=a['surface']))
            continue
        material=a['material'].strip().upper()
        if material in {'MIRROR','ABSORB'}:
            result['issues'].append(dict(code='reflective_path_requires_entity_model',surface=a['surface']));continue
        remaining=budget_seconds-(time.monotonic()-started)
        if remaining<=0:
            result['issues'].append(dict(code='calculation_budget'));break
        pair=check_radial_pair(a,b,a['thickness'],scale_mm=scale,budget_seconds=remaining)
        pair.update(surfaces=[a['surface'],b['surface']],medium='glass' if material else 'air',material=a['material'])
        if material and abs(a['mechanical_semi_diameter']-b['mechanical_semi_diameter'])*scale>1e-6:
            # Beyond the smaller boundary the solid requires an explicit edge
            # profile; extending either optical face would invent geometry.
            pair['issues'].append('unequal_mechanical_boundaries_require_edge_profile')
            if pair['state']=='passed':pair['state']='unverified'
        if 'position_radius_mm' in pair:
            from .geometry import _sag
            r=pair['position_radius_mm']
            pair['position_mm']=[r,0,a['z_mm']+_sag(a,(r/scale)**2)*scale]
        # The local axial thickness must agree with the actual global frame.
        if abs((b['z_mm']-a['z_mm'])-a['thickness']*scale)>1e-7:
            pair['state']='unverified';pair['issues'].append('inconsistent_global_spacing')
        result['rows'].append(pair)
    states=[p['state'] for p in result['rows']]
    result['state']='failed' if 'failed' in states else ('passed' if states and all(s=='passed' for s in states) and not result['issues'] and result['read_complete'] else 'unverified')
    result["elapsed_seconds"]=time.monotonic()-started
    return result


def surface_metric_bounds(face,kind,scale_mm=1,budget_seconds=.5):
    """Conservative maxima for supported radial definitions over mechanical radius."""
    end=face['mechanical_semi_diameter']**2
    deadline=time.monotonic()+budget_seconds
    def multiply(a,b):
        values=[x*y for x in a for y in b]
        return min(values),max(values)
    def second(lo,hi):
        c=1/face['radius'] if face['radius'] else 0
        q=(1+face.get('conic',0))*c*c
        ends=[1-q*lo,1-q*hi]
        if min(ends)<=0:return -math.inf,math.inf
        values=[c*q/(4*x**1.5) for x in ends]
        lower,upper=min(values),max(values)
        for i,a in enumerate(face.get('coefficients',[])):
            values=[a*(i+2)*(i+1)*x**i for x in (lo,hi)]
            lower+=min(values);upper+=max(values)
        return lower,upper
    def interval(lo,hi):
        if kind=='max_aspheric_departure':
            terms=[(face.get('quadratic',0),1)]+[(a,i+2)for i,a in enumerate(face.get('coefficients',[]))]
            lower=upper=0
            for a,power in terms:
                values=[a*x**power for x in (lo,hi)]
                lower+=min(values);upper+=max(values)
            return max(abs(lower),abs(upper))*scale_mm
        d=_derivative_bounds(face,lo,hi)
        slope=multiply((2*math.sqrt(lo),2*math.sqrt(hi)),d)
        maxs=max(map(abs,slope))
        if kind=='max_surface_slope':return math.atan(maxs)
        dd=second(lo,hi);radial=multiply((4*lo,4*hi),dd)
        zsecond=(2*d[0]+radial[0],2*d[1]+radial[1])
        mins=0 if slope[0]<=0<=slope[1] else min(map(abs,slope))
        return max(max(map(abs,zsecond))/(1+mins*mins)**1.5,2*max(map(abs,d))/math.sqrt(1+mins*mins))/scale_mm
    def exact(t):return interval(t,t)
    best=max(exact(t)for t in (0,end/2,end));queue=[(-interval(0,end),0,end)]
    iterations=0
    while queue and -queue[0][0]>best+1e-8 and iterations<20000 and time.monotonic()<deadline:
        bound,lo,hi=heapq.heappop(queue);mid=(lo+hi)/2
        if mid==lo or mid==hi:
            heapq.heappush(queue,(bound,lo,hi))
            break
        for a,b in ((lo,mid),(mid,hi)):
            best=max(best,exact((a+b)/2))
            heapq.heappush(queue,(-interval(a,b),a,b))
        iterations+=1
    upper=max(best,-queue[0][0] if queue else best)
    return [max(0,best-1e-10),upper+1e-10] if math.isfinite(upper) else None


def merge_native_relations(inferred,declared):
    """Attach one explicit declaration to an identical inferred relation."""
    result=[dict(r)for r in inferred]
    for declaration in declared:
        match=next((r for r in result if not r.get('id') and r.get('native_verified') is True
                    and r['kind']==declaration['kind']and set(r['entities'])==set(declaration['entities'])),None)
        if match is None:result.append(dict(declaration))
        else:
            verified=match['native_verified'];match.update(declaration);match['native_verified']=verified
            match['verification_source']='native_shared_boundary'
    return result


def native_containment_path(parents,child,ancestor):
    path=[];node=child
    while node is not None:
        if node in path or node not in parents:return None
        path.append(node);node=parents[node]
    return path[:path.index(ancestor)+1]if ancestor in path[1:]else None
