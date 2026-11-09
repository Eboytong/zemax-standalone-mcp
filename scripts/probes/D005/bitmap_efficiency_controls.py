"""Isolate source brightness/channel effects on the native GBM efficiency header."""
import json
import os
from pathlib import Path
import sys

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts/probes/PO-01')]
from PIL import Image
from probe_common import adapter,poll_task,paged_result,write_json
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


def run(destination,pixel_controls=False,field_controls=False,off_axis_controls=False):
    folder=Path(destination).resolve();folder.mkdir(parents=True,exist_ok=False)
    os.environ['ZEMAX_STATE_DIR']=str(folder/'state')
    backend=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(calls=[],cases=[],cleanup_failures=[],
        hypothesis='with identical geometry, native percent efficiency should be invariant under source channel/brightness scaling',
        independent_geometry=dict(object_distance=200,focal_length=100,image_distance=200,
            magnification=-1,source_width='source_width recorded per case',source_height=1,detector_width=1.7,detector_height=1.1),
        expected_geometric_pass_fraction=1.,diagnostic_efficiency_atol_percent=.1)
    if pixel_controls:
        record['hypothesis']='source pixel parity/dimensions may affect the native efficiency normalization'
    if field_controls:
        record['hypothesis']='breaking field symmetry may remove the efficiency multiplier observed in the on-axis model'
    if off_axis_controls:
        record['hypothesis']='nonzero X field should remove source-parity dependence and reproduce circle-area aperture throughput'
    call=adapter(backend,record['calls'])
    before=None
    try:
        call('connect');call('new_system')
        call('update_system_settings',dict(field_type='ObjectHeight',aperture_value=2,
            fields=[dict(x=.1 if off_axis_controls else 0,y=0)],wavelengths=[dict(wavelength_um=.55)]))
        call('update_surfaces',dict(changes=[dict(surface=0,thickness=200,replace_solves=True),
            dict(surface=1,surface_type='Paraxial',parameters={'1':100},thickness=200,
                 semi_diameter=1,is_stop=True,replace_solves=True)]))
        record['context']=backend.context()
        def baseline():
            return dict(settings=call('get_system_settings'),surfaces=call('get_surfaces'),
                merit=call('get_merit_function'),configurations=call('get_configurations'))
        before=baseline()
        controls=[(name,rgb,(7,5)) for name,rgb in [('red255',(255,0,0)),('red128',(128,0,0)),('green255',(0,255,0)),
                         ('blue255',(0,0,255)),('white255',(255,255,255)),('grey128',(128,128,128)),('black',(0,0,0))]]
        if pixel_controls:
            controls=[(f'white{width}x{height}',(255,255,255),(width,height)) for width,height in [(3,3),(4,4),(5,3),(6,4),(7,5),(8,6)]]
        if field_controls:
            controls=[(name,(255,255,255),(4,4)) for name in ('axis','field_x','field_y','field_xy')]
        if off_axis_controls:
            controls=[(f'white{width}x{height}',(255,255,255),(width,height)) for width,height in [(3,3),(4,4),(5,3),(6,4),(7,5),(8,6)]]
            controls += [('aperture_half',(255,255,255),(4,4)),('aperture_quarter',(255,255,255),(4,4))]
        for name,rgb,size in controls:
            source=folder/(name+'.bmp');Image.new('RGB',size,rgb).save(source)
            case=dict(name=name,source_rgb=rgb,source_size=list(size),source_width=size[0]/size[1]);record['cases'].append(case)
            if off_axis_controls:
                radius={'aperture_half':.5,'aperture_quarter':.25}.get(name)
                if radius is not None:
                    call('update_surfaces',dict(changes=[dict(surface=1,aperture=dict(type='CircularAperture',maximum_radius=radius))]))
                case['aperture_radius']=radius
                case['expected_efficiency_percent']=100. if radius is None else 100*radius**2
                case['atol_percent']=.1 if radius is None else 2.
            if field_controls:
                position={'axis':(0,0),'field_x':(.1,0),'field_y':(0,.1),'field_xy':(.1,.1)}[name]
                case['field_position']=position
                call('update_system_settings',dict(fields=[dict(x=position[0],y=position[1])]))
                case['model_readback']=call('get_system_settings')
            request=dict(kind='geometric_bitmap_image',input_file=str(source),surface=2,field_size=1,
                rotation=0,rays_per_pixel=1000,x_pixels=17,y_pixels=11,x_pixel_size=.1,y_pixel_size=.1)
            case['request']=request
            task=call('run_analysis',dict(request=request))
            case['task']=poll_task(call,task,record,timeout_s=90)
            if case['task']['state']!='succeeded':raise RuntimeError(case['task'])
            case['result']=paged_result(call,task['task_id'],record)
            report=Path(next(a['path'] for a in case['result']['artifacts'] if a['kind']=='native_text'))
            case['report_header']=report.read_text(encoding='utf-16').splitlines()[:20]
            value=case['result']['native_efficiency']['value']
            case['reported_efficiency_percent']=value
            if any(rgb):
                expected=case.get('expected_efficiency_percent',100.)
                case['difference_from_geometric_percent']=abs(value-expected)
                case['geometric_efficiency_matches']=abs(value-expected)<=case.get('atol_percent',record['diagnostic_efficiency_atol_percent'])
            write_json(folder/'probe.json',record)
        if field_controls:call('update_system_settings',dict(fields=[dict(x=0,y=0)]))
        if off_axis_controls:call('update_surfaces',dict(changes=[dict(surface=1,aperture=dict(type='None'))]))
        after=baseline();record['model_preserved']={k:before[k]==after[k] for k in before}
    except Exception as exc:record['error']=dict(type=type(exc).__name__,message=str(exc))
    finally:
        if off_axis_controls and before is not None:
            try:call('update_surfaces',dict(changes=[dict(surface=1,aperture=dict(type='None'))]))
            except Exception as exc:record['cleanup_failures'].append(dict(step='restore_aperture',error=repr(exc)))
        if field_controls and before is not None:
            try:call('update_system_settings',dict(fields=[dict(x=0,y=0)]))
            except Exception as exc:record['cleanup_failures'].append(dict(step='restore_fields',error=repr(exc)))
        try:record['disconnect']=call('disconnect')
        except Exception as exc:record['cleanup_failures'].append(dict(step='disconnect',error=repr(exc)))
        write_json(folder/'probe.json',record)
    print(json.dumps(dict(error=record.get('error'),cases=[dict(name=c['name'],efficiency=c.get('reported_efficiency_percent'),
        matches=c.get('geometric_efficiency_matches')) for c in record['cases']],preserved=record.get('model_preserved'),cleanup=record['cleanup_failures']),ensure_ascii=False))
    return record


if __name__=='__main__':
    result=run(sys.argv[1],pixel_controls='--pixel-controls' in sys.argv[2:],field_controls='--field-controls' in sys.argv[2:],
        off_axis_controls='--off-axis-controls' in sys.argv[2:])
    if result.get('error') or result['cleanup_failures']:sys.exit(1)
