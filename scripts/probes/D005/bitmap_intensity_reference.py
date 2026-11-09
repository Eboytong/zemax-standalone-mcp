"""Compare retained native scalar intensity against exact ideal-image bin areas."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0]=[str(ROOT/'src')]
from zemax_mcp.bitmap_image import parse_bitmap_report


def evaluate(source):
    spec=importlib.util.spec_from_file_location('bitmap_geometry',Path(__file__).with_name('bitmap_geometry.py'))
    geometry=importlib.util.module_from_spec(spec);spec.loader.exec_module(geometry)
    retained=json.loads(Path(source).read_text(encoding='utf-8'))
    cases=[]
    for case in retained['cases']:
        request=case['request']
        path=Path(next(a['path'] for a in case['result']['artifacts'] if a['kind']=='native_text'))
        parsed=parse_bitmap_report(path.read_text(encoding='utf-16'))
        values=parsed['normalized_intensity']
        channels=geometry.independent_reference(request['rotation'])
        nx,ny=parsed['nx'],parsed['ny']
        summed=[[sum(channels[c][y][x] for c in 'RGB') for x in range(nx)] for y in range(ny)]
        peak=max(map(max,summed))
        reference=[[v/peak for v in row] for row in summed]
        error=max(abs(v-reference[y][x]) for y,row in enumerate(values) for x,v in enumerate(row))
        reversed_error=max(abs(v-reference[ny-1-y][x]) for y,row in enumerate(values) for x,v in enumerate(row))
        # Preserve the existing geometry diagnostic bound, before a new native run.
        bound=6/request['rays_per_pixel']**.5+2/255
        cases.append(dict(rotation=request['rotation'],rays_per_pixel=request['rays_per_pixel'],
            raw_report=str(path),nx=nx,ny=ny,native_efficiency_percent=parsed['efficiency_percent'],
            maximum_absolute_error=error,wrong_vertical_orientation_error=reversed_error,
            atol=bound,passed=error<=bound,reference=reference))
    return dict(source=str(Path(source).resolve()),
        method='ideal magnification -1; exact source-rectangle/detector-bin areas; summed RGB energy divided by its peak',
        scope='retained finite-conjugate controls, native current normalization only',
        cases=cases,passed=all(c['passed'] for c in cases))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source');parser.add_argument('output')
    args=parser.parse_args();result=evaluate(args.source)
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=result['passed'],cases=[{k:v for k,v in c.items() if k!='reference'} for c in result['cases']]),ensure_ascii=False))
    if not result['passed']:sys.exit(1)
