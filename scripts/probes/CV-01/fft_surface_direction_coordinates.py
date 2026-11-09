"""Offline angular-coordinate hypotheses using retained 509 ray samples.

No fitted coordinate scale, phase correction or acceptance-tolerance change.
Interpolated OPD/intensity are retained ray outputs, not a new native result.
"""
from pathlib import Path
import json
import sys
import numpy as np
import matplotlib.tri as tri

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
SOURCE=ROOT/'.local/fixtures/surface_mtf509_pupil_3517781fe1'
OUT=ROOT/'.local/evidence/development/CV-01/direction-coordinates-20261109/result.json'
TOLERANCE=.005


def autocorrelation(pupil):
    spectrum=np.fft.fft2(pupil,s=tuple(2*n for n in pupil.shape))
    return abs(np.fft.fftshift(np.fft.ifft2(abs(spectrum)**2)))/np.sum(abs(pupil)**2)


def interpolate(acf,spacing,fx,fy):
    y=fy/spacing[1]+acf.shape[0]//2
    x=fx/spacing[0]+acf.shape[1]//2
    ix=int(np.floor(x));iy=int(np.floor(y));a=x-ix;b=y-iy
    return float(acf[iy,ix]*(1-a)*(1-b)+acf[iy,ix+1]*a*(1-b)
        +acf[iy+1,ix]*(1-a)*b+acf[iy+1,ix+1]*a*b)


def triangle_area_ratio(source, target, triangles):
    """Unsigned coordinate area ratio; singular/folded meshes need separate data."""
    def determinants(points):
        edges=points[triangles[:,1:]]-points[triangles[:,0,None]]
        return edges[:,0,0]*edges[:,1,1]-edges[:,0,1]*edges[:,1,0]
    before=determinants(np.asarray(source));after=determinants(np.asarray(target))
    if not np.all(np.isfinite(before)) or not np.all(np.isfinite(after)) or np.any(before==0) or np.any(after==0):
        raise ValueError('Coordinate mesh contains a singular or nonfinite triangle')
    orientation=np.sign(after/before)
    if not np.all(orientation==orientation[0]):
        raise ValueError('Coordinate mesh changes orientation')
    return abs(after/before)


def lattice_triangles(cells):
    """Join adjacent retained pupil cells without zero-area hull triangles."""
    cells=np.asarray(cells,dtype=int)
    lookup={tuple(cell):index for index,cell in enumerate(cells)}
    triangles=[]
    for iy in range(int(cells[:,0].min()),int(cells[:,0].max())):
        for ix in range(int(cells[:,1].min()),int(cells[:,1].max())):
            corners=[lookup.get(c) for c in ((iy,ix),(iy,ix+1),(iy+1,ix+1),(iy+1,ix))]
            present=[c for c in corners if c is not None]
            if len(present)==4:
                triangles.extend(((present[0],present[1],present[2]),(present[0],present[2],present[3])))
            elif len(present)==3:
                triangles.append(present)
    return np.asarray(triangles,dtype=int)


def run(flux_control=False):
    report=dict(item='CV-01.FftSurfaceMtf',source=str(SOURCE),source_version='0.1.62 working tree',
        computation='offline retained-ray coordinate hypothesis; no native execution',
        absolute_tolerance=TOLERANCE,normalization='zero-lag pupil power',records=[],
        amplitude_control='intensity/Jacobian vs unchanged intensity' if flux_control else 'unchanged intensity')
    previous=json.loads((SOURCE/'autocorrelation.json').read_text(encoding='utf-8'))
    for old in previous:
        field=old['field']
        entries=json.loads((SOURCE/f'field{field}-rays.json').read_text(encoding='utf-8'))
        valid=[e for e in entries if not e['ray']['error_code'] and not e['ray']['vignette_code']]
        rays=[e['ray'] for e in valid]
        cells=[[e['iy'],e['ix']] for e in valid]
        chief=next(r for r in rays if r['input']['px']==r['input']['py']==0)
        z=np.asarray(chief['direction']);z=z/np.linalg.norm(z)
        x=np.array([1.,0.,0.]);x-=np.dot(x,z)*z;x/=np.linalg.norm(x)
        y=np.cross(z,x)
        directions=np.asarray([r['direction'] for r in rays])
        phase=np.asarray([r['opd'] for r in rays])
        intensity=np.asarray([r['intensity'] for r in rays])
        entrance=np.asarray([[r['input']['px'],r['input']['py']] for r in rays])
        wavelength=old['summary']['wavelengths'][0]['wavelength_um']*.001
        for name,coordinates in [('image_xy',directions[:,:2]),('chief_normal',np.column_stack((directions@x,directions@y)))]:
            # Use original cell adjacency: general tessellation can create
            # numerically collinear triangles at the circular pupil boundary.
            triangles=lattice_triangles(cells) if flux_control else None
            triangulation=tri.Triangulation(coordinates[:,0],coordinates[:,1],triangles=triangles)
            phase_interpolator=tri.LinearTriInterpolator(triangulation,phase)
            intensity_interpolator=tri.LinearTriInterpolator(triangulation,intensity)
            ratio=triangle_area_ratio(entrance,coordinates,triangulation.triangles) if flux_control else None
            for size in (256,512):
                low=coordinates.min(axis=0);high=coordinates.max(axis=0)
                step=(high-low)/(size-2)
                axes=[(low[i]+high[i])/2+(np.arange(size)-size/2)*step[i] for i in (0,1)]
                xx,yy=np.meshgrid(*axes)
                sampled_phase=phase_interpolator(xx,yy)
                sampled_intensity=intensity_interpolator(xx,yy)
                mask=np.ma.getmaskarray(sampled_phase)|np.ma.getmaskarray(sampled_intensity)
                weights={'uniform':np.ones(xx.shape)}
                if flux_control:
                    triangle=triangulation.get_trifinder()(xx,yy)
                    weights['flux_area']=np.where(triangle<0,0,1/ratio[np.maximum(0,triangle)])
                for weight_name,weight in weights.items():
                    pupil=np.where(mask,0,np.sqrt(np.maximum(0,sampled_intensity.filled(0))*weight)*np.exp(2j*np.pi*sampled_phase.filled(0)))
                    acf=autocorrelation(pupil);spacing=step/wavelength
                    points=[]
                    for point in old['comparisons']['paraxial']['points']:
                        ref=interpolate(acf,spacing,point['fx'],point['fy'])
                        points.append(dict(fx=point['fx'],fy=point['fy'],native=point['native'],reference=ref,error=abs(ref-point['native'])))
                    report['records'].append(dict(field=field,coordinates=name,size=size,amplitude=weight_name,chief_direction=z.tolist(),
                        triangulation='transported entrance cells' if flux_control else 'target Delaunay',
                        coordinate_min=low.tolist(),coordinate_max=high.tolist(),frequency_spacing=spacing.tolist(),
                        area_ratio_range=[float(ratio.min()),float(ratio.max())] if ratio is not None else None,
                        support_cells=int(np.count_nonzero(~mask)),points=points,
                        maximum_error=max(p['error'] for p in points),passed=all(p['error']<=TOLERANCE for p in points)))
    output=OUT.parent/'flux-control.json' if flux_control else OUT
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for r in report['records']:print(r['field'],r['coordinates'],r['size'],r['amplitude'],r['maximum_error'],r['passed'])
    print('Output:',output)
    return report


if __name__=='__main__':run(flux_control='--flux-control' in sys.argv[1:])
