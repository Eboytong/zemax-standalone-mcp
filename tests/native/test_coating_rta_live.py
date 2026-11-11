"""Direct row-owned coating data through the real MCP stdio client."""
import asyncio
import cmath
import math
from pathlib import Path
from uuid import uuid4

import pytest

from tests.support.native import execute
from tests.support.thin_film import bk7_index


def reference(angle, wave, inward, film=None):
    n0, ns = (1., bk7_index(wave)) if inward else (bk7_index(wave), 1.)
    sine = n0*math.sin(math.radians(angle))
    c0 = math.cos(math.radians(angle))
    cs = cmath.sqrt(1-(sine/ns)**2)
    output = []
    for p in (False, True):
        q0, qs = (n0/c0, ns/cs) if p else (n0*c0, ns*cs)
        if film is None:
            r = (q0-qs)/(q0+qs)
            t = 2*q0/(q0+qs)
        else:
            n1 = film
            c1 = cmath.sqrt(1-(sine/n1)**2)
            q1 = n1/c1 if p else n1*c1
            phase = cmath.exp(-1j*2*math.pi*n1*.1*c1/wave)
            r01, r12 = (q0-q1)/(q0+q1), (q1-qs)/(q1+qs)
            denominator = 1+r01*r12*phase**2
            r = (r01+r12*phase**2)/denominator
            t = 2*q0/(q0+q1)*2*q1/(q1+qs)*phase/denominator
        reflection = abs(r)**2
        transmission = abs(t)**2*qs.real/q0.real
        output.append((reflection, transmission, 1-reflection-transmission))
    return output


@pytest.mark.zemax
def test_direct_coating_rta_stdio_fresnel_films_and_model_preservation():
    name = 'D2' + uuid4().hex[:6].upper()
    text = ('MATE '+name+'_N\n0.4 1.38 0\n0.8 1.38 0\n'
            'MATE '+name+'_K\n0.4 1.38 -0.02\n0.8 1.38 -0.02\n'
            'COAT '+name+'_FILM\n'+name+'_N .1 1 0\n'
            'COAT '+name+'_ABS\n'+name+'_K .1 1 0\n')
    resource = Path.home()/'Documents/Zemax/Coatings'/(name+'.DAT')
    resource.write_text(text, encoding='ascii')

    async def work(e):
        (e.folder/resource.name).write_text(text, encoding='ascii')
        await e.model()
        await e.call('update_system_settings', dict(settings=dict(material_catalogs=['SCHOTT'],
            files=dict(coating_file=resource.name), wavelengths=[dict(wavelength_um=.55),dict(wavelength_um=.635)])))
        await e.call('update_surfaces', dict(changes=[dict(surface=1, material='N-BK7', replace_solves=True)]))
        for coating, film in [('', None), (name+'_FILM', 1.38), (name+'_ABS', 1.38-.02j)]:
            await e.call('update_surfaces', dict(changes=[dict(surface=1, coating=coating)]))
            before = await e.call('get_surfaces', dict(start=0, count=3))
            settings = await e.call('get_system_settings')
            status = await e.call('get_status')
            conditions = [dict(wavelength=wave, angle_deg=angle, direction=direction)
                          for wave in (1,2) for angle in (0,30) for direction in ('inward','outward')]
            result = await e.call('get_coating_rta', dict(request=dict(surface=1, conditions=conditions)))
            assert result['invalid_count'] == 0 and result['total'] == 8
            for sample in result['samples']:
                expected = reference(sample['angle_deg'], sample['wavelength_um'], sample['direction']=='inward', film)
                for channel, values in zip(('s','p'), expected):
                    for metric, wanted in zip(('reflection','transmission','absorption'), values):
                        e.check(f'{coating} {sample["index"]} {channel} {metric}', sample[metric][channel], wanted,
                                atol=1e-8, rtol=1e-6)
                    e.check('energy closure', sample['energy_residual'][channel], 0, atol=1e-8, rtol=0)
            assert await e.call('get_surfaces', dict(start=0, count=3)) == before
            assert await e.call('get_system_settings') == settings
            assert (await e.call('get_status'))['model_revision'] == status['model_revision']
        await e.call('update_surfaces', dict(changes=[dict(surface=1, coating='')]))
        tir = await e.call('get_coating_rta', dict(request=dict(surface=1,
                       conditions=[dict(wavelength_um=.55, angle_deg=60, direction='outward')])))
        for channel in ('s','p'):
            e.check('TIR reflection', tir['samples'][0]['reflection'][channel], 1)
            e.check('TIR transmission', tir['samples'][0]['transmission'][channel], 0)
        bad = await e.call('get_coating_rta', dict(request=dict(surface=1, conditions=[dict(wavelength=99)])), okay=False)
        assert bad['error']['code'] == 'INDEX_OUT_OF_RANGE'
        await e.call('get_coating_rta', dict(request=dict(surface=1)))

    async def guarded_work(e):
        try:
            await work(e)
        finally:
            await e.call('disconnect')

    try:
        asyncio.run(execute('direct_coating_rta', guarded_work))
    finally:
        resource.unlink(missing_ok=True)
