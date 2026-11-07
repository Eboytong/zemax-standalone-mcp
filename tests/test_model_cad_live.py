"""Installed ASCII/binary STL meshes define independent native hit references."""
import asyncio,json,math
from pathlib import Path
import pytest
from support.native import execute
from support.nsc import setup,update,trace
from support.mesh_reference import triangles,intersect,dot


@pytest.mark.zemax
@pytest.mark.parametrize('name',['block.stl','oval.stl','sphere.stl','torus.stl','wedge.stl'])
def test_installed_mesh_geometry_native(name):
    async def work(e):
        path=Path.home()/'Documents/Zemax/Objects/CAD Files'/name;mesh=triangles(path)
        bounds=[[min(p[i]for triangle in mesh for p in triangle),max(p[i]for triangle in mesh for p in triangle)]for i in range(3)]
        # Fixed interior barycentric points supply candidate axes without using native hits.
        candidate=None
        for triangle in mesh:
            p=[.23*triangle[0][i]+.31*triangle[1][i]+.46*triangle[2][i]for i in range(3)]
            origin=[p[0],p[1],bounds[2][0]-2]
            try:
                hit=intersect(mesh,origin,[0,0,1])
                if abs(hit['normal'][2])<.5:continue
                candidate=(origin,hit);break
            except ValueError:continue
        assert candidate;origin,expected=candidate
        await setup(e,2)
        await update(e,[dict(object=1,object_type='SourceRay',x=origin[0],y=origin[1],z=origin[2],data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),
            dict(object=2,object_type='CADPartSTL',file1=name,material='MIRROR')])
        saved=e.folder/'mesh.zos';await e.call('save_lens_as',dict(path=str(saved)))
        records=[]
        for transformed in (False,True):
            tx,ty=map(math.radians,(7,-11))if transformed else(0,0)
            cx,sx,cy,sy=math.cos(tx),math.sin(tx),math.cos(ty),math.sin(ty)
            rotation=[[cy,0,sy],[sx*sy,cx,-sx*cy],[-cx*sy,sx,cx*cy]];translation=[1,-2,5]if transformed else[0,0,0]
            def rotate(p):return [dot(r,p)for r in rotation]
            def position(p):return [a+b for a,b in zip(rotate(p),translation)]
            source=position(origin);direction=rotate([0,0,1]);point=position(expected['position'])
            normal=expected['normal']
            if normal[2]>0:normal=[-x for x in normal]
            reflection=rotate([d-2*normal[2]*n for d,n in zip([0,0,1],normal)])
            await update(e,[dict(object=1,x=source[0],y=source[1],z=source[2],data=dict(XCosine=direction[0],YCosine=direction[1],ZCosine=direction[2])),
                dict(object=2,x=translation[0],y=translation[1],z=translation[2],tilt_x=7 if transformed else 0,tilt_y=-11 if transformed else 0)])
            saved=e.folder/f'mesh_{transformed}.zos';await e.call('save_lens_as',dict(path=str(saved)))
            for reload in (False,True):
                if reload:await e.call('open_lens',dict(path=str(saved)))
                _,segments=await trace(e,f'mesh_{transformed}_{reload}',use_polarization=True)
                index=next(i for i,r in enumerate(segments)if r['HitObject']==2);hit=segments[index]
                for axis,v in zip('XYZ',point):e.check('STL signed-transform intersection mm '+axis,hit[axis],v)
                for axis,v in zip(('XNorm','YNorm','ZNorm'),rotate(normal)):e.check('STL outward incident-facing normal '+axis,hit[axis],v)
                assert index+1<len(segments)
                for axis,v in zip('LMN',reflection):e.check('STL reflected direction '+axis,segments[index+1][axis],v)
                assert 0<segments[index+1]['Intensity']<=1
                records.append(dict(transformed=transformed,reloaded=reload,expected_position=point,expected_normal=rotate(normal),
                    expected_reflection=reflection,hit=hit,material_power_scope='MIRROR native power bounded; optical constants not independently reconstructed'))
        (e.folder/'mesh-reference.json').write_text(json.dumps(dict(source=str(path),triangles=len(mesh),bounds_mm=bounds,
            reference='Moller-Trumbore intersection on original installed STL triangles',records=records),indent=2),encoding='utf-8')
    asyncio.run(execute('adaptation_cad_'+name.replace('.','_'),work))
