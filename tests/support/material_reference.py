"""Catalog dispersion and Snell references for sequential material solves."""
import math

# Documented d/F/C lines, OpticStudio 2024 R2 manual pp.1347-1348.
PHYSICAL_LINES = dict(d=0.5875618, F=0.4861327, C=0.6562725)
# Four-decimal classic lines that the existing model-solve checks actually use.
CLASSIC_LINES = dict(d=0.5876, F=0.4861, C=0.6563)


def sellmeier1(wavelength, coefficients):
    values = {c['name'].rstrip(':'): c['value'] for c in coefficients}
    square = wavelength * wavelength
    return math.sqrt(1 + sum(values[f'K{i}'] * square / (square - values[f'L{i}'])
                             for i in range(1, 4)))


def abbe(values):
    nd, nf, nc = values
    return (nd - 1) / (nf - nc)


def line_positions(wavelengths, lines=CLASSIC_LINES):
    """Positions of the d/F/C lines inside a wavelength list, as used for the Abbe number."""
    positions = {}
    for name in ("d", "F", "C"):
        matches = [i for i, w in enumerate(wavelengths) if math.isclose(w, lines[name], rel_tol=0, abs_tol=1e-12)]
        if len(matches) != 1:
            raise ValueError("谱线不在波长列表中或不唯一：" + name)
        positions[name] = matches[0]
    return positions


def abbe_from_wavelengths(indices, wavelengths, lines=CLASSIC_LINES):
    """Abbe number from a per-wavelength index list, with an explicit line convention."""
    positions = line_positions(wavelengths, lines)
    return abbe(tuple(indices[positions[name]] for name in ("d", "F", "C")))


def snell_rays(wavelengths, sines=(.1, .2)):
    """Direct rays through a plane interface, ordered by incidence angle then wavelength number."""
    count = len(wavelengths)
    return [dict(x=0, y=0, z=0, l=sine, m=0, n=math.sqrt(1 - sine * sine), wavelength=w)
            for sine in sines for w in range(1, count + 1)]


def snell_request(wavelengths, sines=(.1, .2)):
    """Body of the batch-ray request; the MCP surface nests it under 'request'."""
    return dict(input_mode='Direct', start_surface=0, target_surface=1, rays=snell_rays(wavelengths, sines))


def snell_indices_from_rows(rows, count, sines=(.1, .2)):
    """Indices from the first incidence angle plus the same indices at every other angle."""
    assert len(rows) == len(sines) * count, (len(rows), len(sines), count)
    assert all(r['error_code'] == 0 and r['vignette_code'] == 0 for r in rows)
    indices = [sines[0] / r['direction'][0] for r in rows[:count]]
    angles = [dict(sine=sine, indices=[sine / r['direction'][0] for r in rows[i * count:(i + 1) * count]])
              for i, sine in enumerate(sines[1:], start=1)]
    return indices, angles


async def snell_indices(e, wavelengths):
    count = len(wavelengths)
    trace = await e.finish(await e.call('run_batch_ray_trace', {'request': snell_request(wavelengths)}))
    indices, angles = snell_indices_from_rows(trace['rows'], count)
    for angle in angles:
        for wavelength, index, other in zip(wavelengths, indices, angle['indices']):
            e.check('Snell independent angle ' + str(wavelength), other, index, atol=1e-10, rtol=1e-10)
    return indices


async def model_indices(e, wavelengths, properties, nd_offset=0, vd_offset=0):
    await e.call('update_surfaces', {'changes': [{
        'surface': 1, 'replace_solves': True, 'solves': {'material': {
            'mode': 'material_model', 'index_nd': properties['Nd'] + nd_offset,
            'abbe_vd': properties['Vd'] + vd_offset, 'dpgf': properties['dPgF'],
        }},
    }]})
    return await snell_indices(e, wavelengths)
