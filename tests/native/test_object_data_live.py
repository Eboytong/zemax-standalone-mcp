"""Prepared NS-04 native facets and bounded detector region checks."""
import asyncio
import pytest
from tests.support.native import execute
from tests.support.nsc import setup,update,trace

@pytest.mark.zemax
def test_native_object_facet_pages_local_global():
    async def work(e):
        await setup(e,3)
        await update(e,[dict(object=1,object_type='RectangularVolume',x=3,z=5,material='N-BK7',data=dict(X1HalfWidth=1,Y1HalfWidth=2,X2HalfWidth=1,Y2HalfWidth=2,ZLength=2)),dict(object=2,object_type='DetectorRectangle',z=12,material='ABSORB',data=dict(NumberXPixels=7,NumberYPixels=5,XHalfWidth=2,YHalfWidth=3)),dict(object=3,object_type='DetectorVolume',z=12,material='ABSORB',data=dict(NumberXPixels=7,NumberYPixels=5,NumberZPixels=3,XHalfWidth=2,YHalfWidth=3,ZHalfWidth=2))])
        await update(e,[dict(object=1,type_settings=dict(ObjectIsADetector=True))])
        baseline=await e.call('get_nsc_objects',dict(request={}))
        for frame,x_offset,z_offset in [('local',0,0),('global',3,5)]:
            start=0;faces=[]
            while True:
                page=await e.call('get_nsc_object_geometry',dict(request=dict(object=1,start=start,count=2,frame=frame)))
                assert page['cursor_restored'];faces+=page['rows']
                if page['next_start']is None:break
                start=page['next_start']
            points=[p for f in faces for p in f['vertices']];assert points
            for axis,minimum,maximum in [(0,x_offset-1,x_offset+1),(1,-2,2),(2,z_offset,z_offset+2)]:
                e.check('object facet minimum',min(p[axis]for p in points),minimum,atol=1e-8,rtol=1e-7)
                e.check('object facet maximum',max(p[axis]for p in points),maximum,atol=1e-8,rtol=1e-7)
        assert (await e.call('get_nsc_objects',dict(request={})))==baseline
    asyncio.run(execute('object_data029_geometry',work))

@pytest.mark.zemax
@pytest.mark.parametrize('volume',[False,True])
def test_native_detector_region_matches_full(volume):
    async def work(e):
        await setup(e,4)
        data=dict(NumberXPixels=7,NumberYPixels=5,XHalfWidth=2,YHalfWidth=3)
        if volume:data.update(NumberZPixels=3,ZHalfWidth=2)
        await update(e,[dict(object=1,object_type='SourceRay',x=.5,data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),dict(object=3 if volume else 2,object_type='DetectorVolume'if volume else'DetectorRectangle',z=22,data=data,type_settings={}if volume else dict(UsePixelInterpolation=False))])
        saved=str(e.folder/'region.zos');await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        baseline=await e.call('get_nsc_objects',dict(request={}))
        await trace(e,'region_reference')
        full=await e.call('get_detector_data',dict(request=dict(detector=3 if volume else 2,width=7,height=5,depth=3 if volume else 1)))
        region=await e.call('get_detector_data',dict(request=dict(detector=3 if volume else 2,read_mode='region',x_start=1,y_start=1,z_start=1 if volume else 0,width=4,height=3,depth=2 if volume else 1)))
        expected=[[r[1:5]for r in p[1:4]]for p in full['values'][1:3]]if volume else[r[1:5]for r in full['values'][1:4]]
        assert region['values']==expected and region['total_flux']is None
        assert region['scope']=='requested region only' and len(region['x_axis']['centers'])==4
        e.check('independent point-ray cell W',region['values'][0][1][3]if volume else region['values'][1][3],1)
        for kind in (['absorbed_flux','absorbed_density']if volume else ['irradiance','intensity']):
            full=await e.call('get_detector_data',dict(request=dict(detector=3 if volume else 2,kind=kind,width=7,height=5,depth=3 if volume else 1)))
            region=await e.call('get_detector_data',dict(request=dict(detector=3 if volume else 2,kind=kind,read_mode='region',x_start=1,y_start=1,z_start=1 if volume else 0,width=4,height=3,depth=2 if volume else 1)))
            expected=[[r[1:5]for r in p[1:4]]for p in full['values'][1:3]]if volume else[r[1:5]for r in full['values'][1:4]]
            assert region['values']==expected,kind
        assert await e.call('get_nsc_objects',dict(request={}))==baseline
    asyncio.run(execute('object_data029_regions',work))

@pytest.mark.zemax
def test_large_native_detector_region_without_full_read():
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=2,object_type='DetectorVolume',data=dict(NumberXPixels=128,NumberYPixels=128,NumberZPixels=128,XHalfWidth=2,YHalfWidth=3,ZHalfWidth=4))])
        region=await e.call('get_detector_data',dict(request=dict(detector=2,read_mode='region',x_start=127,y_start=127,z_start=127,width=1,height=1,depth=1)))
        assert region['values']==[[[0.]]] and region['nx']*region['ny']*region['nz']>1000000
    asyncio.run(execute('object_data029_large',work))

@pytest.mark.zemax
def test_native_facet_radiometry_absorbing_box():
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=1,object_type='SourceRay',x=.2,y=.3,z=-1,data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),
                        dict(object=2,object_type='RectangularVolume',material='ABSORB',data=dict(X1HalfWidth=1,Y1HalfWidth=2,X2HalfWidth=1,Y2HalfWidth=2,ZLength=2),type_settings=dict(ObjectIsADetector=True))])
        await trace(e,'box')
        result=await e.call('get_nsc_object_geometry',dict(request=dict(object=2,count=100,include_radiometry=True)))
        e.check('faceted absorbing box incident W',sum(r['radiometry']['Flux']for r in result['rows']),1)
        e.check('faceted absorbing box absorbed W',sum(r['radiometry']['AbsorbedFlux']for r in result['rows']),1)
        assert result['cursor_restored']
    asyncio.run(execute('facets065_radiometry',work))
