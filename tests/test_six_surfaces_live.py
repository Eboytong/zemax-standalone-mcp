from zemax_mcp.models import COMMAND_MODELS
"""Finite six-surface stdio validation, independently reproducible per condition."""
import asyncio
import cmath
import json
import math
import pytest
from support.native import execute
from support.finite_reference import glass_coefficients,sellmeier,snell,unit
from support.six_surface_reference import sag,normal,conjugate_value,reflected,extended_sag

POINTS=[(0,0),(.6,0),(-.6,0),(0,.6),(0,-.6),(.7,.4),(-.7,.4),(.7,-.4),(-.7,-.4)]
GEOMETRY=[
    ('OddAsphere','smooth',50,-.3,{1:0,2:.001,3:-.0002,8:.00001}),
    ('OddAsphere','cusp',50,-.3,{1:.001,2:-.0005,3:.0002}),
    ('Biconic','xy',50,-.3,{1:30,2:-.7}),
    ('Biconic','yx',30,-.7,{1:50,2:-.3}),
    ('Biconic','infinite_x',50,-.3,{1:0,2:-.7}),
    ('Conjugate','real',0,0,{1:0,2:0,3:-30,4:0,5:0,6:-50}),
    ('Conjugate','virtual',0,0,{1:0,2:0,3:-30,4:0,5:0,6:50}),
    ('Conjugate','off_axis',0,0,{1:1,2:-2,3:-30,4:-2,5:1,6:-50}),
]


@pytest.mark.zemax
def test_six_capabilities_native():
    async def work(e):
        caps=await e.call('get_capabilities')
        assert len(caps['implemented_tools'])==len(COMMAND_MODELS)
        assert {'Conjugate','ABCD','RetroReflect','JonesMatrix'}<=set(caps['validated_surface_model_scope'])
        assert 'l/n' in caps['surface_numeric_reference_scopes']['ABCD']
        (e.folder/'capabilities.json').write_text(json.dumps(caps,ensure_ascii=False,indent=2),encoding='utf-8')
        await e.model()
        resources=await e.call('get_system_resources',dict(request=dict(kind='surface_types',count=1000)))
        (e.folder/'surface-identifiers.json').write_text(json.dumps(resources,ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('six_capabilities',work))


async def setup(e,kind,p,material='',radius=0,conic=0):
    await e.model();await e.call('insert_surfaces',dict(at=2))
    await e.call('update_system_settings',dict(settings=dict(lens_units='Millimeters',material_catalogs=['SCHOTT'],temperature_c=20,adjust_index_to_environment=True)))
    await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=1,semi_diameter=5,replace_solves=True),
        dict(surface=2,surface_type=kind,parameters=p,material=material,thickness=-5 if material=='MIRROR' else 5,semi_diameter=4,replace_solves=True)]))
    # Some ideal surfaces intentionally do not expose radius/conic columns.
    if kind in ('OddAsphere','Biconic'):
        await e.call('update_surfaces',dict(changes=[dict(surface=2,radius=radius,conic=conic,replace_solves=True)]))


async def row(e,surface=2):
    return (await e.call('get_surfaces',dict(start=surface,count=1,parameter_count=254)))['surfaces'][0]


async def trace(e,rays,polarization=None,target=2):
    q=dict(input_mode='Direct',start_surface=1,target_surface=target,rays=rays)
    if polarization is not None:q['polarization']=polarization
    result=await e.finish(await e.call('run_batch_ray_trace',dict(request=q)))
    assert len(result['rows'])==len(rays)
    assert all(r['error_code']==0 and not r['vignette_code'] for r in result['rows']),result
    return result['rows']


async def reload_states(e,validate):
    await validate('memory')
    e.surface_save_sequence=getattr(e,'surface_save_sequence',0)+1
    for ext in ('zos','zmx'):
        path=e.folder/(f'model_{e.surface_save_sequence}.'+ext)
        await e.call('save_lens_as',dict(path=str(path)))
        await e.call('open_lens',dict(path=str(path)))
        await validate(ext)


def vector_check(e,label,actual,expected):
    for a,b in zip(actual,expected,strict=True):e.check(label,a,b)


@pytest.mark.zemax
@pytest.mark.parametrize('kind,case,radius,conic,p',GEOMETRY,ids=[k+'_'+c for k,c,*_ in GEOMETRY])
def test_six_geometric_native(kind,case,radius,conic,p):
    async def work(e):
        mirror=kind=='Conjugate'
        await setup(e,kind,p,'MIRROR' if mirror else 'N-BK7',radius,conic)
        n=sellmeier(.55,glass_coefficients())
        async def validate(state):
            actual=await row(e);assert actual['surface_type']==kind
            for i,v in p.items():e.check('parameter readback',actual['cells'][f'parameter_{i}']['value'],v)
            if kind in ('OddAsphere','Biconic'):
                e.check('base radius mm',actual['cells']['radius']['value'],radius)
                e.check('base conic',actual['cells']['conic']['value'],conic)
            points=[q for q in POINTS if not(case=='cusp' and q==(0,0))]
            geometry=(await e.call('get_surface_geometry',dict(request=dict(surface=2,points=[dict(x=x,y=y)for x,y in POINTS]))))['rows']
            for (x,y),g in zip(POINTS,geometry,strict=True):
                z=sag(kind,x,y,radius,conic,p);e.check('independent sag mm',g['sag'],z)
                if mirror:e.check('conjugate distance residual mm',conjugate_value(x,y,z,p)[0],0)
            rays=await trace(e,[dict(x=x,y=y,z=0,l=0,m=0,n=1) for x,y in points])
            for (x,y),r in zip(points,rays,strict=True):
                z=sag(kind,x,y,radius,conic,p);nr=normal(kind,x,y,radius,conic,p)
                vector_check(e,'independent intersection mm',r['position'],(x,y,z))
                vector_check(e,'reference normal step convergence',nr,normal(kind,x,y,radius,conic,p,step=5e-6))
                e.check('native normal parallel',abs(sum(a*b for a,b in zip(unit(r['surface_normal']),nr))),1)
                expected=tuple(-v for v in reflected((0,0,1),nr)) if mirror else snell((0,0,1),nr,1,n)
                vector_check(e,'signed native direction',r['direction'],expected)
        await reload_states(e,validate)
    asyncio.run(execute('six_'+kind+'_'+case,work))


ABCD=[('identity',[1,0,0,1,1,0,0,1]),('lens',[1,0,-.01,1,1,0,-.02,1]),('separate',[1.2,2,-.01,.8166666666666667,.9,-1,.02,1.088888888888889])]


@pytest.mark.zemax
@pytest.mark.parametrize('case,coefficients',ABCD)
def test_six_abcd_native(case,coefficients):
    async def work(e):
        p=dict(enumerate(coefficients,1));await setup(e,'ABCD',p)
        async def validate(state):
            actual=await row(e)
            for i,v in p.items():e.check('ABCD adopted coefficient',actual['cells'][f'parameter_{i}']['value'],v)
            seeds=[(.3,-.2,.01,-.02),(-.4,.5,-.015,.012),(0,0,0,0)]
            inputs=[];expected=[]
            for x,y,ax,ay in seeds:
                d=unit((math.tan(ax),math.tan(ay),1))
                inputs.append(dict(x=x-d[0]/d[2],y=y-d[1]/d[2],z=0,l=d[0],m=d[1],n=d[2]))
                # ABCD first-order ray variables are geometric slopes l/n,m/n,
                # not the finite arctangent angles used to construct the input.
                sx,sy=math.tan(ax),math.tan(ay)
                xx=p[1]*x+p[2]*sx;yy=p[5]*y+p[6]*sy
                aa=p[3]*x+p[4]*sx;bb=p[7]*y+p[8]*sy
                expected.append(((xx,yy,0),unit((aa,bb,1))))
            for r,(position,direction) in zip(await trace(e,inputs),expected,strict=True):
                vector_check(e,'ABCD height mm',r['position'],position)
                vector_check(e,'ABCD angular matrix direction',r['direction'],direction)
        await reload_states(e,validate)
    asyncio.run(execute('six_ABCD_'+case,work))


@pytest.mark.zemax
@pytest.mark.parametrize('material',['','N-BK7','MIRROR'])
def test_six_retro_native(material):
    async def work(e):
        await setup(e,'RetroReflect',{},material)
        async def validate(state):
            rays=[];directions=[];positions=[]
            for x,y,sx,sy in [(0,0,0,0),(.3,-.2,.03,-.02),(-.4,.5,-.01,.02)]:
                d=unit((sx,sy,1));directions.append(d);positions.append((x,y,0))
                rays.append(dict(x=x-d[0]/d[2],y=y-d[1]/d[2],z=0,l=d[0],m=d[1],n=d[2]))
            for r,d,pos in zip(await trace(e,rays),directions,positions,strict=True):
                vector_check(e,'Retro plane intercept mm',r['position'],pos)
                expected=snell(d,(0,0,1),1,sellmeier(.55,glass_coefficients())) if material=='N-BK7' else d
                vector_check(e,'Retro native cosines',r['direction'],expected)
            if material=='MIRROR':
                # Subsequent negative-thickness propagation must retrace the path.
                after=await trace(e,rays,target=3)
                for r,d,pos in zip(after,directions,positions,strict=True):
                    vector_check(e,'Retro returned intersection mm',r['position'],(pos[0]-5*d[0]/d[2],pos[1]-5*d[1]/d[2],0))
        await reload_states(e,validate)
    asyncio.run(execute('six_Retro_'+(material or 'AIR'),work))


JONES=[('identity',(1,0,0,1)),('linear',(1,0,0,0)),('quarter',(1,0,0,1j)),('rotation',(math.sqrt(.5),-math.sqrt(.5),math.sqrt(.5),math.sqrt(.5)))]


@pytest.mark.zemax
@pytest.mark.parametrize('case,matrix',JONES)
def test_six_jones_native(case,matrix):
    async def work(e):
        p={2*i+1:v.real for i,v in enumerate(map(complex,matrix))}
        p.update({2*i+2:v.imag for i,v in enumerate(map(complex,matrix))})
        await setup(e,'JonesMatrix',p)
        inputs=[dict(jx=1,jy=0),dict(jx=0,jy=1),dict(jx=1,jy=1),dict(jx=1,jy=1,y_phase=90)]
        await e.call('update_surfaces',dict(changes=[dict(surface=2,parameters={1:1,2:0,3:0,4:0,5:0,6:0,7:1,8:0},replace_solves=True)]))
        phases=[]
        for pol in inputs:
            baseline=(await trace(e,[dict(x=.2,y=-.3,z=0,l=0,m=0,n=1)],pol))[0]
            f=baseline['electric_field'];component='x' if pol['jx'] else 'y'
            input_value=(pol['jx'] if component=='x' else pol['jy']*cmath.exp(1j*math.radians(pol.get('y_phase',0))))/math.sqrt(pol['jx']**2+pol['jy']**2)
            phase=complex(f[f'e{component}_real'],f[f'e{component}_imag'])/input_value
            e.check('identity common propagation factor magnitude',abs(phase),1)
            e.check('identity input power',baseline['intensity'],1)
            phases.append(cmath.exp(1j*cmath.phase(phase)))
        await e.call('update_surfaces',dict(changes=[dict(surface=2,parameters=p,replace_solves=True)]))
        (e.folder/'jones-reference.json').write_text(json.dumps(dict(matrix=[str(v)for v in matrix],inputs=inputs,common_propagation_phase=[str(v)for v in phases],reference='complex Jones multiplication; phase from same-geometry identity, magnitude independently required unity'),indent=2),encoding='utf-8')
        async def validate(state):
            actual=await row(e)
            for i,v in p.items():e.check('Jones matrix adopted coefficient',actual['cells'][f'parameter_{i}']['value'],v)
            for pol,phase in zip(inputs,phases):
                r=(await trace(e,[dict(x=.2,y=-.3,z=0,l=0,m=0,n=1)],pol))[0]
                power=pol['jx']**2+pol['jy']**2
                ex=pol['jx']/math.sqrt(power);ey=pol['jy']/math.sqrt(power)*cmath.exp(1j*math.radians(pol.get('y_phase',0)))
                a,b,c,d=matrix;reference=((a*ex+b*ey)*phase,(c*ex+d*ey)*phase,0j)
                field=r['electric_field']
                actual_field=[complex(field[f'e{k}_real'],field[f'e{k}_imag'])for k in 'xyz']
                for z,v in zip(actual_field,reference):e.check('Jones field real',z.real,v.real);e.check('Jones field imag',z.imag,v.imag)
                e.check('Jones transmitted power',r['intensity'],sum(abs(v)**2 for v in reference))
        await reload_states(e,validate)
    asyncio.run(execute('six_Jones_'+case,work))


@pytest.mark.zemax
@pytest.mark.parametrize('kind',['ExtendedAsphere','ExtendedOddAsphere','ExtendedPolynomial'])
def test_six_extended_controls_native(kind):
    async def work(e):
        await setup(e,kind,{13:30,14:1.2,15:.001,21:-.002})
        await e.call('update_surfaces',dict(changes=[dict(surface=2,radius=50,conic=-.2,replace_solves=True)]))
        maximum=230 if kind=='ExtendedPolynomial' else 240
        last=14+maximum
        for norm in (1.2,2.):
            for count in (3,30,maximum):
                p={13:count,14:norm,15:.001,21:-.002,last:.0001}
                await e.call('update_surfaces',dict(changes=[dict(surface=2,parameters={13:maximum},replace_solves=True)]))
                await e.call('update_surfaces',dict(changes=[dict(surface=2,parameters={14:norm,15:.001,21:-.002,last:.0001},replace_solves=True)]))
                await e.call('update_surfaces',dict(changes=[dict(surface=2,parameters={13:count},replace_solves=True)]))
                points=[(norm,0),(-norm,0),(0,norm),(0,-norm),(norm*.8,norm*.6),(-norm*.8,norm*.6)]
                async def validate(state):
                    r=await row(e)
                    for i,v in p.items():
                        if i<15 or i<=14+count:e.check('extended coefficient/control readback',r['cells'][f'parameter_{i}']['value'],v)
                    if count==3:assert 'parameter_21' not in r['cells']
                    g=(await e.call('get_surface_geometry',dict(request=dict(surface=2,points=[dict(x=x,y=y) for x,y in points]))))['rows']
                    for (x,y),value in zip(points,g):e.check('extended term participation sag mm',value['sag'],extended_sag(kind,x,y,p))
                await reload_states(e,validate)
        # Use an earlier compatible surface, independently of forward-reference
        # restrictions of native parameter pickups.
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type=kind,parameters={13:30,14:2,21:.003},semi_diameter=4,replace_solves=True)]))
        await e.call('set_variables',dict(variables=[dict(surface=2,cell='parameter_21',variable=True)]))
        async def variable(state):
            cell=(await row(e))['cells']['parameter_21']
            assert cell['solve']['type']=='Variable'
            e.check('variable coefficient',cell['value'],-.002)
        await reload_states(e,variable)
        await e.call('set_variables',dict(variables=[dict(surface=2,cell='parameter_21',variable=False)]))
        async def fixed(state):assert (await row(e))['cells']['parameter_21']['solve']['type']=='Fixed'
        await reload_states(e,fixed)
        await e.call('update_surfaces',dict(changes=[dict(surface=2,solves={'parameter_21':dict(mode='surface_pickup',source_surface=1,scale=1,offset=0)})]))
        async def picked(state):
            cell=(await row(e))['cells']['parameter_21']
            assert cell['solve']['type']=='SurfacePickup'
            e.check('same-column pickup coefficient',cell['value'],.003)
        await reload_states(e,picked)
        bad=await e.call('update_surfaces',dict(changes=[dict(surface=2,parameters={21:.004})]),okay=False)
        assert not bad['ok'];await picked('protected')
        await e.call('get_system_summary')
        revision=e.calls[-1]['response']['context']['model_revision']
        bad=await e.call('update_surfaces',dict(changes=[dict(surface=2,parameters={13:3,21:.004},replace_solves=True)]),okay=False)
        assert not bad['ok'] and bad['error']['code']=='CELL_NOT_WRITABLE'
        assert bad['context']['model_revision']==revision
        await e.call('update_surfaces',dict(changes=[dict(surface=2,parameters={21:.004},replace_solves=True)]))
        e.check('explicit pickup replacement',(await row(e))['cells']['parameter_21']['value'],.004)
        bad=await e.call('update_surfaces',dict(changes=[dict(surface=2,surface_type='Standard')]),okay=False)
        assert not bad['ok'] and bad['error']['code']=='SOLVE_PROTECTED'
        await e.call('update_surfaces',dict(changes=[dict(surface=2,surface_type='Standard',replace_solves=True)]))
        bad=await e.call('update_surfaces',dict(changes=[dict(surface=2,parameters={254:.1})]),okay=False)
        assert not bad['ok']
    asyncio.run(execute('six_Extended_'+kind,work))
