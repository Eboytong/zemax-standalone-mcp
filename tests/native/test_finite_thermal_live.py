"""Curved/curved contact, radial cap branches, signed global placement and reload."""
import asyncio
import json
import math
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.finite_reference import thermal_edge_gap


def catalog_cte():
    selected=False
    for line in (Path.home()/'Documents/Zemax/Glasscat/SCHOTT.AGF').read_text(encoding='utf-8-sig',errors='replace').splitlines():
        if line.startswith('NM '):selected=line.split()[1]=='N-BK7'
        if selected and line.startswith('ED '):return float(line.split()[1])
    raise ValueError('N-BK7 ED thermal expansion missing')


@pytest.mark.zemax
@pytest.mark.parametrize('cte',[0,50,100])
def test_finite_thermal_contact_branches_native(cte):
    async def work(e):
        import numpy as np
        await e.model();await e.call('insert_surfaces',dict(at=2,count=5))
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'],temperature_c=20,
            adjust_index_to_environment=True,global_reference_surface=1)))
        await e.call('update_surfaces',dict(changes=[
            dict(surface=1,thickness=2,material='N-BK7',semi_diameter=3,replace_solves=True),
            dict(surface=2,surface_type='CoordinateBreak',parameters={4:5},thickness=0,replace_solves=True),
            dict(surface=3,radius=50,thickness=10,tce=cte,material='',semi_diameter=3,replace_solves=True),
            dict(surface=4,radius=-70,thickness=2,material='N-BK7',semi_diameter=3,replace_solves=True),
            dict(surface=5,surface_type='CoordinateBreak',parameters={3:-3},thickness=0,replace_solves=True),
            dict(surface=6,radius=50,thickness=7,tce=50,material='',semi_diameter=3,replace_solves=True),
            dict(surface=7,radius=-70,thickness=2,material='N-BK7',semi_diameter=3,replace_solves=True)]))
        temperatures=[20,-20,19.99,20.01,60]
        await e.call('update_surfaces',dict(changes=[dict(surface=s,mechanical_semi_diameter=3,
            chip_zone=0,replace_solves=True)for s in (1,3,4,6,7)]))
        operands=[dict(type='TEMP',cells=[dict(configuration=i,value=t)for i,t in enumerate(temperatures,1)])]
        for s,L in ((3,10),(6,7)):
            operands.append(dict(type='THIC',parameters={1:s},cells=[dict(configuration=i,value=L)for i in range(1,6)]))
        for s,R in ((3,50),(4,-70),(6,50),(7,-70)):
            operands.append(dict(type='CRVT',parameters={1:s},cells=[dict(configuration=i,value=1/R)for i in range(1,6)]))
        for s in (1,3,4,6,7):
            for kind,value in (('SDIA',3),('MCSD',3),('CHZN',0)):
                operands.append(dict(type=kind,parameters={1:s},cells=[dict(configuration=i,value=value)for i in range(1,6)]))
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)for _ in range(4)],operands=operands)))
        rows=(await e.call('get_configurations',dict(request={})))['rows']
        await e.call('update_configurations',dict(request=dict(operands=[dict(operand=row['operand'],cells=[dict(configuration=i,
            solve=dict(mode='thermal_pickup',configuration=1))for i in range(2,6)])for row in rows if row['type']in('THIC','CRVT','SDIA','MCSD','CHZN')])))
        glass=catalog_cte();a,b=map(math.radians,(5,-3))
        ry=np.array([[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]])
        rx=np.array([[1,0,0],[0,math.cos(b),-math.sin(b)],[0,math.sin(b),math.cos(b)]])
        records=[]
        for configuration,temp in enumerate(temperatures,1):
            await e.call('set_configuration',dict(configuration=configuration))
            first,branch=thermal_edge_gap(10,50,-70,3,cte,glass,temp-20)
            second,branch2=thermal_edge_gap(7,50,-70,3,50,glass,temp-20)
            s=(await e.call('get_surfaces',dict(start=3,count=5)))['surfaces']
            lengths=[s[0]['cells']['thickness']['value'],s[3]['cells']['thickness']['value']]
            for row in (s[0],s[1],s[3],s[4]):
                mechanical=row['properties']['mechanical']
                e.check('explicit heated mechanical radius mm',mechanical['mechanical_semi_diameter']['value'],3*(1+glass*1e-6*(temp-20)))
                e.check('zero chip zone mm',mechanical['chip_zone']['value'],0)
            geometry=(await e.call('get_surface_geometry',dict(request=dict(surface=7))))['global_transform']
            expected=np.array([0,0,2])+ry@np.array([0,0,first+2])+ry@rx@np.array([0,0,second])
            checks=[abs(v-w)<=1e-8+1e-7*abs(w)for v,w in zip(lengths,(first,second))]
            for i in range(3):
                checks.append(abs(geometry['translation'][i]-expected[i])<=1e-8+1e-7*abs(expected[i]))
                for j in range(3):checks.append(abs(geometry['rotation'][i][j]-(ry@rx)[i,j])<=1e-8+1e-7*abs((ry@rx)[i,j]))
            records.append(dict(configuration=configuration,temperature_C=temp,expected_lengths_mm=[first,second],actual_lengths_mm=lengths,
                branches=[branch,branch2],surfaces=s,actual_transform=geometry,expected_translation_mm=expected.tolist(),passed=all(checks)))
        file=e.folder/'model.zos';await e.call('save_lens_as',dict(path=str(file)));await e.call('open_lens',dict(path=str(file)))
        after=await e.call('get_surface_geometry',dict(request=dict(surface=7)))
        for i,v in enumerate(records[-1]['actual_transform']['translation']):e.check('thermal reload endpoint',after['global_transform']['translation'][i],v)
        reread=(await e.call('get_surfaces',dict(start=3,count=5)))['surfaces']
        for index in (0,1,3,4):
            for key in ('mechanical_semi_diameter','chip_zone'):
                e.check('thermal reload '+key,reread[index]['properties']['mechanical'][key]['value'],records[-1]['surfaces'][index]['properties']['mechanical'][key]['value'])
        reloaded_mce=await e.call('get_configurations',dict(request={}))
        assert all(all(cell['solve']['mode']=='ThermalPickup'for cell in row['cells'][1:])for row in reloaded_mce['rows']if row['type']in('MCSD','CHZN','SDIA'))
        (e.folder/'thermal-contact-reference.json').write_text(json.dumps(dict(mount_cte=cte,glass_cte=glass,
            reference='manual2.1.1.4.4.2: spacer expansion plus edge correction when contact is capped at lens edge; explicit MCSD/CHZN/SDIA thermal pickup',
            nominal_mechanical_radius_mm=3,scope='zero chip-zone controlled fixture; no thermoelastic model',rows=records),indent=2),encoding='utf-8')
        assert all(r['passed']for r in records),records
    asyncio.run(execute('finite_thermal_'+str(cte),work))
