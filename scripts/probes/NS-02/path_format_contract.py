"""Compare native ZRD and PAF path statistics from one controlled trace."""
import json
import os
from pathlib import Path
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts/probes/PO-01')]
from probe_common import adapter, paged_result, poll_task, write_json
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap
from zemax_mcp.imaging import new_analysis, checked, check
from zemax_mcp.analyses import scalar_settings
from zemax_mcp.path_analysis import collect_paths


def run(destination, multipath=False):
    folder = Path(destination).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ['ZEMAX_STATE_DIR'] = str(folder / 'state')
    backend = Backend(Config(Config.from_env().install_dir, folder / 'native'))
    record = dict(calls=[], cases=[], cleanup_failures=[],
                  hypothesis='PAF and ZRD may expose different threshold-uncategorized results',
                  multipath=multipath)
    call = adapter(backend, record['calls'])

    def state():
        return dict(settings=call('get_system_settings'), objects=call('get_nsc_objects'),
                    merit=call('get_merit_function'),
                    configuration=int(backend.system.MCE.CurrentConfiguration))

    try:
        call('connect')
        call('new_system', dict(mode='NonSequential'))
        call('insert_nsc_objects', dict(at=1, count=3 if multipath else 2))
        catalogs = call('get_system_settings')['material_catalogs']
        call('update_system_settings', dict(material_catalogs=list(dict.fromkeys(catalogs + ['SCHOTT'])),
                                            wavelengths=[dict(wavelength_um=.55)]))
        call('update_nsc_objects', dict(changes=[
            dict(object=1, object_type='SourceRay', data=dict(NumberOfAnalysisRays=10, Power=.8 if multipath else 1, ZCosine=1),
                 sources=dict(RandomPolarization=False, Jx=1, Jy=0)),
            dict(object=2, object_type='RectangularVolume', z=5, material='N-BK7',
                 data=dict(X1HalfWidth=1 if multipath else 10, Y1HalfWidth=10, X2HalfWidth=1 if multipath else 10, Y2HalfWidth=10, ZLength=2)),
            dict(object=3, object_type='DetectorRectangle', z=12,
                 data=dict(XHalfWidth=6, YHalfWidth=6, NumberXPixels=7, NumberYPixels=5)),
        ] + ([dict(object=4, object_type='SourceRay', x=3,
                   data=dict(NumberOfAnalysisRays=10, Power=.2, ZCosine=1),
                   sources=dict(RandomPolarization=False, Jx=1, Jy=0))] if multipath else [])))
        record['context'] = backend.context()
        before = state()
        trace = backend.system.Tools.OpenNSCRayTrace()
        owner = dict(native=trace)
        started = False
        try:
            trace.ClearDetectors(0)
            trace.UsePolarization = True
            trace.SplitNSCRays = False
            trace.ScatterNSCRays = False
            trace.IgnoreErrors = False
            trace.NumberOfCores = 1
            trace.SetRandomSeed(42)
            trace.SaveRays = True
            trace.SaveRaysFile = 'format_compare.zrd'
            trace.SavePaths = True
            trace.SavePathsFile = 'format_compare.paf'
            trace.Filter = ''
            record['trace_settings'] = {name: getattr(trace, name) for name in (
                'UsePolarization', 'SplitNSCRays', 'ScatterNSCRays', 'SaveRays', 'SaveRaysFile',
                'SavePaths', 'SavePathsFile', 'Filter')}

            def collect(task):
                result = dict(succeeded=bool(trace.Succeeded), error=str(trace.ErrorMessage),
                              dead_ray_errors=float(trace.DeadRayErrors),
                              total_energy=float(trace.GetTotalRayEnergy()))
                if not backend._close_task_native(task):
                    raise RuntimeError('trace close failed')
                return result

            task = backend._start_task('path_format_trace', trace, record['trace_settings'],
                                       collector=collect, budget_seconds=60)
            started = True
            record['trace_task'] = poll_task(call, task, record, timeout_s=75)
            if record['trace_task']['state'] != 'succeeded':
                raise RuntimeError('trace failed')
        finally:
            if not started:
                record['setup_close'] = backend._close_task_native(owner)
        work = Path(str(backend.system.SystemFile)).parent
        zrd = work / str(record['trace_settings']['SaveRaysFile'])
        paf = work / str(record['trace_settings']['SavePathsFile'])
        record['generated'] = [dict(path=str(p), exists=p.exists(), bytes=p.stat().st_size if p.exists() else 0)
                               for p in (zrd, paf)]
        if not zrd.is_file() or not paf.is_file():
            raise RuntimeError('both native databases were not generated')
        reader = call('read_zrd', dict(path=str(zrd), max_segments=100))
        reader = poll_task(call, reader, record, timeout_s=75)
        if reader['state'] != 'succeeded':
            raise RuntimeError('ZRD reader failed')
        segments = paged_result(call, reader['task_id'], record, chunk=7)
        record['segments'] = segments
        record['reference_detector_w'] = sum(row['Intensity'] for row in segments['rows'] if row['HitObject'] == 3)
        for database in (zrd, paf):
            for first, last, minimum in ([(1, -1, 0), (1, -1, .5), (1, -1, 1), (1, 10, 0), (11, 20, 0)] if multipath else [(1, -1, 0), (1, -1, 1)]):
                entry = dict(format=database.suffix, threshold=minimum, first_ray=first, last_ray=last)
                record['cases'].append(entry)
                if database.suffix=='.paf' and (minimum!=0 or first!=1 or last!=-1):
                    # Deliberately inspect raw native adoption beyond the guarded public contract.
                    tool=new_analysis(backend,'PathAnalysis')
                    try:
                        settings=unwrap(tool.GetSettings())
                        values=dict(RayDatabaseFile=database.name,FirstRay=first,LastRay=last,
                                    RelativeMinimumFlux=minimum,FilterString='',GeneratePathFilters=False)
                        for name,value in values.items():checked(backend.native,settings,name,value)
                        for name,value in values.items():check(backend.native,settings,name,value)
                        entry['execution_route']='raw native adoption probe; public request rejects these controls'
                        task=backend._start_task('path_analysis',tool,dict(native=scalar_settings(settings)),
                            analysis=True,collector=lambda t:collect_paths(backend,t))
                    except Exception:
                        backend._close_task_native(dict(native=tool))
                        raise
                else:
                    entry['execution_route']='public run_analysis'
                    task = call('run_analysis', dict(request=dict(kind='path_analysis', path=str(database),
                                                                  relative_minimum_flux=minimum, first_ray=first, last_ray=last)))
                entry['task'] = poll_task(call, task, record, timeout_s=75)
                entry['result'] = paged_result(call, task['task_id'], record, chunk=1)
                write_json(folder / 'probe.json', record)
        after = state()
        record['model_preserved'] = {k: before[k] == after[k] for k in before}
    except Exception as exc:
        record['error'] = dict(type=type(exc).__name__, message=str(exc))
    finally:
        backend.shutdown()
        receipt = folder / 'state/close_receipt.json'
        record['close_receipt'] = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
        write_json(folder / 'probe.json', record)
    print(json.dumps(dict(output=str(folder), error=record.get('error'),
                          reference=record.get('reference_detector_w'),
                          cases=[dict(format=c['format'], threshold=c['threshold'],
                                      state=c.get('task', {}).get('state'),
                                      rows=c.get('result', {}).get('total'),
                                      uncategorized=c.get('result', {}).get('uncategorized'))
                                 for c in record['cases']],
                          preserved=record.get('model_preserved'), receipt=record['close_receipt']),
                     ensure_ascii=False))
    return record


if __name__ == '__main__':
    result = run(sys.argv[1], multipath='--multipath' in sys.argv[2:])
    if result.get('error'):
        sys.exit(1)
