"""Serial default-report outlet discovery with bounded task lifetimes."""
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.imaging import new_analysis
from zemax_mcp.data import unwrap
from zemax_mcp.analyses import scalar_settings


def run(folder=None,selections=None):
    folder=Path(folder or ROOT/'verification/development/NS-04/outlets068').resolve()
    folder.mkdir(exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(items=[])
    def save():
        (folder/'summary.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        record['connect']=b.dispatch('connect',{});assert record['connect']['ok']
        for mode,kinds in selections or [('Sequential',['PrescriptionDataSettings','SurfaceDataSettings','PrescriptionGraphic','PartViewer']),('NonSequential',['NSCObjectViewer','PartViewer','PrescriptionDataSettings'])]:
            assert b.dispatch('new_system',dict(mode=mode))['ok']
            for kind in kinds:
                item=dict(mode=mode,kind=kind);record['items'].append(item)
                tool=None;handed=False
                try:
                    tool=new_analysis(b,kind)
                    if tool is None:
                        item['factory']='null';continue
                    item['settings']=scalar_settings(unwrap(tool.GetSettings()))
                    def collect(task):
                        result=b._collect_general_analysis(task)
                        item['result']=result
                        return result
                    task=b._start_task(kind,tool,dict(kind=kind,native=item['settings']),analysis=True,collector=collect)
                    handed=True;deadline=time.monotonic()+20;cancelled=False
                    while task['state']not in {'succeeded','failed','cancelled'}:
                        if time.monotonic()>deadline:
                            if cancelled:raise TimeoutError('Native cancellation did not reach terminal state in 10 seconds')
                            b.dispatch('cancel_task',dict(task_id=task['task_id']))
                            deadline=time.monotonic()+10;cancelled=True
                        b.tick();task=b._task_view(b._task(task['task_id']));time.sleep(.02)
                    item['task']=task
                except Exception as exc:
                    item['error']=dict(type=type(exc).__name__,message=str(exc))
                finally:
                    if tool is not None and not handed:
                        owner=dict(native=tool);item['closed']=b._close_task_native(owner)
                    save()
    finally:
        record['disconnect']=b.dispatch('disconnect',{});save()
    print(json.dumps(dict(items=len(record['items']),closed=record['disconnect']['ok'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--mode',choices=['Sequential','NonSequential'],default='Sequential')
    parser.add_argument('--items',nargs='+')
    args=parser.parse_args()
    run(args.output,[(args.mode,args.items)]if args.items else None)
