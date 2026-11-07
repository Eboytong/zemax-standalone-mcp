"""Native CAD NSC settings with independent transformed box geometry."""
import asyncio,itertools,math,json
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.nsc import setup,update,trace
from tests.support.mesh_reference import triangles,cross,dot


def geometry(path):
    if path.suffix.lower()=='.stl':
        mesh=triangles(path);points=[p for t in mesh for p in t]
        volume=abs(sum(dot(a,cross(b,c))/6 for a,b,c in mesh))
    else:
        from OCP.STEPControl import STEPControl_Reader
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopAbs import TopAbs_VERTEX,TopAbs_SOLID
        from OCP.TopoDS import TopoDS
        from OCP.BRep import BRep_Tool
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        r=STEPControl_Reader();assert r.ReadFile(str(path));assert r.TransferRoots()>0;shape=r.OneShape()
        g=GProp_GProps();BRepGProp.VolumeProperties_s(shape,g,1e-10);volume=g.Mass();points=[];solids=TopExp_Explorer(shape,TopAbs_SOLID)
        while solids.More():
            it=TopExp_Explorer(solids.Current(),TopAbs_VERTEX)
            while it.More():points.append(list(BRep_Tool.Pnt_s(TopoDS.Vertex(it.Current())).Coord()));it.Next()
            solids.Next()
        assert points,'expected an exported solid'
    return dict(volume=volume,bounds=[[min(p[k]for p in points),max(p[k]for p in points)]for k in range(3)])


@pytest.mark.zemax
def test_native_cad_nsc_options_and_geometry():
    async def work(e):
        await setup(e,3)
        await update(e,[dict(object=1,object_type='SourceRay',x=5,y=-2,z=5,data=dict(NumberOfAnalysisRays=1,NumberOfLayoutRays=8,Power=1,ZCosine=1)),dict(object=2,object_type='RectangularVolume',x=5,y=-2,z=10,tilt_z=30,material='N-BK7',data=dict(X1HalfWidth=2,Y1HalfWidth=3,X2HalfWidth=2,Y2HalfWidth=3,ZLength=4),faces=[dict(face=1,coating='SPLIT',scatter_model='Lambertian',number_of_rays=1,settings=dict(ScatterFraction=.5))]),dict(object=3,object_type='DetectorRectangle',x=5,y=-2,z=20,material='ABSORB',data=dict(XHalfWidth=20,YHalfWidth=20,NumberXPixels=8,NumberYPixels=8))])
        saved=str(e.folder/'cad_nsc.zos');await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        baseline=await e.call('get_nsc_objects',dict(request={}));settings=await e.call('get_system_settings')
        c=math.cos(math.pi/6);s=math.sin(math.pi/6);points=[[5+c*x-s*y,-2+s*x+c*y,10+z]for x,y,z in itertools.product([-2,2],[-3,3],[0,4])]
        bounds=[[min(p[k]for p in points),max(p[k]for p in points)]for k in range(3)];records=[]
        for scatter,split,polarization in itertools.product([False,True],repeat=3):
            q=dict(path=str(e.folder/f'box-{scatter}-{split}-{polarization}.step'),format='STEP',start=2,end=2,number_of_rays=0,scatter_nsc_rays=scatter,split_nsc_rays=split,use_polarization=polarization)
            result=await e.finish(await e.call('run_cad_export',dict(request=q)))
            actual=geometry(Path(result['path']));records.append(dict(request=q,geometry=actual));(e.folder/'geometry.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
            e.check('NSC STEP box volume',actual['volume'],96,atol=1e-5,rtol=1e-6)
            for axis in range(3):
                for side in range(2):e.check('NSC STEP transformed bounds',actual['bounds'][axis][side],bounds[axis][side],atol=1e-5,rtol=1e-6)
            task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert task['close_attempted']and not task.get('cleanup_warnings')
            assert await e.call('get_nsc_objects',dict(request={}))==baseline and await e.call('get_system_settings')==settings
        result=await e.finish(await e.call('run_cad_export',dict(request=dict(path=str(e.folder/'box.stl'),format='STL',start=2,end=2,angular_tolerance='High'))))
        actual=geometry(Path(result['path']));e.check('NSC STL box volume',actual['volume'],96,atol=1e-5,rtol=1e-6)
        for axis in range(3):
            for side in range(2):e.check('NSC STL bounds',actual['bounds'][axis][side],bounds[axis][side],atol=1e-5,rtol=1e-6)
        _,segments=await trace(e,'after_cad',scatter_rays=True,split_rays=True,use_polarization=True,max_segments=1000)
        first=next(r for r in segments if r['HitObject']==2)
        for name,value in [('X',5),('Y',-2),('Z',10)]:e.check('NSC trace hit after CAD',first[name],value)
        assert await e.call('get_nsc_objects',dict(request={}))==baseline and await e.call('get_system_settings')==settings
    asyncio.run(execute('cad180_nsc_reference',work))
