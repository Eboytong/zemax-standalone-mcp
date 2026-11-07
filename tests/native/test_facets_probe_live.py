"""Discover runtime faceted geometry on a controlled local STL resource."""
import asyncio,json,math
from pathlib import Path
from uuid import uuid4
import pytest
from tests.support.native import execute
from tests.support.nsc import setup,update

def tetrahedron():
    points=[(0,0,0),(2,0,0),(0,3,0),(0,0,4)]
    lines=['solid tetra']
    for indices in [(0,2,1),(0,1,3),(0,3,2),(1,2,3)]:
        a,b,c=[points[i]for i in indices]
        u=[b[i]-a[i]for i in range(3)];v=[c[i]-a[i]for i in range(3)]
        n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];length=math.hypot(*n)
        lines+=['facet normal '+' '.join(str(x/length)for x in n),'outer loop']
        lines+=['vertex '+' '.join(map(str,p))for p in [a,b,c]]
        lines+=['endloop','endfacet']
    return '\n'.join(lines+['endsolid tetra'])+'\n'

@pytest.mark.zemax
def test_controlled_stl_facet_probe():
    resource=Path.home()/'Documents/Zemax/Objects/CAD Files'/('MCP065_'+uuid4().hex+'.STL')
    resource.write_text(tetrahedron(),encoding='ascii')
    async def work(e):
        (e.folder/'tetra.STL').write_text(tetrahedron(),encoding='ascii')
        await setup(e,1)
        await update(e,[dict(object=1,object_type='CADPartSTL',file1=resource.name,x=3,z=5,tilt_y=30,type_settings=dict(ObjectIsADetector=True))])
        saved=str(e.folder/'facets-baseline.zos');await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        baseline=await e.call('get_nsc_objects',dict(request={}))
        records=[]
        for frame in ['local','global']:
            response=await e.call('get_nsc_object_geometry',dict(request=dict(object=1,count=10,frame=frame)),okay=False)
            records.append(dict(frame=frame,result=response))
            assert response.get('ok')is not False,response
            assert response['total']==4 and len(response['rows'])==4
            expected_vertices=[(0,0,0),(2,0,0),(0,3,0),(0,0,4)]
            if frame=='global':expected_vertices=[(math.cos(math.pi/6)*x+math.sin(math.pi/6)*z+3,y,-math.sin(math.pi/6)*x+math.cos(math.pi/6)*z+5)for x,y,z in expected_vertices]
            for row in response['rows']:
                assert row['vertex_count']==3
                for p in row['vertices']:
                    assert any(all(abs(a-b)<=1e-8+1e-7*abs(b)for a,b in zip(p,v))for v in expected_vertices),p
                a,b,c=row['vertices'];u=[b[i]-a[i]for i in range(3)];v=[c[i]-a[i]for i in range(3)]
                normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];length=math.hypot(*normal)
                e.check('STL triangle area',row['triangle_area'],length/2)
                for n in row['vertex_normals']:
                    for actual,reference in zip(n,normal):e.check('STL normal',actual,reference/length)
        saved=str(e.folder/'facets.zos');await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        reloaded=await e.call('get_nsc_object_geometry',dict(request=dict(object=1,count=10,frame='local')))
        assert reloaded['rows']==records[0]['result']['rows']
        assert await e.call('get_nsc_objects',dict(request={}))==baseline
        (e.folder/'facet-probe.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    try:asyncio.run(execute('facets065_stl',work))
    finally:resource.unlink(missing_ok=True)
