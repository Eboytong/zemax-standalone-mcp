"""Inspect public NSC MTF sampling/result members using an owned detector model."""
import json
import sys
import time
from pathlib import Path

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap
from zemax_mcp.imaging import new_analysis


def describe(value):
    value=unwrap(value)
    if value is None:return None
    typ=value.GetType()
    return dict(type=str(typ.FullName),
        properties=[dict(name=str(p.Name),type=str(p.PropertyType),writable=bool(p.CanWrite))
                    for p in typ.GetProperties()],
        methods=[str(m) for m in typ.GetMethods() if m.IsPublic and not m.IsSpecialName
                 and str(m.DeclaringType.FullName)!='System.Object'])


def run(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'));out={};tool=None
    def call(name,args=None):
        result=b.dispatch(name,args or {})
        out.setdefault('calls',[]).append(dict(tool=name,args=args,response=result))
        assert result['ok'],result
        return result['data']
    try:
        calls=json.loads(Path('outputs/runs/nsc_mtf491_asymmetric_0048fec6c8/calls.json').read_text(encoding='utf-8'))
        for c in calls:
            if c['tool']=='run_analysis':break
            args=c['arguments'] or {}
            args=dict(args.get('request',args.get('settings',args)))
            if c['tool']=='run_nsc_ray_trace':
                args['save_zrd']=str(folder/'owned.zrd')
                task=call(c['tool'],args);deadline=time.monotonic()+90
                while task['state'] not in {'succeeded','failed','cancelled'}:
                    assert time.monotonic()<deadline
                    b.tick();task=call('get_task_status',dict(task_id=task['task_id']))
                    time.sleep(.02)
                assert task['state']=='succeeded',task
                break
            call(c['tool'],args)
        tool=new_analysis(b,'NSCGeometricMtf');s=unwrap(tool.GetSettings())
        s.Detector.SetDetectorNumber(4);s.MaximumFrequency=.625
        out['settings']=describe(s)
        tool.ApplyAndWaitForCompletion();r=unwrap(tool.GetResults())
        out['result']=describe(r)
        out['series']=[]
        for i in range(r.NumberOfDataSeries):
            series=unwrap(r.GetDataSeries(i))
            out['series'].append(dict(interface=describe(series),x=describe(series.XData),y=describe(series.YData)))
        out['text_exported']=bool(r.GetTextFile(str(folder/'native.txt')))
        out['analysis']=describe(tool)
    except Exception as exc:
        out['error']=dict(type=type(exc).__name__,message=str(exc))
        raise
    finally:
        if tool is not None:out['close']=b._close_task_native({'native':tool})
        out['disconnect']=b.dispatch('disconnect',{})
        (folder/'probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(close=out.get('close'),result_type=out.get('result',{}).get('type'),
                         series=len(out.get('series',[])),disconnect=out['disconnect']['ok'])))


if __name__=='__main__':run(sys.argv[1])
