"""Interpret native triangle-list data without inventing an export error bound."""
import math
from .geometry_backend import UNIT_MM


def visualization_mesh(data, *, surfaces=None, object_id=None):
    scale=UNIT_MM.get(data.get('position_unit'))
    if scale is None:raise ValueError('unknown_export_units')
    v=data['vectors'];count=data['triangles']
    if not isinstance(count,int) or count<1 or count>250000:raise ValueError('entity_capacity')
    if any(len(v[k])!=3*count for k in ('x','y','z','surface','object')):raise ValueError('incomplete_triangle_vectors')
    vertices=[];triangles=[];lookup={}
    for start in range(0,3*count,3):
        if surfaces is not None and any(v['surface'][start+k] not in surfaces for k in range(3)):continue
        if object_id is not None and any(v['object'][start+k]!=object_id for k in range(3)):continue
        face=[]
        for k in range(3):
            p=tuple(float(v[key][start+k])*scale for key in ('x','y','z'))
            if not all(math.isfinite(x) for x in p):raise ValueError('nonfinite_export_vertex')
            if p not in lookup:lookup[p]=len(vertices);vertices.append(p)
            face.append(lookup[p])
        triangles.append(face)
    return dict(vertices=vertices,triangles=triangles,error_mm=None,
                source='native_shaded_model_triangle_list',surfaces=surfaces,object_id=object_id,
                precision_state='native_tessellation_error_unverified')
