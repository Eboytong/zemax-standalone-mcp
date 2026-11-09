"""Controlled native temperature response for missing/placeholder AGF data."""
from pathlib import Path
import json
import math
import os
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0] = [str(ROOT), str(ROOT/'src'), str(ROOT/'scripts/probes/PO-01')]
from probe_common import adapter, paged_result, poll_task, write_json
from tests.support import athermal_reference as reference
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.models import SystemPatch

MATERIALS = ('BK7G18', 'B270', 'F2HTI', 'P-SK57Q1', 'REALVIEW_2.0', 'LF5G15', 'SF66')
TEMPERATURES = (19.99, 20.0, 20.01)
WAVELENGTH = 0.55


def catalog_records(path):
    records, current = {}, None
    for line in Path(path).read_text(encoding='utf-8-sig', errors='replace').splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == 'NM':
            current = dict(name=parts[1], formula=int(float(parts[2])), raw=[line])
            records[parts[1].upper()] = current
        elif current is not None:
            current['raw'].append(line)
            if parts[0] in ('CD', 'TD', 'ED'):
                current[parts[0].lower()] = [None if v in ('_', '-') else float(v) for v in parts[1:]]
    return records


def environment_request(temperature):
    return SystemPatch(temperature_c=temperature, pressure_atm=1.0,
        adjust_index_to_environment=True).model_dump(exclude_unset=True)


def temperature_comparison(values):
    if len(values) != 3 or any(not math.isfinite(v) for v in values):
        raise ValueError('Three finite indices in temperature order are required')
    derivative = (values[2]-values[0])/(TEMPERATURES[2]-TEMPERATURES[0])
    fixed_absolute = -values[1]*reference.air_dn_dt(WAVELENGTH,20)/reference.air_index(WAVELENGTH,20)
    return dict(native_relative_dn_dt=derivative, fixed_relative_dn_dt=0.0,
        fixed_absolute_relative_dn_dt=fixed_absolute,
        fixed_relative_error=abs(derivative), fixed_absolute_error=abs(derivative-fixed_absolute))


def evaluate_record(record):
    """Compare saved native inputs with independent formulas; creates no instance."""
    results = []
    for entry in record['materials']:
        item = dict(material=entry['material'])
        results.append(item)
        try:
            if entry.get('error'):
                raise ValueError(entry['error'])
            effective = dict(entry['catalog_record'])
            native = entry['native_catalog_properties']
            raw = native['properties']
            if not effective.get('td'):
                if any(float(raw[k]) != 0 for k in ('D0','D1','D2','E0','E1','Ltk')):
                    raise ValueError('Missing TD does not have the documented zero default')
                effective['td'] = [0.]*6+[float(raw['Temp'])]
                item['thermal_source'] = 'manual six-zero default, confirmed by native readback; Temp from IMaterialsCatalog'
            else:
                item['thermal_source'] = 'AGF TD'
            coefficients = list(effective.get('cd') or [])
            item['coefficient_overrides'] = []
            for coefficient in native['coefficients']:
                i = coefficient['native_index']
                if i >= len(coefficients):
                    raise ValueError('Catalog has fewer coefficient positions than the native formula')
                if coefficients[i] is None:
                    item['coefficient_overrides'].append(dict(index=i,catalog_value=None,
                        native_value=coefficient['value'],native_name=coefficient['name'],
                        source='formal IMaterialsCatalog.GetFitCoefficient actual input'))
                    coefficients[i] = coefficient['value']
                elif abs(coefficients[i]-coefficient['value']) > 1e-13*max(1,abs(coefficients[i])):
                    raise ValueError('Non-placeholder AGF coefficient differs from native actual input')
            effective['cd'] = coefficients
            item['reference_entry'] = effective
            predicted = reference.catalog_thermal_power(effective,record['wavelength_um'])
            maps=[]
            for report in record['reports']:
                row = next(r for r in report['rows'] if str(r['material']).upper()==entry['material'])
                error=abs(row['thermal_power_per_celsius']-predicted)
                maps.append(dict(system_temperature_c=report['temperature_c'],
                    actual=row['thermal_power_per_celsius'],reference=predicted,error=error,
                    passed=error <= record['map_tolerance']))
            item['map_comparisons']=maps
            item['system_index_comparisons']=[]
            for sample in entry['samples']:
                predicted=reference.system_relative_index(effective,record['wavelength_um'],sample['temperature_c'])
                error=abs(predicted-sample['index'])
                item['system_index_comparisons'].append(dict(temperature_c=sample['temperature_c'],
                    actual=sample['index'],reference=predicted,error=error,passed=error<=1e-12))
        except Exception as exc:
            item['error']=dict(type=type(exc).__name__,message=str(exc))
    complete=[r for r in results if not r.get('error')]
    return dict(source_version=record['source_version'],map_tolerance=record['map_tolerance'],
        index_tolerance=1e-12,source='independent formulas applied to saved AGF and formal actual coefficients',
        results=results,summary=dict(material_count=len(results),error_count=len(results)-len(complete),
        map_pass_count=sum(c['passed'] for r in complete for c in r['map_comparisons']),
        map_max_error=max((c['error'] for r in complete for c in r['map_comparisons']),default=None),
        index_pass_count=sum(c['passed'] for r in complete for c in r['system_index_comparisons']),
        index_max_error=max((c['error'] for r in complete for c in r['system_index_comparisons']),default=None)))


def run(folder):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    os.environ['ZEMAX_STATE_DIR'] = str(folder/'state')
    backend = Backend(Config(Config.from_env().install_dir, folder/'native'))
    calls = []
    call = adapter(backend, calls)
    record = dict(probe='athermal missing data temperature controls', source_version='0.1.62 working tree',
        wavelength_um=WAVELENGTH, temperatures_c=TEMPERATURES, map_tolerance=5e-9,
        hypotheses=['fixed relative index', 'fixed absolute index; air conversion remains active'],
        calls=calls, reports=[], materials=[], cleanup_failures=[])
    snapshot = None
    try:
        call('connect')
        call('new_system')
        record['context'] = backend.context()
        baseline = call('get_system_settings')
        before = call('get_surfaces', dict(start=0,count=100))
        source, work = backend.source_path, backend.work_path
        snapshot = backend._checkpoint('athermal_missing_data')
        catalog = Path.home()/'Documents/Zemax/Glasscat/SCHOTT.AGF'
        records = catalog_records(catalog)
        record['catalog'] = str(catalog)
        call('update_system_settings', dict(settings=SystemPatch(material_catalogs=['SCHOTT'],
            wavelengths=[dict(wavelength_um=WAVELENGTH)],primary_wavelength=1).model_dump(exclude_unset=True)))
        for temperature in (15.0,20.0,25.0):
            call('update_system_settings', dict(settings=environment_request(temperature)))
            task = poll_task(call,call('run_analysis',dict(request=dict(kind='athermal_glass_map'))),record)
            if task['state'] != 'succeeded':
                raise RuntimeError(dict(temperature=temperature,task=task))
            report = paged_result(call,task['task_id'],record)
            selected = [r for r in report['rows'] if str(r['material']).upper() in MATERIALS]
            record['reports'].append(dict(temperature_c=temperature,actual_settings=call('get_system_settings'),
                rows=selected, report=report, task=task))
        from System import Array,Double
        for name in MATERIALS:
            entry = dict(material=name,catalog_record=records[name],samples=[])
            record['materials'].append(entry)
            try:
                call('update_surfaces',dict(changes=[dict(surface=1,material=records[name]['name'],replace_solves=True)]))
                entry['actual_surface'] = call('get_surfaces',dict(start=1,count=1))
                properties = call('get_material_properties',dict(catalog='SCHOTT',material=records[name]['name'],
                    include_internal_transmission=False,include_birefringence=False))
                entry['native_catalog_properties'] = properties
                effective = dict(records[name])
                if not effective.get('td'):
                    raw = properties['properties']
                    coefficients = [float(raw[k]) for k in ('D0','D1','D2','E0','E1','Ltk')]
                    entry['native_missing_thermal_coefficients_are_zero'] = all(v==0 for v in coefficients)
                    if not entry['native_missing_thermal_coefficients_are_zero']:
                        raise RuntimeError('Missing thermal data does not read back as the documented zero default')
                    effective['td'] = [0.]*6+[float(raw['Temp'])]
                    entry['effective_thermal_source'] = 'documented six-zero default; reference temperature read from IMaterialsCatalog.Temp'
                entry['reference_entry'] = effective
                for temperature in TEMPERATURES:
                    call('update_system_settings',dict(settings=environment_request(temperature)))
                    actual = call('get_system_settings')
                    if actual['temperature_c'] != temperature or not actual['adjust_index_to_environment']:
                        raise RuntimeError('Environment readback differs')
                    values = Array[Double]([0.0])
                    count = int(backend.system.LDE.GetIndex(1,1,values))
                    index = float(values[0])
                    if count != 1 or not math.isfinite(index) or index <= 0:
                        raise RuntimeError(dict(get_index_return=count,index=index))
                    entry['samples'].append(dict(temperature_c=temperature,index=index,actual_settings=actual))
                entry['comparison'] = temperature_comparison([s['index'] for s in entry['samples']])
                if None not in effective.get('cd',[]):
                    for sample in entry['samples']:
                        sample['independent_system_index'] = reference.system_relative_index(effective,WAVELENGTH,sample['temperature_c'])
                        sample['independent_system_index_error'] = abs(sample['index']-sample['independent_system_index'])
                    entry['system_index_tolerance'] = 1e-12
                    entry['system_index_passed'] = all(s['independent_system_index_error'] <= entry['system_index_tolerance'] for s in entry['samples'])
                    entry['effective_thermal_power'] = reference.catalog_thermal_power(effective,WAVELENGTH)
                    row = next(r for r in record['reports'][1]['rows'] if str(r['material']).upper()==name)
                    entry['thermal_map_error'] = abs(entry['effective_thermal_power']-row['thermal_power_per_celsius'])
                    entry['thermal_map_passed'] = entry['thermal_map_error'] <= record['map_tolerance']
                ed = records[name].get('ed',[])
                if ed and ed[0] is not None:
                    c=entry['comparison']
                    c['from_native_derivative_thermal_power']=c['native_relative_dn_dt']/(entry['samples'][1]['index']-1)-ed[0]*1e-6
                try:
                    entry['independent_thermal_power']=reference.catalog_thermal_power(records[name],WAVELENGTH)
                except ValueError as exc:
                    entry['independent_reference_unavailable']=str(exc)
            except Exception as exc:
                entry['error']=dict(type=type(exc).__name__,message=str(exc))
    except Exception as exc:
        record['error']=dict(type=type(exc).__name__,message=str(exc))
    finally:
        if snapshot is not None:
            try:
                holder={}
                backend._restore_model(holder,snapshot,source,work)
                record['restoration']=holder.get('restoration')
                record['settings_restored']=call('get_system_settings')==baseline
                record['surfaces_restored']=call('get_surfaces',dict(start=0,count=100))==before
            except Exception as exc:
                record['cleanup_failures'].append(dict(step='restore',error=repr(exc)))
        try:
            record['disconnect']=call('disconnect')
        except Exception as exc:
            record['cleanup_failures'].append(dict(step='disconnect',error=repr(exc)))
        write_json(folder/'probe.json',record)
    print(json.dumps(dict(folder=str(folder),error=record.get('error'),
        materials=[dict(material=e['material'],error=e.get('error'),comparison=e.get('comparison')) for e in record['materials']],
        settings_restored=record.get('settings_restored'),surfaces_restored=record.get('surfaces_restored'),
        cleanup_failures=record['cleanup_failures']),ensure_ascii=False))
    return record

if __name__ == '__main__':
    if sys.argv[1] == '--evaluate':
        source=Path(sys.argv[2]).resolve()
        result=evaluate_record(json.loads(source.read_text(encoding='utf-8')))
        result['source_record']=str(source)
        write_json(source.parent/'independent-reference.json',result)
        print(json.dumps(result['summary']))
        sys.exit(1 if result['summary']['error_count'] else 0)
    result=run(sys.argv[1])
    if result.get('error') or result['cleanup_failures']:
        sys.exit(1)
