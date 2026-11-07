import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Inspect formal matrix spot result outlets with adopted zero defocus."""
import json,sys,time
from pathlib import Path
ROOT=PROJECT_ROOT;sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.imaging import new_analysis,checked
from zemax_mcp.data import unwrap
from zemax_mcp.analyses import scalar_settings
folder=ROOT/'verification/development/CV-01/outlets088';folder.mkdir(exist_ok=False)
b=Backend(Config(Config.from_env().install_dir,folder/'native'));record=dict(items=[])
try:
    record['connect']=b.dispatch('connect',{});assert record['connect']['ok']
    assert b.dispatch('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))['ok']
    for name in ['MatrixSpot','ConfigurationMatrixSpot']:
        tool=new_analysis(b,name);s=unwrap(tool.GetSettings())
        checked(b.native,s,'DeltaFocus',0.)
        item=dict(kind=name,settings=scalar_settings(s));record['items'].append(item)
        def collect(task):
            r=unwrap(tool.GetResults())
            d=dict(valid=bool(r.IsValid),counts={n:int(getattr(r,n))for n in ['NumberOfDataSeries','NumberOfDataGrids','NumberOfDataGridsRgb','NumberOfDataScatterPoints','NumberOfDataScatterPointsRgb']},text_exported=bool(r.GetTextFile(str(folder/(name+'.txt')))))
            spot=unwrap(r.SpotData);d['spot_data']=None if spot is None else dict(type=str(spot.GetType().FullName),methods=[str(m)for m in spot.GetType().GetMethods()])
            item['outlets']=d;return d
        task=b._start_task(name,tool,dict(kind=name,native=item['settings']),analysis=True,collector=collect)
        deadline=time.monotonic()+30
        while task['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            b.tick();task=b._task_view(b._task(task['task_id']));time.sleep(.02)
        item['task']=task
finally:
    record['disconnect']=b.dispatch('disconnect',{})
    (folder/'summary.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(closed=record['disconnect']['ok'],items=[dict(kind=i['kind'],counts=i.get('outlets',{}).get('counts'),text=i.get('outlets',{}).get('text_exported'),spot=i.get('outlets',{}).get('spot_data'))for i in record['items']])))
