"""Inspect native result shapes for failures found in the B003 family smoke."""
import json,time,traceback
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap
from zemax_mcp.imaging import new_analysis
from zemax_mcp.analyses import scalar_settings

folder=Path('verification/development/CV-01/outlets265').resolve()
folder.mkdir(exist_ok=False)
b=Backend(Config(Config.from_env().install_dir,folder/'native'))
record={'items':[]}
try:
    record['connect']=b.dispatch('connect',{});assert record['connect']['ok']
    assert b.dispatch('open_lens',{'path':str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')})['ok']
    for name in ['SeidelDiagram','Foucault','FftPsfLineEdgeSpread']:
        tool=new_analysis(b,name)
        item={'kind':name,'settings':scalar_settings(unwrap(tool.GetSettings()))}
        record['items'].append(item)
        def collect(task):
            r=unwrap(tool.GetResults())
            item['result_type']=str(r.GetType().FullName)
            item['valid']=bool(r.IsValid)
            item['methods']=[str(m) for m in r.GetType().GetMethods()]
            item['header']=None if r.HeaderData is None or r.HeaderData.Lines is None else [str(x) for x in r.HeaderData.Lines]
            item['counts']={n:int(getattr(r,n)) for n in ['NumberOfDataSeries','NumberOfDataGrids','NumberOfDataGridsRgb','NumberOfDataScatterPoints','NumberOfDataScatterPointsRgb']}
            item['text_exported']=bool(r.GetTextFile(str(folder/(name+'.txt'))))
            item['series']=[]
            for i in range(r.NumberOfDataSeries):
                s=r.GetDataSeries(i)
                item['series'].append(dict(description=str(s.Description),labels=None if s.SeriesLabels is None else list(s.SeriesLabels),x_null=s.XData is None,y_null=s.YData is None))
            item['grids']=[]
            for i in range(r.NumberOfDataGrids):
                g=r.GetDataGrid(i)
                item['grids'].append(dict(nx=int(g.Nx),ny=int(g.Ny),values_null=g.Values is None))
            try:item['existing_collector']=b._collect_general_analysis(task)
            except Exception:item['collector_traceback']=traceback.format_exc()
            return {'outlets_inspected':True,'artifacts':[]}
        task=b._start_task(name,tool,dict(kind=name,native=item['settings']),analysis=True,collector=collect)
        deadline=time.monotonic()+60
        while task['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            b.tick();task=b._task_view(b._task(task['task_id']));time.sleep(.02)
        item['task']=task
finally:
    record['disconnect']=b.dispatch('disconnect',{})
    (folder/'summary.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'closed':record['disconnect']['ok'],'items':[{'kind':i['kind'],'counts':i.get('counts'),'header':i.get('header'),'series':i.get('series'),'grids':i.get('grids'),'traceback':i.get('collector_traceback')} for i in record['items']]}))
