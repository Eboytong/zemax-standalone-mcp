"""Owned finite-conjugate RGB geometry and display-normalization diagnostic."""
import json, os, sys, time
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from PIL import Image
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import clean


def independent_reference(rotation):
    # Object pixels occupy uniform cells: full Y=1 mm, X=7/5 mm.
    # Ideal conjugate magnification -1; positive native rotation is clockwise here.
    rectangles={'R':(.3,.7,-.5,.5,255),'G':(-.7,.7,-.5,-.1,160),'B':(-.7,-.1,.1,.5,96)}
    expected={}
    for channel,(x0,x1,y0,y1,weight) in rectangles.items():
        if rotation==90:x0,x1,y0,y1=y0,y1,-x1,-x0
        values=[]
        for y in range(11):
            lo_y=-.55+.1*y;dy=max(0,min(y1,lo_y+.1)-max(y0,lo_y))
            values.append([weight*dy*max(0,min(x1,-.85+.1*(x+1))-max(x0,-.85+.1*x)) for x in range(17)])
        expected[channel]=values
    peak=max(v for values in expected.values() for row in values for v in row)
    return {channel:[[v/peak for v in row] for row in values] for channel,values in expected.items()}


def run(destination):
    folder=Path(destination).resolve();folder.mkdir(parents=True,exist_ok=False)
    os.environ['ZEMAX_STATE_DIR']=str(folder/'state')
    backend=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(source_root=str(ROOT),model_reference=dict(object_distance=200,focal_length=100,image_distance=200,magnification=-1),calls=[],cases=[],error=None)
    def save(): (folder/'probe.json').write_text(json.dumps(clean(record),ensure_ascii=False,indent=2),encoding='utf-8')
    def call(name,args=None):
        r=backend.dispatch(name,args or {});record['calls'].append(dict(tool=name,arguments=args,response=r));save()
        if not r['ok']:raise RuntimeError(r)
        return r['data']
    try:
        call('connect');call('new_system')
        call('update_system_settings',dict(field_type='ObjectHeight',aperture_value=2,fields=[dict(x=0,y=0)],wavelengths=[dict(wavelength_um=.55)]))
        call('update_surfaces',dict(changes=[dict(surface=0,thickness=200,replace_solves=True),dict(surface=1,surface_type='Paraxial',parameters={'1':100},thickness=200,semi_diameter=1,is_stop=True,replace_solves=True)]))
        before=call('get_system_settings');surfaces=call('get_surfaces')
        pixels=[(255 if x<2 else 0,160 if y<2 else 0,96 if x>=4 and y>=3 else 0) for y in range(5) for x in range(7)]
        image=Image.new('RGB',(7,5));image.putdata(pixels);source=folder/'source.bmp';image.save(source)
        record['source_pixels_top_down']=[pixels[i:i+7] for i in range(0,35,7)]
        for rays,rotation in ([(10000,0),(10000,90)] if '--reference' in sys.argv else [(1,0),(1000,0),(1000,90)]):
            q=dict(kind='geometric_bitmap_image',input_file=str(source),surface=2,field_size=1,rotation=rotation,rays_per_pixel=rays,x_pixels=17,y_pixels=11,x_pixel_size=.1,y_pixel_size=.1)
            case=dict(request=q);record['cases'].append(case)
            task=call('run_analysis',dict(request=q));deadline=time.monotonic()+120
            while backend.tasks[task['task_id']]['state'] not in {'succeeded','failed','cancelled'}:
                if time.monotonic()>deadline:raise TimeoutError('bitmap geometry')
                backend.tick();time.sleep(.03)
            raw=backend.tasks[task['task_id']];case['task']=backend._task_view(raw)
            result=raw.get('result') or json.loads(Path(raw['result_path']).read_text(encoding='utf-8'))
            case['result']=result
            summaries=[]
            for grid in result.get('grids',[]):
                if grid['channel'] not in 'RGB':continue
                values=grid['values'];total=sum(map(sum,values))
                summaries.append(dict(channel=grid['channel'],total=total,maximum=max(map(max,values)),centroid_pixels=None if not total else [sum(v*(x+.5) for row in values for x,v in enumerate(row))/total,sum(v*(y+.5) for y,row in enumerate(values) for v in row)/total]))
            case['channel_summary']=summaries
            if '--reference' in sys.argv:
                expected=independent_reference(rotation)
                # Predeclared diagnostic bound: six/sqrt(N) + two display levels.
                # A pass covers this model/reference only, not the full analysis contract.
                bound=6/(rays**.5)+2/255
                comparisons=[]
                for grid in result['grids']:
                    if grid['channel'] not in 'RGB':continue
                    ref=expected[grid['channel']]
                    maximum=max(abs(v/255-ref[y][x]) for y,row in enumerate(grid['values']) for x,v in enumerate(row))
                    comparisons.append(dict(channel=grid['channel'],maximum_normalized_display_error=maximum,atol=bound,passed=maximum<=bound))
                case['independent_reference']=dict(method='analytic magnification -1, uniform rectangular source cells, clockwise rotation, exact detector-bin intersections, shared peak normalization',values=expected,comparisons=comparisons)
            save()
        record['settings_preserved']=before==call('get_system_settings')
        record['surfaces_preserved']=surfaces==call('get_surfaces')
    except Exception as exc:record['error']=repr(exc)
    finally:
        backend.shutdown();receipt=folder/'state/close_receipt.json'
        record['close_receipt']=json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None;save()
    print(json.dumps(dict(folder=str(folder),error=record['error'],cases=[dict(request=c['request'],summary=c.get('channel_summary'),state=c.get('task',{}).get('state')) for c in record['cases']],close=record['close_receipt']),ensure_ascii=False))

if __name__=='__main__':run(sys.argv[1])
