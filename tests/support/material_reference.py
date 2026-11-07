"""Catalog dispersion and Snell references for sequential material solves."""
import math


def sellmeier1(wavelength, coefficients):
    values = {c['name'].rstrip(':'): c['value'] for c in coefficients}
    square = wavelength * wavelength
    return math.sqrt(1 + sum(values[f'K{i}'] * square / (square - values[f'L{i}'])
                             for i in range(1, 4)))


def abbe(values):
    nd, nf, nc = values
    return (nd - 1) / (nf - nc)


async def snell_indices(e, wavelengths):
    count = len(wavelengths)
    trace = await e.finish(await e.call('run_batch_ray_trace', {'request': {
        'input_mode': 'Direct', 'start_surface': 0, 'target_surface': 1,
        'rays': [dict(x=0, y=0, z=0, l=sine, m=0, n=math.sqrt(1-sine*sine),
                      wavelength=w) for sine in [.1, .2] for w in range(1, count+1)],
    }}))
    assert len(trace['rows']) == 2 * count
    assert all(r['error_code'] == 0 and r['vignette_code'] == 0 for r in trace['rows'])
    indices = [.1 / r['direction'][0] for r in trace['rows'][:count]]
    for wavelength, index, row in zip(wavelengths, indices, trace['rows'][count:]):
        e.check('Snell independent angle ' + str(wavelength), .2/row['direction'][0],
                index, atol=1e-10, rtol=1e-10)
    return indices


async def model_indices(e, wavelengths, properties, nd_offset=0, vd_offset=0):
    await e.call('update_surfaces', {'changes': [{
        'surface': 1, 'replace_solves': True, 'solves': {'material': {
            'mode': 'material_model', 'index_nd': properties['Nd'] + nd_offset,
            'abbe_vd': properties['Vd'] + vd_offset, 'dpgf': properties['dPgF'],
        }},
    }]})
    return await snell_indices(e, wavelengths)
