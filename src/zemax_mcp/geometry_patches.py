"""Finite native optical patches for global three-dimensional distances."""
import math
from .geometry import _sag
from .geometry_kernel import _global_transform,_shapes,native_polynomial_lens


def native_patch(face,scale,target,region=None):
    from OCP.gp import gp_Pnt,gp_Dir,gp_Ax1
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Compound
    from OCP.GC import GC_MakeArcOfCircle
    radius=face['mechanical_semi_diameter']*scale
    definition=dict(rotation=face['rotation'],translation_mm=face['translation_mm'])
    if 'polynomial'in face:
        terms=[[i,j,c*scale/(face['normalization']*scale)**(i+j)]for i,j,c in face['polynomial']]
        local,error=native_polynomial_lens(dict(rotation=[1,0,0,0,1,0,0,0,1],translation_mm=[0,0,0],polynomials=[terms,terms],normalization_mm=1,thickness_mm=1,mechanical_radius_mm=radius,patch_only=True))
        return _global_transform(clip_local_patch(local,region,radius),definition),error
    def point(r):return gp_Pnt(r,0,_sag(face,(r/scale)**2)*scale)
    exact=face.get('conic',0)==0 and not face.get('quadratic',0)and not any(face.get('coefficients',[]))
    segments=[];error=0
    if exact:
        edge=BRepBuilderAPI_MakeEdge(point(0),point(radius)).Edge()if not face['radius']else BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(point(0),point(radius/2),point(radius)).Value()).Edge()
        segments=[edge]
    else:
        c=1/(face['radius']*scale)if face['radius']else 0;q=(1+face.get('conic',0))*c*c
        terms=[(2,face.get('quadratic',0)/scale)]+[(4+2*i,a/scale**(3+2*i))for i,a in enumerate(face.get('coefficients',[]))]
        stack=[(0,radius)]
        while stack:
            if len(stack)+len(segments)>8192:raise ValueError('surface_patch_capacity')
            lo,hi=stack.pop();denominator=min(1-q*lo*lo,1-q*hi*hi)
            if denominator<=0:raise ValueError('surface_patch_sag_domain')
            curvature=abs(c)/denominator**1.5+sum(abs(a)*n*(n-1)*hi**(n-2)for n,a in terms)
            bound=curvature*(hi-lo)**2/8
            if bound>target:
                mid=(lo+hi)/2
                if mid in [lo,hi]:raise ValueError('surface_patch_precision_limit')
                stack.extend([(mid,hi),(lo,mid)])
            else:
                error=max(error,bound);segments.append(BRepBuilderAPI_MakeEdge(point(lo),point(hi)).Edge())
    compound=TopoDS_Compound();builder=BRep_Builder();builder.MakeCompound(compound)
    for edge in segments:builder.Add(compound,BRepPrimAPI_MakeRevol(edge,gp_Ax1(gp_Pnt(0,0,0),gp_Dir(0,0,1)),2*math.pi).Shape())
    return _global_transform(clip_local_patch(compound,region,radius),definition),error+1e-10


def measure_surface_gap(request):
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    first,ea=native_patch(request['front'],request['scale_mm'],request['target_mm'],request.get('region'))
    second,eb=native_patch(request['back'],request['scale_mm'],request['target_mm'],request.get('region'))
    distance=BRepExtrema_DistShapeShape(first,second)
    if not distance.IsDone():return dict(id=request['id'],state='unverified',reason='surface_patch_distance_failed')
    value=distance.Value();error=ea+eb+2e-7+(2e-6 if request.get('region')else 0)
    point=distance.PointOnShape1(1)
    return dict(id=request['id'],state='measured',source='native_global_finite_surface_distance',distance_mm=value,interval_mm=[max(0,value-error),value+error],representation_error_mm=[ea,eb],region=request.get('region',{}),region_frame='each_surface_local_xy_mm',position_mm=[point.X(),point.Y(),point.Z()])


def clip_local_patch(shape,region,radius):
    if not region:return shape
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common,BRepAlgoAPI_Cut
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.TopAbs import TopAbs_FACE
    from OCP.gp import gp_Pnt,gp_Ax2,gp_Dir
    bounds=Bnd_Box();BRepBndLib.Add_s(shape,bounds)
    zmin=bounds.CornerMin().Z()-1;zmax=bounds.CornerMax().Z()+1
    rectangular={f'{a}_{end}_mm'for a in 'xy'for end in ['min','max']}
    if set(region)==rectangular:
        x0,x1,y0,y1=(region[k]for k in ['x_min_mm','x_max_mm','y_min_mm','y_max_mm'])
        if x0>=x1 or y0>=y1:raise ValueError('invalid_rectangular_region')
        cutter=BRepPrimAPI_MakeBox(gp_Pnt(x0,y0,zmin),x1-x0,y1-y0,zmax-zmin).Shape()
    elif not set(region)-{'r_min_mm','r_max_mm'}:
        inner=region.get('r_min_mm',0);outer=region.get('r_max_mm',radius)
        if not 0<=inner<outer<=radius:raise ValueError('engineering_region_outside_boundary')
        axis=gp_Ax2(gp_Pnt(0,0,zmin),gp_Dir(0,0,1));cutter=BRepPrimAPI_MakeCylinder(axis,outer,zmax-zmin).Shape()
        if inner:
            cut=BRepAlgoAPI_Cut(cutter,BRepPrimAPI_MakeCylinder(axis,inner,zmax-zmin).Shape())
            if not cut.IsDone():raise ValueError('surface_region_boolean_failed')
            cutter=cut.Shape()
    else:raise ValueError('engineering_region_adapter_required')
    intersection=BRepAlgoAPI_Common(shape,cutter)
    if not intersection.IsDone():raise ValueError('surface_region_boolean_failed')
    result=intersection.Shape()
    if not list(_shapes(result,TopAbs_FACE)):raise ValueError('surface_region_empty')
    return result
