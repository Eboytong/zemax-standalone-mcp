"""Separate native environment caching from model-glass temperature conventions."""
from pathlib import Path
import json
import os
import sys
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts/probes/PO-01')]
from probe_common import adapter,write_json
from tests.support.athermal_reference import air_index
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.models import SystemPatch

WAVES=(.5875618,.4861327,.6562725)
ENVIRONMENTS=((10.,1.),(30.,1.),(20.,0.),(20.,.8))
MODEL=dict(mode='material_model',index_nd=1.6,abbe_vd=60,dpgf=.001,
    vary_index=True,vary_dpgf=True)


def environment_request(temperature,pressure):
    return SystemPatch(adjust_index_to_environment=True,temperature_c=temperature,
        pressure_atm=pressure).model_dump(exclude_unset=True)


def environment_candidates(baseline,temperature,pressure):
    if len(baseline)!=len(WAVES):
        raise ValueError('Three baseline indices are required')
    # These transform measured baseline indices only; they do not claim an
    # independent model-glass dispersion formula or replace the Nd/Vd gates.
    return dict(temperature_air=[n*air_index(w,20)/air_index(w,temperature,pressure)
        for n,w in zip(baseline,WAVES)],
        nominal_20_air=[n*air_index(w,20)/air_index(w,20,pressure)
        for n,w in zip(baseline,WAVES)])


def evaluate_record(record):
    import runpy
    reader=runpy.run_path(str(ROOT/'scripts/probes/MA-01/athermal_missing_data.py'))['catalog_records']
    catalog=Path.home()/'Documents/Zemax/Glasscat/SCHOTT.AGF'
    glass=reader(catalog)['N-BK7']
    from tests.support.athermal_reference import system_relative_index
    checks=[]
    for material in record['materials']:
        if material['material']!='N-BK7':continue
        for case in material['cases']:
            for wave,actual in zip(record['wavelengths_um'],case['after_reload']['indices']):
                expected=system_relative_index(glass,wave,case['temperature_c'],case['pressure_atm'])
                checks.append(dict(wavelength_um=wave,temperature_c=case['temperature_c'],
                    pressure_atm=case['pressure_atm'],actual=actual,reference=expected,
                    error=abs(actual-expected),passed=abs(actual-expected)<=1e-12))
    return dict(source='independent catalog/environment formulas with original input wavelength in all air-index evaluations',
        catalog=str(catalog),catalog_entry=glass,tolerance=1e-12,checks=checks,
        pass_count=sum(c['passed'] for c in checks),max_error=max((c['error'] for c in checks),default=None))


def run(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    os.environ['ZEMAX_STATE_DIR']=str(folder/'state')
    backend=Backend(Config(Config.from_env().install_dir,folder/'native'))
    calls=[];call=adapter(backend,calls)
    record=dict(item='ED-02.MaterialModel.Material',source_version='0.1.62 working tree',
        probe='model/catalog environment before update and after reload',wavelengths_um=WAVES,
        model=MODEL,environments=ENVIRONMENTS,candidate_tolerance=1e-12,calls=calls,
        materials=[],cleanup_failures=[])
    snapshot=None
    def indices():
        from System import Array,Double
        buffer=Array[Double]([0.]*len(WAVES))
        count=int(backend.system.LDE.GetIndex(1,len(WAVES),buffer))
        if count!=len(WAVES):raise RuntimeError('GetIndex returned an unexpected count')
        return [float(v) for v in buffer]
    def state():
        return dict(settings=call('get_system_settings'),surface=call('get_surfaces',dict(start=1,count=1)),
                    indices=indices(),context=backend.context())
    try:
        call('connect');call('new_system')
        record['context']=backend.context()
        baseline_settings=call('get_system_settings');baseline_surfaces=call('get_surfaces',dict(start=0,count=100))
        source,work=backend.source_path,backend.work_path
        snapshot=backend._checkpoint('model_environment_refresh')
        call('update_system_settings',dict(settings=SystemPatch(material_catalogs=['SCHOTT'],
            wavelengths=[dict(wavelength_um=w) for w in WAVES],primary_wavelength=1).model_dump(exclude_unset=True)))
        for material in ('N-BK7','MaterialModel'):
            call('update_system_settings',dict(settings=environment_request(20,1)))
            if material=='MaterialModel':
                call('update_surfaces',dict(changes=[dict(surface=1,replace_solves=True,solves={'material':MODEL})]))
            else:
                call('update_surfaces',dict(changes=[dict(surface=1,material=material,replace_solves=True)]))
            native_status=str(backend.system.UpdateStatus())
            baseline=state()
            entry=dict(material=material,baseline=baseline,initial_status=native_status,cases=[])
            record['materials'].append(entry)
            for i,(temperature,pressure) in enumerate(ENVIRONMENTS):
                call('update_system_settings',dict(settings=environment_request(temperature,pressure)))
                before=state()
                status=str(backend.system.UpdateStatus())
                updated=state()
                path=folder/(material+'-'+str(i)+'.zos')
                call('save_lens_as',dict(path=str(path)))
                call('open_lens',dict(path=str(path)))
                reloaded=state()
                candidates=environment_candidates(baseline['indices'],temperature,pressure)
                entry['cases'].append(dict(temperature_c=temperature,pressure_atm=pressure,
                    before_update=before,update_status=status,after_update=updated,after_reload=reloaded,
                    update_index_max_change=max(abs(a-b) for a,b in zip(before['indices'],updated['indices'])),
                    reload_index_max_change=max(abs(a-b) for a,b in zip(updated['indices'],reloaded['indices'])),
                    candidate_indices=candidates,
                    candidate_errors={name:max(abs(a-b) for a,b in zip(reloaded['indices'],values))
                        for name,values in candidates.items()}))
                call('update_system_settings',dict(settings=environment_request(20,1)))
    except Exception as exc:
        record['error']=dict(type=type(exc).__name__,message=str(exc))
    finally:
        if snapshot is not None:
            try:
                holder={};backend._restore_model(holder,snapshot,source,work)
                record['restoration']=holder.get('restoration')
                record['settings_restored']=call('get_system_settings')==baseline_settings
                record['surfaces_restored']=call('get_surfaces',dict(start=0,count=100))==baseline_surfaces
            except Exception as exc:record['cleanup_failures'].append(dict(step='restore',error=repr(exc)))
        try:record['disconnect']=call('disconnect')
        except Exception as exc:record['cleanup_failures'].append(dict(step='disconnect',error=repr(exc)))
        write_json(folder/'probe.json',record)
    print(json.dumps(dict(error=record.get('error'),materials=[dict(material=e['material'],
        cases=[{k:c[k] for k in ('temperature_c','pressure_atm','update_index_max_change',
            'reload_index_max_change','candidate_errors')} for c in e['cases']]) for e in record['materials']],
        settings_restored=record.get('settings_restored'),surfaces_restored=record.get('surfaces_restored'),
        cleanup_failures=record['cleanup_failures']),ensure_ascii=False))
    return record

if __name__=='__main__':
    if sys.argv[1]=='--evaluate':
        path=Path(sys.argv[2]).resolve()
        result=evaluate_record(json.loads(path.read_text(encoding='utf-8')))
        result['source_record']=str(path)
        write_json(path.parent/'catalog-reference-corrected.json',result)
        print(json.dumps(dict(pass_count=result['pass_count'],max_error=result['max_error'])))
        sys.exit(0 if result['checks'] and all(c['passed'] for c in result['checks']) else 1)
    result=run(sys.argv[1])
    if result.get('error') or result['cleanup_failures']:sys.exit(1)
