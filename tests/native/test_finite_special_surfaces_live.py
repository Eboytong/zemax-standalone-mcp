"""Installed uniaxial, MEMS, grid-GRIN and mixed-mode fixture boundaries."""
import asyncio
import json
import math
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.finite_reference import snell,sellmeier,glass_coefficients,unit


def crystal_indices(wavelength):
    path=Path.home()/'Documents/Zemax/Glasscat/BIREFRINGENT.AGF';data={};name=None
    for line in path.read_text(encoding='utf-8-sig',errors='replace').splitlines():
        if line.startswith('NM '):name=line.split()[1]
        if name in ('CALCITE','CALCITE-E')and line.startswith('CD '):
            c=list(map(float,line.split()[1:]));w2=wavelength*wavelength
            data[name]=math.sqrt(1+sum(c[i]*w2/(w2-c[i+1])for i in range(0,len(c),2)))
    return data['CALCITE'],data['CALCITE-E']


@pytest.mark.zemax
@pytest.mark.parametrize('mode',[0,1])
def test_finite_birefringent_in_out_native(mode):
    async def work(e):
        import numpy as np
        await e.model();await e.call('insert_surfaces',dict(at=2,count=2))
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['BIREFRINGENT'],temperature_c=20,adjust_index_to_environment=True)))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=1,semi_diameter=2,replace_solves=True),
            dict(surface=2,surface_type='BirefringentIn',surface_file='ub_mode6.dll',radius='Infinity',material='CALCITE',thickness=5,
                parameters={1:mode,2:0,3:math.sqrt(.5),4:math.sqrt(.5),5:0,6:0,13:0},semi_diameter=2,replace_solves=True),
            dict(surface=3,surface_type='BirefringentOut',radius='Infinity',material='',thickness=5,semi_diameter=2,replace_solves=True)]))
        no,ne=crystal_indices(.55);a=np.array([0,math.sqrt(.5),math.sqrt(.5)])
        Q=np.eye(3)/ne**2+np.outer(a,a)*(1/no**2-1/ne**2)
        direction=np.array([0,0,1])if mode==0 else np.asarray(unit(Q@np.array([0,0,1])))
        path=e.folder/'model.zos';await e.call('save_lens_as',dict(path=str(path)));records=[]
        for reload in (False,True):
            if reload:await e.call('open_lens',dict(path=str(path)))
            for target in (2,3):
                result=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(input_mode='Direct',start_surface=1,target_surface=target,
                    rays=[dict(x=x,y=y,z=0,l=0,m=0,n=1)for x,y in ((0,0),(.1,.1),(-.1,.05))]))))
                for (x,y),row in zip(((0,0),(.1,.1),(-.1,.05)),result['rows'],strict=True):
                    expected_position=[x,y,0]if target==2 else[x+5*direction[0]/direction[2],y+5*direction[1]/direction[2],0]
                    expected_direction=direction if target==2 else[0,0,1]
                    passed=row['error_code']==row['vignette_code']==0
                    passed=passed and all(abs(v-w)<=1e-8+1e-7*abs(w)for v,w in zip(row['position'],expected_position))
                    passed=passed and all(abs(v-w)<=1e-8+1e-7*abs(w)for v,w in zip(row['direction'],expected_direction))
                    records.append(dict(reloaded=reload,target=target,expected_position_mm=expected_position,
                        expected_direction=[float(v)for v in expected_direction],actual=row,passed=passed))
        (e.folder/'crystal-reference.json').write_text(json.dumps(dict(mode=mode,ordinary_index=no,extraordinary_index=ne,
            formula='uniaxial dispersion tensor Q=I/ne^2+aaT*(1/no^2-1/ne^2); Poynting along Qk; plane exit preserves transverse wavevector',
            rows=records),indent=2),encoding='utf-8')
        assert all(r['passed']for r in records),records
    asyncio.run(execute('finite_crystal_'+str(mode),work))


@pytest.mark.zemax
def test_finite_mems_source_reference_native():
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2))
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'],temperature_c=20,adjust_index_to_environment=True)))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=1,semi_diameter=10,replace_solves=True),
            dict(surface=2,surface_type='UserDefined',surface_file='us_mems.dll',material='N-BK7',thickness=5,semi_diameter=5,
                parameters={1:4,2:4,3:10,4:10,5:0,6:-10,7:10,8:45,13:0,14:5},replace_solves=True)]))
        path=e.folder/'model.zos';await e.call('save_lens_as',dict(path=str(path)));records=[]
        n=sellmeier(.55,glass_coefficients())
        for reload in (False,True):
            if reload:await e.call('open_lens',dict(path=str(path)))
            points=[(1,-3.75),(1,-1.25),(1,1.25),(1,3.75)]
            data=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(input_mode='Direct',start_surface=1,target_surface=2,
                rays=[dict(x=x,y=y,z=0,l=0,m=0,n=1)for x,y in points]))))
            for (x,y),row in zip(points,data['rows'],strict=True):
                pixel_row=1+math.floor((y+5)/2.5);state=(5//(3**(pixel_row-1)))%3
                A=math.radians((0,-10,10)[state]);B=math.pi/4
                normal=(math.sin(A)*math.sin(B),math.sin(A)*math.cos(B),-math.cos(A))
                expected=snell((0,0,1),normal,1,n)
                for i in range(3):e.check('source-defined MEMS direction',row['direction'][i],expected[i])
                e.check('source-defined MEMS plane Sag',row['position'][2],0)
                records.append(dict(reloaded=reload,pixel_row=pixel_row,state=state,normal=normal,actual=row,expected=expected))
        (e.folder/'mems-reference.json').write_text(json.dumps(dict(source='installed DLL/Surfaces/US_mems.c case5; independent Python implementation',rows=records),indent=2),encoding='utf-8')
    asyncio.run(execute('finite_mems',work))


@pytest.mark.zemax
def test_finite_grid_grin_fixture_boundary_native():
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2,count=2))
        source=Path(r'C:\Program Files\ANSYS Inc\v242\Zemax OpticStudio\ZemaxData\Glasscat\Sample.GGD')
        assert source.is_file()
        import numpy as np
        table=np.loadtxt(source,skiprows=1,encoding='utf-16');axis=table.reshape(21,21,21,-1)
        symmetry_errors=[float(np.max(abs(axis[:,:,:,3]-axis[::-1,:,:,3]))),
                         float(np.max(abs(axis[:,:,:,3]-axis[:,::-1,:,3])))]
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=1,semi_diameter=.4,replace_solves=True),
            dict(surface=2,surface_type='GridGradient',surface_file='Sample.GGD',parameters={1:.005},thickness=3.8,semi_diameter=.4,replace_solves=True),
            dict(surface=3,thickness=1,material='',semi_diameter=.4,replace_solves=True)]))
        path=e.folder/'model.zos';await e.call('save_lens_as',dict(path=str(path)))
        for reload in (False,True):
            if reload:await e.call('open_lens',dict(path=str(path)))
            geometry=await e.call('get_surface_geometry',dict(request=dict(surface=2,points=[dict(x=0,y=0),dict(x=.1,y=-.1)])))
            for row in geometry['rows']:e.check('GGD entrance is a plane',row['sag'],0)
        (e.folder/'grid-grin-reference.json').write_text(json.dumps(dict(source=str(source),status='deferred',
            offset_symmetry_errors=symmetry_errors,
            reason='supplied grid has nonzero transverse gradient; tri-cubic derivative/boundary reference is not established by the documented interpolation label',
            verified_scope='file selection, flat entrance Sag and save/reload; no GRIN ray numerical pass'),indent=2),encoding='utf-8')
    asyncio.run(execute('finite_grid_grin_boundary',work))


@pytest.mark.zemax
def test_finite_hybrid_object_access_boundary_native():
    async def work(e):
        cases=json.loads((Path(__file__).parent/'reference_data/official-surfaces.json').read_text(encoding='utf-8'))
        case=next(c for c in cases if c['native_type']=='NONSEQCO')
        await e.call('open_lens',dict(path=case['file']))
        response=await e.call('get_nsc_objects',dict(request={}),okay=False)
        assert response.get('ok')is False and response['error']['code']=='UNSUPPORTED_MODE',response
        (e.folder/'hybrid-boundary.json').write_text(json.dumps(dict(status='deferred',fixture=case,
            reason='existing object entry addresses pure NonSequential system, not the NCE editor inside LDE NonSequential component',
            response=response,scope='API boundary observed; no mixed-model optical numerical pass'),indent=2),encoding='utf-8')
    asyncio.run(execute('finite_hybrid_boundary',work))
