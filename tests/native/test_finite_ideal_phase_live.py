"""Ideal, coordinate-break, binary phase and hologram reciprocity references."""
import asyncio
import json
import math
import pytest
from tests.support.native import execute
from tests.support.finite_reference import unit


@pytest.mark.zemax
@pytest.mark.parametrize('kind',['Paraxial','ParaxialXY','CoordinateBreak'])
def test_finite_ideal_surface_native(kind):
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2))
        parameters={'Paraxial':{1:100,2:1},'ParaxialXY':{1:.01,2:.02},'CoordinateBreak':{1:.2,2:-.3,4:5}}[kind]
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=1,semi_diameter=5,replace_solves=True),
            dict(surface=2,surface_type=kind,parameters=parameters,semi_diameter=5,replace_solves=True)]))
        path=e.folder/'model.zos';await e.call('save_lens_as',dict(path=str(path)));records=[]
        for reload in (False,True):
            if reload:await e.call('open_lens',dict(path=str(path)))
            points=[(0,0),(1,0),(-1,0),(0,1),(.5,-.75)]
            rays=[dict(x=x,y=y,z=0,l=0,m=0,n=1)for x,y in points]
            data=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(input_mode='Direct',start_surface=1,target_surface=2,rays=rays))))
            for (x,y),row in zip(points,data['rows'],strict=True):
                assert row['error_code']==row['vignette_code']==0,row
                position=(x,y,0);direction=unit((-x*.01,-y*(.02 if kind=='ParaxialXY'else .01),1))
                if kind=='CoordinateBreak':
                    a=math.radians(5);position=((x-.2)/math.cos(a),y+.3,0)
                    direction=(-math.sin(a),0,math.cos(a))
                for i in range(3):
                    e.check('ideal surface position mm',row['position'][i],position[i])
                    e.check('ideal surface signed direction',row['direction'][i],direction[i])
                records.append(dict(reloaded=reload,actual=row,position=position,direction=direction))
        (e.folder/'ideal-reference.json').write_text(json.dumps(dict(kind=kind,parameters=parameters,rows=records),indent=2),encoding='utf-8')
    asyncio.run(execute('finite_ideal_'+kind,work))


@pytest.mark.zemax
@pytest.mark.parametrize('kind',['Binary2','Binary3','DiffractionGrating','Hologram2'])
def test_finite_phase_surface_native(kind):
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=1,semi_diameter=5,replace_solves=True),
            dict(surface=2,surface_type=kind,semi_diameter=5,replace_solves=True)]))
        parameters={
            'Binary2':{**{i:0 for i in range(1,9)},13:2,14:5,15:.2,16:.1},
            'Binary3':{1:0,2:0,3:1,4:3,5:1,6:1,8:0,13:1,14:0,15:.2,16:0,17:.3},
            'DiffractionGrating':{1:.1,2:1},
            'Hologram2':{1:0,2:0,3:-100,4:0,5:0,6:-200,7:.55,8:1,13:0},
        }[kind]
        if kind in ('Binary2','Binary3'):
            await e.call('update_surfaces',dict(changes=[dict(surface=2,parameters={13:parameters[13]},replace_solves=True)]))
        await e.call('update_surfaces',dict(changes=[dict(surface=2,radius='Infinity',parameters=parameters,
            material='MIRROR'if kind=='Hologram2'else'',thickness=-100 if kind=='Hologram2'else 10,replace_solves=True)]))
        path=e.folder/'model.zos';await e.call('save_lens_as',dict(path=str(path)));records=[]
        points=[(.25,0),(-.25,0),(0,.5),(2,0),(0,-2)]
        for reload in (False,True):
            if reload:await e.call('open_lens',dict(path=str(path)))
            rays=[];expected=[]
            for x,y in points:
                if kind=='Hologram2':
                    d=unit((x,y,100));rays.append(dict(x=x-d[0]/d[2],y=y-d[1]/d[2],z=0,l=d[0],m=d[1],n=d[2]))
                    # Negative-index sequential reflection: API direction is
                    # opposite the physical outgoing ray, as separately documented.
                    direction=unit((x,y,200))
                else:
                    rays.append(dict(x=x,y=y,z=0,l=0,m=0,n=1))
                    if kind=='DiffractionGrating':dx,dy=0,.55*.1
                    else:
                        r2=x*x+y*y
                        if kind=='Binary2':gradient=.4/25+.4*r2/625
                        else:gradient=.4 if r2<=1 else .6/9
                        # Manual Binary1 sign convention: focusing power has
                        # a negative quadratic coefficient (unlike GridPhase).
                        dx=.00055/(2*math.pi)*gradient*x;dy=.00055/(2*math.pi)*gradient*y
                    direction=(dx,dy,math.sqrt(1-dx*dx-dy*dy))
                expected.append(direction)
            result=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(input_mode='Direct',start_surface=1,target_surface=2,rays=rays))))
            for point,reference,row in zip(points,expected,result['rows'],strict=True):
                assert row['error_code']==row['vignette_code']==0,row
                values=[]
                for i in range(3):values.append(abs(row['direction'][i]-reference[i])<=1e-8+1e-7*abs(reference[i]))
                records.append(dict(point_mm=point,reloaded=reload,expected_direction=reference,actual=row,passed=all(values)))
        (e.folder/'phase-reference.json').write_text(json.dumps(dict(kind=kind,parameters=parameters,
            reference='Binary1 optical-path sign at manual L5923; grating2.3.1.2.21; hologram construction-beam reciprocity',
            hologram_direction_scope='negative-index API cosine opposite physical outgoing vector',rows=records),indent=2),encoding='utf-8')
        assert all(r['passed']for r in records),records
    asyncio.run(execute('finite_phase_'+kind,work))
