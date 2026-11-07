"""Test angular pupil coordinates against retained native data, without native execution."""
import argparse
import json
from pathlib import Path

import matplotlib.tri as tri
import numpy as np

from diffraction_reference import pupil_autocorrelation


def interpolate(axis_x, axis_y, values, x, y):
    ix = np.clip(np.searchsorted(axis_x, x) - 1, 0, len(axis_x) - 2)
    iy = np.clip(np.searchsorted(axis_y, y) - 1, 0, len(axis_y) - 2)
    tx = (x - axis_x[ix]) / (axis_x[ix + 1] - axis_x[ix])
    ty = (y - axis_y[iy]) / (axis_y[iy + 1] - axis_y[iy])
    return float((1 - ty) * ((1 - tx) * values[iy, ix] + tx * values[iy, ix + 1])
                 + ty * ((1 - tx) * values[iy + 1, ix] + tx * values[iy + 1, ix + 1]))


def run(folder, output):
    folder = Path(folder)
    record = json.loads((folder / 'autocorrelation.json').read_text(encoding='utf-8'))[0]
    rows = json.loads((folder / f"field{record['field']}-rays.json").read_text(encoding='utf-8'))
    rays = [r['ray'] for r in rows if not r['ray']['error_code'] and not r['ray']['vignette_code']]
    chief = next(r['ray'] for r in rows if r['ray']['input']['px'] == r['ray']['input']['py'] == 0)
    direction = np.asarray([r['direction'] for r in rays])
    opd = np.asarray([r['opd'] for r in rays])
    amplitude = np.sqrt([r['intensity'] for r in rays])
    grid = record['result']['grids'][0]
    native_settings = record['result']['task']['settings']['native']
    wavelength_number = native_settings['Wavelength']
    if wavelength_number < 1 or record['result']['context']['lens_units'] != 'Millimeters':
        raise ValueError('This controlled reference requires a monochromatic millimeter model')
    wavelength_mm = record['result']['system_settings']['wavelengths'][wavelength_number-1]['wavelength_um'] * .001
    output_data = dict(hypothesis='Nonlinear exit angular coordinates explain off-axis residual',
        source=str(folder), native_execution=False, absolute_tolerance=.005,
        reference='Linear triangulation of OPD and sqrt(intensity), then zero-padded complex-pupil autocorrelation; frequency lag=delta(direction cosine)/wavelength_mm',
        limitations='Convex sampled hull boundary; no independent exit-pupil amplitude/Jacobian transport or folded-pupil support',
        native_settings=record['result']['task'], wavelength_number=wavelength_number,
        wavelength_mm=wavelength_mm, records=[])
    chief_direction = np.asarray(chief['direction'])
    if abs(chief_direction[0]) > 1e-12:
        raise ValueError('This controlled experiment requires the chief ray in the YZ plane')
    tangent = np.cross(chief_direction, [1., 0., 0.])
    tangent /= np.linalg.norm(tangent)
    for name, uv in [('image_plane', direction[:, :2]),
                     ('chief_normal', np.column_stack((direction[:, 0], direction @ tangent)))]:
        triangulation = tri.Triangulation(uv[:, 0], uv[:, 1])
        phase_interp = tri.LinearTriInterpolator(triangulation, opd)
        amp_interp = tri.LinearTriInterpolator(triangulation, amplitude)
        for size in [256, 512]:
            axes = [np.linspace(uv[:, k].min(), uv[:, k].max(), size) for k in [0, 1]]
            xx, yy = np.meshgrid(*axes)
            phase = phase_interp(xx, yy)
            amp = amp_interp(xx, yy)
            pupil = (amp * np.exp(2j * np.pi * phase)).filled(0)
            acf = pupil_autocorrelation(pupil)
            frequencies = [(np.arange(2 * size) - size) * (a[1] - a[0]) / wavelength_mm for a in axes]
            points = []
            for fx, fy in [(0,0),(10,0),(30,0),(50,0),(0,10),(0,30),(0,50),(20,30),(-20,30),(20,-30)]:
                ix = round((fx - grid['min_x']) / grid['dx'])
                iy = round((fy - grid['min_y']) / grid['dy'])
                fx = grid['min_x'] + ix * grid['dx']; fy = grid['min_y'] + iy * grid['dy']
                expected = interpolate(*frequencies, acf, fx, fy)
                actual = grid['values'][iy][ix]
                points.append(dict(fx=fx, fy=fy, native=actual, reference=expected, error=abs(actual-expected)))
            output_data['records'].append(dict(mapping=name, size=size,
                direction_bounds=[[float(a[0]),float(a[-1])] for a in axes],
                points=points, maximum_error=max(p['error'] for p in points)))
    Path(output).write_text(json.dumps(output_data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps([{k:r[k] for k in ['mapping','size','maximum_error']} for r in output_data['records']]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder'); parser.add_argument('output')
    args = parser.parse_args(); run(args.folder, args.output)
