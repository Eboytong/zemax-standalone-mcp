"""STEP boundary representations; only source adapters supply representation bounds.

OpenCascade tolerances describe the imported representation. They are recorded
separately from the error between that representation and the optical model.
"""
import math
import time

ALGORITHM_VERSION = 'occt-step-1'
TOLERANCE_MM = 1e-6


def _global_transform(shape,definition):
    from OCP.gp import gp_Trsf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    matrix=definition['rotation'];translation=definition['translation_mm']
    if len(matrix)!=9 or len(translation)!=3 or not all(math.isfinite(v) for v in matrix+translation):
        raise ValueError('invalid_native_transform')
    for i in range(3):
        for j in range(3):
            if abs(sum(matrix[3*k+i]*matrix[3*k+j] for k in range(3))-(1 if i==j else 0))>1e-9:
                raise ValueError('nonrigid_native_transform')
    trsf=gp_Trsf();values=[]
    for i in range(3):values.extend([*matrix[3*i:3*i+3],translation[i]])
    trsf.SetValues(*values)
    return BRepBuilderAPI_Transform(shape,trsf,True).Shape()


def native_polynomial_lens(definition):
    """Polynomial graph caps are exact tensor Bezier patches on a circular edge.

    Optical x/y polynomials are converted algebraically, without sampled fits.
    Curve construction uses an explicit tolerance, separate from BRep tolerance.
    """
    from OCP.gp import gp_Pnt,gp_Pnt2d,gp_Dir2d,gp_Ax2d
    from OCP.Geom import Geom_BezierSurface
    from OCP.Geom2d import Geom2d_Circle
    from OCP.collections import Array2_gp_Pnt
    from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge,BRepBuilderAPI_MakeWire,
        BRepBuilderAPI_MakeFace,BRepBuilderAPI_Sewing,BRepBuilderAPI_MakeSolid)
    from OCP.BRepFill import BRepFill
    from OCP.BRepLib import BRepLib
    from OCP.TopoDS import TopoDS
    from OCP.TopAbs import TopAbs_SHELL
    from fractions import Fraction
    radius=definition['mechanical_radius_mm'];normalization=definition['normalization_mm']
    if radius<=0 or normalization<=0:raise ValueError('invalid_polynomial_domain')
    caps=[];edges=[];rounding=0.
    exact_radius=Fraction(radius);exact_normalization=Fraction(normalization)
    for index,terms in enumerate(definition['polynomials']):
        nx=max([1]+[t[0] for t in terms]);ny=max([1]+[t[1] for t in terms])
        if nx>20 or ny>20:raise ValueError('polynomial_degree_capacity')
        power={}
        for i,j,c in terms:
            if i<0 or j<0 or not math.isfinite(c):raise ValueError('invalid_polynomial_term')
            c=Fraction(c)*(exact_radius/exact_normalization)**(i+j)
            for k in range(i+1):
                for l in range(j+1):
                    value=c*math.comb(i,k)*math.comb(j,l)*2**(k+l)*(-1)**(i+j-k-l)
                    power[k,l]=power.get((k,l),0)+value
        points=Array2_gp_Pnt(1,nx+1,1,ny+1)
        for i in range(nx+1):
            for j in range(ny+1):
                z=sum(c*Fraction(math.comb(i,k),math.comb(nx,k))*Fraction(math.comb(j,l),math.comb(ny,l))
                      for (k,l),c in power.items() if k<=i and l<=j)
                coordinates=[exact_radius*(Fraction(2*i,nx)-1),exact_radius*(Fraction(2*j,ny)-1),
                             z+index*Fraction(definition['thickness_mm'])]
                values=[float(v) for v in coordinates]
                rounding=max(rounding,sum(float(abs(Fraction(v)-exact)) for v,exact in zip(values,coordinates)))
                points.SetValue(i+1,j+1,gp_Pnt(*values))
        surface=Geom_BezierSurface(points)
        circle=Geom2d_Circle(gp_Ax2d(gp_Pnt2d(.5,.5),gp_Dir2d(1,0)),.5)
        edge=BRepBuilderAPI_MakeEdge(circle,surface).Edge()
        if not BRepLib.BuildCurves3d_s(edge,1e-9):raise ValueError('polynomial_edge_construction_failed')
        cap=BRepBuilderAPI_MakeFace(surface,BRepBuilderAPI_MakeWire(edge).Wire(),True).Face()
        caps.append(cap);edges.append(edge)
    if definition.get('patch_only'):return _global_transform(caps[0],definition),rounding+1e-9
    sewing=BRepBuilderAPI_Sewing(1e-8)
    caps[0].Reverse()
    for cap in caps:sewing.Add(cap)
    sewing.Add(BRepFill.Face_s(edges[0],edges[1]));sewing.Perform()
    shells=list(_shapes(sewing.SewedShape(),TopAbs_SHELL))
    if len(shells)!=1:raise ValueError('polynomial_shell_not_closed')
    solid=BRepBuilderAPI_MakeSolid(TopoDS.Shell(shells[0])).Solid()
    if not BRepLib.OrientClosedSolid_s(solid):raise ValueError('polynomial_solid_orientation')
    # Bernstein convex hull bounds coefficient conversion error over the domain.
    if rounding>1e-6:raise ValueError('polynomial_roundoff_bound_exceeded')
    return _global_transform(solid,definition),rounding+1e-9


def native_radial_lens(definition):
    """Bound each profile chord by sup(|z''|) * dr**2 / 8, then revolve."""
    from OCP.gp import gp_Pnt,gp_Dir,gp_Ax1
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge,BRepBuilderAPI_MakeWire,BRepBuilderAPI_MakeFace
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol
    radius=definition['mechanical_radius_mm'];target=definition.get('target_error_mm',1e-3)
    if radius<=0 or not 0<target<=1e-3:raise ValueError('invalid_profile_precision')
    paths=[];error=0.
    for i,face in enumerate(definition['profiles']):
        R=face['radius_mm'];c=1/R if R else 0.;q=(1+face['conic'])*c*c
        polynomial=face['terms']
        def sag(r):
            denominator=1-q*r*r
            if denominator<=0:raise ValueError('radial_sag_domain')
            return c*r*r/(1+math.sqrt(denominator))+sum(value*r**power for power,value in polynomial)
        def curvature_bound(lo,hi):
            denominator=min(1-q*lo*lo,1-q*hi*hi)
            if denominator<=0:raise ValueError('radial_sag_domain')
            return abs(c)/denominator**1.5+sum(abs(value)*power*(power-1)*hi**(power-2) for power,value in polynomial if power>=2)
        stack=[(0.,radius)];points=[(0.,sag(0.))]
        while stack:
            if len(stack)+len(points)>8192:raise ValueError('radial_profile_capacity')
            lo,hi=stack.pop();bound=curvature_bound(lo,hi)*(hi-lo)**2/8
            if not math.isfinite(bound):raise ValueError('radial_profile_bound_unverified')
            if bound>target:
                mid=(lo+hi)/2
                if mid==lo or mid==hi:raise ValueError('radial_profile_precision_limit')
                stack.extend([(mid,hi),(lo,mid)])
            else:
                error=max(error,bound);points.append((hi,sag(hi)))
        paths.append([gp_Pnt(r,0,z+i*definition['thickness_mm']) for r,z in points])
    points=paths[0]+list(reversed(paths[1]));wire=BRepBuilderAPI_MakeWire()
    for a,b in zip(points,points[1:]+points[:1]):
        if a.Distance(b)>1e-12:wire.Add(BRepBuilderAPI_MakeEdge(a,b).Edge())
    face=BRepBuilderAPI_MakeFace(wire.Wire()).Face()
    shape=BRepPrimAPI_MakeRevol(face,gp_Ax1(gp_Pnt(0,0,0),gp_Dir(0,0,1)),2*math.pi).Shape()
    return _global_transform(shape,definition),math.nextafter(error+1e-10,math.inf)


def _shapes(shape, kind):
    from OCP.TopExp import TopExp_Explorer
    explorer=TopExp_Explorer(shape,kind)
    while explorer.More():
        yield explorer.Current()
        explorer.Next()


def _properties(shape, volume=False):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    props=GProp_GProps()
    (BRepGProp.VolumeProperties_s if volume else BRepGProp.SurfaceProperties_s)(shape,props,1e-10)
    return abs(props.Mass())


def read_step(path):
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.collections import Sequence_TCollection_AsciiString
    reader=STEPControl_Reader()
    if reader.ReadFile(str(path))!=IFSelect_RetDone:
        raise ValueError('step_read_failed')
    length,angle,solid_angle=(Sequence_TCollection_AsciiString() for _ in range(3))
    reader.FileUnits(length,angle,solid_angle)
    units=[length.Value(i).ToCString() for i in range(1,length.Length()+1)]
    if not units:
        raise ValueError('step_units_missing')
    reader.SetSystemLengthUnit(1.0)
    if not reader.TransferRoots():
        raise ValueError('step_transfer_failed')
    return reader.OneShape(),units


def native_spherical_lens(definition):
    """Exact sphere/plane profile, cylindrical declared edge, native global frame."""
    from OCP.gp import gp_Pnt,gp_Dir,gp_Ax1,gp_Trsf
    from OCP.GC import GC_MakeArcOfCircle
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge,BRepBuilderAPI_MakeWire,BRepBuilderAPI_MakeFace,BRepBuilderAPI_Transform
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol
    radius=definition['mechanical_radius_mm']
    thickness=definition['thickness_mm']
    def point(r,R,z):
        sag=math.copysign(abs(R)-math.sqrt(R*R-r*r),R) if R else 0
        return gp_Pnt(r,0,z+sag)
    front,back=definition['radii_mm']
    f0,f1=point(0,front,0),point(radius,front,0)
    b0,b1=point(0,back,thickness),point(radius,back,thickness)
    def curve(a,b,R,z,reverse=False):
        if not R:return BRepBuilderAPI_MakeEdge(a,b).Edge()
        middle=point(radius/2,R,z)
        return BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(a,middle,b).Value()).Edge()
    wire=BRepBuilderAPI_MakeWire()
    for edge in (curve(f0,f1,front,0),BRepBuilderAPI_MakeEdge(f1,b1).Edge(),curve(b1,b0,back,thickness),BRepBuilderAPI_MakeEdge(b0,f0).Edge()):
        wire.Add(edge)
    face=BRepBuilderAPI_MakeFace(wire.Wire()).Face()
    shape=BRepPrimAPI_MakeRevol(face,gp_Ax1(gp_Pnt(0,0,0),gp_Dir(0,0,1)),2*math.pi).Shape()
    return _global_transform(shape,definition)


def _inspect(entity):
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRep import BRep_Tool
    from OCP.TopoDS import TopoDS
    from OCP.TopAbs import TopAbs_SOLID,TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX
    from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
    representation_error=entity.get('representation_error_mm')
    if entity.get('native_definition',{}).get('kind')=='box':
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.gp import gp_Pnt
        definition=entity['native_definition'];hx,hy,length=definition['half_x_mm'],definition['half_y_mm'],definition['length_mm']
        if not all(math.isfinite(v)and v>0 for v in [hx,hy,length]):raise ValueError('invalid_native_box_dimensions')
        shape=_global_transform(BRepPrimAPI_MakeBox(gp_Pnt(-hx,-hy,0),2*hx,2*hy,length).Shape(),definition)
        units=['mm'];representation_error=0
    elif entity.get('native_definition',{}).get('kind')=='radial':
        shape,representation_error=native_radial_lens(entity['native_definition']);units=['mm']
    elif entity.get('native_definition',{}).get('kind')=='polynomial':
        shape,representation_error=native_polynomial_lens(entity['native_definition']);units=['mm']
    elif entity.get('native_definition'):
        shape,units=native_spherical_lens(entity['native_definition']),['mm']
    else:shape,units=read_step(entity['path'])
    solids=list(_shapes(shape,TopAbs_SOLID))
    if not solids:
        raise ValueError('step_has_no_closed_solids')
    if not BRepCheck_Analyzer(shape).IsValid():
        raise ValueError('invalid_boundary_representation')
    analyzer=BOPAlgo_ArgumentAnalyzer()
    analyzer.SetShape1(shape)
    analyzer.SelfInterMode=True
    analyzer.Perform()
    if analyzer.HasFaulty():
        raise ValueError('self_interference')
    tolerances=[]
    for kind,cast in ((TopAbs_FACE,TopoDS.Face),(TopAbs_EDGE,TopoDS.Edge),(TopAbs_VERTEX,TopoDS.Vertex)):
        tolerances.extend(BRep_Tool.Tolerance_s(cast(s)) for s in _shapes(shape,kind))
    tolerance=max(tolerances,default=0)
    error=representation_error
    if error is not None and (not math.isfinite(error) or error<0):
        raise ValueError('invalid_representation_error')
    fact=dict(id=entity['id'],state='passed' if error is not None else 'unverified',
              source=entity.get('source'),material=entity.get('material'),inside_of=entity.get('inside_of'),unit='mm',source_units=units,solid_count=len(solids),
              volume_mm3=_properties(shape,True),surface_area_mm2=_properties(shape),
              kernel_tolerance_mm=tolerance,representation_error_mm=error,
              healing_applied=False)
    if entity.get('native_definition'):
        fact['native_definition']=entity['native_definition']
        fact['definition_length_unit']='mm'
    fact['wall_measurements']=[]
    faces=list(_shapes(shape,TopAbs_FACE))
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    fact['faces']=[]
    for index,face in enumerate(faces,1):
        typed=TopoDS.Face(face);props=GProp_GProps()
        BRepGProp.SurfaceProperties_s(typed,props,1e-10)
        center=props.CentreOfMass()
        fact['faces'].append(dict(id=index,geometry_type=str(BRepAdaptor_Surface(typed).GetType()),
            area_mm2=props.Mass(),center_mm=[center.X(),center.Y(),center.Z()],orientation=str(typed.Orientation())))
        from OCP.BRepLProp import BRepLProp_SLProps
        from OCP.TopAbs import TopAbs_REVERSED
        adaptor=BRepAdaptor_Surface(typed)
        u=(adaptor.FirstUParameter()+adaptor.LastUParameter())/2
        v=(adaptor.FirstVParameter()+adaptor.LastVParameter())/2
        if math.isfinite(u)and math.isfinite(v):
            differential=BRepLProp_SLProps(adaptor,u,v,1,1e-10)
            if differential.IsNormalDefined():
                normal=differential.Normal();sign=-1 if typed.Orientation()==TopAbs_REVERSED else 1
                fact['faces'][-1]['outward_normal']=[sign*normal.X(),sign*normal.Y(),sign*normal.Z()]
                fact['faces'][-1]['normal_source']='oriented support surface at parameter midpoint'
    for request in entity.get('wall_requests',[]):
        measurement=dict(id=request['id'],state='unverified',faces=request['faces'])
        if request.get('region'):
            measurement['reason']='wall_region_adapter_required'
        elif error is None:
            measurement['reason']='source_representation_unverified'
        elif any(i<1 or i>len(faces) for i in request['faces']):
            measurement['reason']='wall_face_identity_missing'
        else:
            from OCP.BRepExtrema import BRepExtrema_DistShapeShape
            a,b=(faces[i-1] for i in request['faces'])
            distance=BRepExtrema_DistShapeShape(a,b)
            if distance.IsDone():
                value=distance.Value();uncertainty=2*(error+tolerance)
                p=distance.PointOnShape1(1)
                measurement.update(state='measured',interval_mm=[max(0,value-uncertainty),value+uncertainty],position_mm=[p.X(),p.Y(),p.Z()])
        fact['wall_measurements'].append(measurement)
    return shape,fact


def _pair(a,b,fa,fb,relations,minimum_gap_mm):
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    distance=BRepExtrema_DistShapeShape(a,b)
    if not distance.IsDone() or distance.NbSolution()<1:
        raise ValueError('distance_not_completed')
    d=distance.Value()
    p=distance.PointOnShape1(1)
    ea,eb=fa['representation_error_mm'],fb['representation_error_mm']
    error=None if ea is None or eb is None else ea+eb+fa['kernel_tolerance_mm']+fb['kernel_tolerance_mm']
    result=dict(entities=[fa['id'],fb['id']],distance_mm=d,
                position_mm=[p.X(),p.Y(),p.Z()],state='unverified',
                distance_interval_mm=None if error is None else [max(0,d-error),d+error])
    common=BRepAlgoAPI_Common(a,b)
    if not common.IsDone():
        result['reason']='intersection_not_completed'
        return result
    overlap=_properties(common.Shape(),True)
    result['intersection_volume_mm3']=overlap
    relation=next((r for r in relations if set(r['entities'])==set(result['entities'])),None)
    relation_kind=relation.get('kind') if relation else None
    if relation:result['relationship']=dict(relation)
    if error is None:
        result['reason']='source_representation_unverified'
    elif overlap>(fa['surface_area_mm2']+fb['surface_area_mm2'])*(error+TOLERANCE_MM):
        if relation_kind in {'nested','intentional_overlap'} and relation.get('native_verified') is True:
            uncertainty=(fa['surface_area_mm2']+fb['surface_area_mm2'])*(error+TOLERANCE_MM)
            child=relation.get('native_child')
            contained_volume=fa['volume_mm3']if child==fa['id']else fb['volume_mm3']if child==fb['id']else min(fa['volume_mm3'],fb['volume_mm3'])
            if relation_kind=='nested' and abs(overlap-contained_volume)>uncertainty:
                result.update(state='failed',reason='nested_region_not_contained')
            else:result.update(state='passed',relation=relation_kind)
        else:
            result.update(state='failed',reason='solid_penetration_or_containment')
    elif overlap>TOLERANCE_MM**3:
        result['reason']='intersection_within_representation_uncertainty'
    elif d-error>max(TOLERANCE_MM,minimum_gap_mm):
        result['state']='passed'
    elif d+error<minimum_gap_mm-TOLERANCE_MM:
        result.update(state='failed',reason='minimum_gap_violated')
    elif relation_kind in {'contact','cemented'} and d+error<=TOLERANCE_MM and minimum_gap_mm==0:
        result.update(state='passed',relation=relation_kind)
    else:
        result['reason']='contact_or_representation_uncertainty'
    return result


def check_step_entities(entities, *, relations=(), budget_seconds=120, minimum_gap_mm=0, progress=None, gap_requests=()):
    start=time.monotonic()
    result=dict(state='passed',unit='mm',algorithm_version=ALGORITHM_VERSION,
                entities=[],pairs=[],issues=[],read_complete=False)
    prepared=[]
    try:
        if not entities:
            raise ValueError('no_entities')
        ids=[e['id'] for e in entities]
        if len(set(ids))!=len(ids):
            raise ValueError('duplicate_entity_identity')
        seen_relations=set()
        for relation in relations:
            if len(relation.get('entities',[]))!=2 or any(i not in ids for i in relation['entities']):
                raise ValueError('relationship_identity_missing')
            pair=frozenset(relation['entities'])
            if pair in seen_relations:raise ValueError('relationship_conflict')
            seen_relations.add(pair)
        for entity in entities:
            if time.monotonic()-start>=budget_seconds:
                raise TimeoutError('geometry_budget')
            shape,fact=_inspect(entity)
            prepared.append(shape)
            result['entities'].append(fact)
            if progress:progress(result)
        for i,a in enumerate(prepared):
            for j in range(i+1,len(prepared)):
                if time.monotonic()-start>=budget_seconds:
                    raise TimeoutError('geometry_budget')
                result['pairs'].append(_pair(a,prepared[j],result['entities'][i],result['entities'][j],relations,minimum_gap_mm))
                if progress:progress(result)
        result['gap_measurements']=[measure_selected_solids(request,entities,prepared,result['entities'],start+budget_seconds)for request in gap_requests]
        result['media']=material_regions(entities,prepared,result['entities'],result['pairs'],start+budget_seconds)
        result['media_state']='unverified'
        if result['media']and all(r['state']=='measured'for r in result['media']):
            result['media_state']='partial'if any(r.get('boundary_mapping_state')=='face_mapping_required'for r in result['media'])else'measured'
        result['read_complete']=True
    except (ValueError,RuntimeError,KeyError,TypeError,TimeoutError) as exc:
        result['issues'].append(dict(code=str(exc)))
    states=[x['state'] for x in result['entities']+result['pairs']]
    result['state']='failed' if 'failed' in states else ('passed' if states and all(s=='passed' for s in states) and result['read_complete'] else 'unverified')
    result['elapsed_seconds']=time.monotonic()-start
    return result


def material_regions(inputs,shapes,facts,pairs,deadline):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    indexed={f['id']:i for i,f in enumerate(facts)}
    rows=[];interfaces={}
    for entity,shape,fact in zip(inputs,shapes,facts):
        parent=entity.get('inside_of');children=[e['id']for e in inputs if e.get('inside_of')==entity['id']]
        row=dict(entity=entity['id'],material=entity.get('material'),parent=parent,children=children,
                 gross_volume_mm3=fact['volume_mm3'],state='unverified',unit='mm3',source='native_material_and_closed_solid_boolean')
        rows.append(row)
        ancestry=set();node=entity['id']
        while node is not None:
            if node in ancestry:row['reason']='medium_parent_cycle';break
            ancestry.add(node)
            if node not in indexed:row['reason']='medium_parent_missing';break
            node=inputs[indexed[node]].get('inside_of')
        if 'reason'in row:continue
        if entity.get('material') is None:
            row['reason']='native_material_unavailable';continue
        if parent is not None:
            host_pair=next((p for p in pairs if set(p['entities'])=={entity['id'],parent}),None)
            uncertainty=(fact['surface_area_mm2']+facts[indexed[parent]]['surface_area_mm2'])*TOLERANCE_MM
            if host_pair is None or abs(host_pair.get('intersection_volume_mm3',-1)-fact['volume_mm3'])>uncertainty:
                row['reason']='medium_not_contained_in_native_parent';continue
        row['boundaries']=[dict(entity=entity['id'],normal_sign=1,exterior_container=parent or 'system_ambient')]+[
            dict(entity=child,normal_sign=-1,excluded_region=child)for child in children]
        involved=[p for p in pairs if entity['id']in p['entities']]
        if fact['state']!='passed' or any(p['state']!='passed'for p in involved):
            row['reason']='medium_boundary_or_relationship_unverified';continue
        row['interfaces']=[]
        for pair in involved:
            if pair.get('relation')not in {'contact','cemented'}:continue
            key=tuple(pair['entities']);ia,ib=(indexed[k]for k in key)
            if key not in interfaces:interfaces[key]=shared_material_faces(shapes[ia],shapes[ib],facts[ia],facts[ib],deadline)
            other=next(k for k in key if k!=entity['id'])
            patches=interfaces[key]
            row['interfaces'].append(dict(other_entity=other,other_material=facts[indexed[other]]['material'],
                relationship=pair['relation'],state='mapped'if patches else'contact_without_shared_area',patches=patches))
        row['boundary_mapping_state']='face_mapping_required'if any(i['state']!='mapped'for i in row['interfaces'])else'entity_boundary'
        remaining=shape
        for child in children:
            if time.monotonic()>deadline:raise TimeoutError('geometry_budget')
            cut=BRepAlgoAPI_Cut(remaining,shapes[indexed[child]])
            if not cut.IsDone():row['reason']='medium_boolean_not_completed';break
            remaining=cut.Shape()
        if 'reason'not in row:
            row.update(state='measured',effective_volume_mm3=_properties(remaining,True))
    return rows


def shared_material_faces(a,b,fa,fb,deadline):
    """Intersect trimmed boundary faces; solid common omits zero-volume interfaces."""
    from OCP.TopAbs import TopAbs_FACE
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    def faces(shape):
        rows=[]
        for i,face in enumerate(_shapes(shape,TopAbs_FACE)):
            bounds=Bnd_Box();BRepBndLib.Add_s(face,bounds)
            rows.append((i,face,bounds))
        return rows
    patches=[]
    for ia,first,ba in faces(a):
        for ib,second,bb in faces(b):
            if time.monotonic()>deadline:raise TimeoutError('geometry_budget')
            if ba.IsOut(bb):continue
            common=BRepAlgoAPI_Common(first,second)
            if not common.IsDone():raise ValueError('medium_interface_boolean_failed')
            area=_properties(common.Shape())
            if area<=TOLERANCE_MM**2:continue
            patches.append(dict(area_mm2=area,faces=[dict(entity=f['id'],face=f['faces'][index]['id'],material=f['material'],
                outward_normal=f['faces'][index].get('outward_normal'))for f,index in [(fa,ia),(fb,ib)]],
                source='trimmed_boundary_face_intersection'))
    return patches


def measure_selected_solids(request,inputs,shapes,facts,deadline):
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_SOLID
    result=dict(id=request['id'],entities=request['entities'],state='unverified',region=request.get('region',{}),source='closed_solid_distance')
    indexed={e['id']:i for i,e in enumerate(inputs)}
    if any(k not in indexed for k in request['entities']):return dict(result,reason='requested_entity_unavailable')
    indices=[indexed[k]for k in request['entities']]
    if any(facts[i]['representation_error_mm']is None for i in indices):return dict(result,reason='source_representation_unverified')
    selected=[shapes[i]for i in indices];region=request.get('region',{})
    if region:
        keys={f'{a}_{end}_mm'for a in 'xyz'for end in ['min','max']}
        if set(region)!=keys or any(region[f'{a}_min_mm']>=region[f'{a}_max_mm']for a in 'xyz'):
            return dict(result,reason='invalid_global_box_region')
        box=BRepPrimAPI_MakeBox(gp_Pnt(*[region[f'{a}_min_mm']for a in 'xyz']),*[region[f'{a}_max_mm']-region[f'{a}_min_mm']for a in 'xyz']).Shape()
        for i,shape in enumerate(selected):
            if time.monotonic()>deadline:raise TimeoutError('geometry_budget')
            common=BRepAlgoAPI_Common(shape,box)
            if not common.IsDone():return dict(result,reason='region_intersection_failed')
            selected[i]=common.Shape()
            if not list(_shapes(selected[i],TopAbs_SOLID)):return dict(result,reason='region_has_no_selected_solid')
        result['source']='global_box_clipped_solid_distance'
    distance=BRepExtrema_DistShapeShape(*selected)
    if not distance.IsDone():return dict(result,reason='selected_solid_distance_failed')
    value=distance.Value();error=sum(facts[i]['representation_error_mm']+facts[i]['kernel_tolerance_mm']for i in indices)+(2*TOLERANCE_MM if region else 0)
    point=distance.PointOnShape1(1)
    result.update(state='measured',distance_mm=value,interval_mm=[max(0,value-error),value+error],position_mm=[point.X(),point.Y(),point.Z()])
    return result
