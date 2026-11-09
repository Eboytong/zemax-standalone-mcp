"""Selected material index curves through the formal native lens-data getter."""
import math

from .errors import ZemaxError

CURVE_DEFAULTS=dict(minimum_wavelength_um=.4,maximum_wavelength_um=.8,samples=101,
    use_temperature_pressure=False,temperature_c=20.,pressure_atm=1.)
INDEX_DEFAULTS=CURVE_DEFAULTS | dict(minimum_index=0.,maximum_index=0.)
DISPERSION_DEFAULTS=CURVE_DEFAULTS | dict(minimum_dispersion=0.,maximum_dispersion=0.)

def uses_index(q):
    explicit={key for key in q.model_fields_set-{'kind','method'} if getattr(q,key) is not None}
    if q.method=='native' and explicit:
        raise ZemaxError('UNSUPPORTED_SETTING','本机色散专题未提供可回读的材料和范围选择。',settings=sorted(explicit))
    return q.method not in {'auto','native'} or q.method=='auto' and bool(explicit)


def set_wavelengths(table,values):
    while int(table.NumberOfWavelengths)>1:
        previous=int(table.NumberOfWavelengths)
        table.RemoveWavelength(previous)
        if int(table.NumberOfWavelengths)!=previous-1:
            raise ZemaxError('SETTING_REJECTED','材料分析副本无法清除旧波长。')
    for i,value in enumerate(values,1):
        wave=table.GetWavelength(1) if i==1 else table.AddWavelength(value,1.)
        if wave is None or int(table.NumberOfWavelengths)!=i:
            raise ZemaxError('SETTING_REJECTED','材料分析副本未添加请求波长。',wavelength_number=i)
        wave.Wavelength=value;wave.Weight=1.
    actual=[float(table.GetWavelength(i).Wavelength) for i in range(1,len(values)+1)]
    if any(not math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-14) for a,b in zip(actual,values)):
        raise ZemaxError('SETTING_REJECTED','材料分析副本波长回读不符。',requested=values,actual=actual)
    return actual


def read_indices(system,count):
    from System import Array,Double
    values=Array[Double]([0.]*count)
    returned=int(system.LDE.GetIndex(1,count,values))
    result=[float(v) for v in values]
    if returned!=count or any(not math.isfinite(v) or v<=0 for v in result):
        raise ZemaxError('INVALID_RESULT_DATA','ILDE.GetIndex返回无效折射率或数量。',
                         expected_count=count,returned_count=returned,values=[str(v) for v in result])
    return returned,result


def derivative_stencil(wavelength,low,high):
    """Fourth-order derivative with all evaluation nodes inside the resource range."""
    h=min(1e-4,(high-low)/8)
    if not h>0:raise ZemaxError('INVALID_RESOURCE','材料波长范围无法计算导数。',minimum=low,maximum=high)
    if wavelength-2*h>=low and wavelength+2*h<=high:
        offsets=(-2,-1,0,1,2);coefficients=(1,-8,0,8,-1);denominator=12*h
    elif wavelength+4*h<=high:
        offsets=(0,1,2,3,4);coefficients=(-25,48,-36,16,-3);denominator=12*h
    else:
        offsets=(0,-1,-2,-3,-4);coefficients=(25,-48,36,-16,3);denominator=12*h
    return [wavelength+i*h for i in offsets],[v/denominator for v in coefficients]


def run_material_index(backend,q):
    from .materials import resolve_glasses
    from .material_models import MaterialProperties
    derivative=q.kind=='dispersion_vs_wavelength'
    defaults=DISPERSION_DEFAULTS if derivative else INDEX_DEFAULTS
    q=q.model_copy(update={key:value for key,value in defaults.items() if getattr(q,key) is None})
    display_keys=('minimum_dispersion','maximum_dispersion') if derivative else ('minimum_index','maximum_index')
    display=[getattr(q,key) for key in display_keys]
    backend._require_sequential();backend._require_work()
    table_names=[name for name in q.glasses if name.casefold().endswith('.ztg')]
    normal=[name for name in q.glasses if name not in table_names]
    if table_names:
        from pathlib import Path
        from .materials import choose_catalog
        from .gradium import glasscat_directory
        catalog=choose_catalog(backend.system.SystemData.MaterialCatalogs.GetCatalogsInUse(),q.catalog)
        root,reason=glasscat_directory(backend.native.application)
        if root is None:raise ZemaxError('INVALID_RESOURCE','表格玻璃目录不可用。',reason=reason)
        tables={}
        for name in table_names:
            matches=[p for p in root.glob('*') if p.is_file() and p.name.casefold()==name.casefold() and p.suffix.casefold()=='.ztg']
            if len(matches)!=1:raise ZemaxError('INVALID_RESOURCE','表格玻璃文件不存在或不唯一。',requested=name,directory=str(root))
            path=matches[0];nodes=[]
            for line in path.read_text(encoding='utf-8-sig').splitlines():
                line=line.strip()
                if not line or line.startswith('!') or line.upper().startswith('DENSITY'):continue
                try:w,n=map(float,line.split()[:2])
                except (ValueError,TypeError) as exc:raise ZemaxError('INVALID_RESOURCE','表格玻璃数据格式错误。',path=str(path)) from exc
                if not math.isfinite(w) or not math.isfinite(n) or w<=0 or n<=0 or nodes and w<=nodes[-1][0]:
                    raise ZemaxError('INVALID_RESOURCE','表格玻璃波长或折射率无效。',path=str(path))
                nodes.append((w,n))
            if len(nodes)<2:raise ZemaxError('INVALID_RESOURCE','表格玻璃数据点不足。',path=str(path))
            tables[name.casefold()]=dict(material=path.name,path=str(path),minimum_wavelength_um=nodes[0][0],maximum_wavelength_um=nodes[-1][0],source='native ZTG resource')
        if normal:
            _,resolved=resolve_glasses(backend,q.model_copy(update=dict(glasses=normal)))
            identities={a.casefold():b for a,b in zip(normal,resolved,strict=True)}
        else:identities={}
        glasses=[tables[name.casefold()]['material'] if name in table_names else identities[name.casefold()] for name in q.glasses]
    else:
        catalog,glasses=resolve_glasses(backend,q)
        tables={}

    resources=[]
    automatic_range=(q.minimum_wavelength_um,q.maximum_wavelength_um)==(0,0)
    for material in glasses:
        if material.casefold() in tables:
            resource=tables[material.casefold()]
            low,high=resource['minimum_wavelength_um'],resource['maximum_wavelength_um']
        else:
            data=backend.get_material_properties(MaterialProperties(catalog=catalog,material=material,
                include_internal_transmission=False,include_birefringence=False))
            properties=data['properties']
            low,high=float(properties['MinimumWavelength']),float(properties['MaximumWavelength'])
            resource=dict(catalog=catalog,material=material,minimum_wavelength_um=low,maximum_wavelength_um=high)
        if not automatic_range and (q.minimum_wavelength_um<low or q.maximum_wavelength_um>high):
            raise ZemaxError('WAVELENGTH_OUT_OF_RANGE','请求范围超出材料目录有效波长。',
                material=material,requested=[q.minimum_wavelength_um,q.maximum_wavelength_um],available=[low,high])
        resources.append(resource)
    if automatic_range:
        q=q.model_copy(update=dict(minimum_wavelength_um=min(r['minimum_wavelength_um'] for r in resources),
            maximum_wavelength_um=max(r['maximum_wavelength_um'] for r in resources)))
    wavelengths=[q.minimum_wavelength_um+(q.maximum_wavelength_um-q.minimum_wavelength_um)*i/(q.samples-1)
                 for i in range(q.samples)]
    wavelengths[-1]=q.maximum_wavelength_um

    def flow(task):
        payload=dict(analysis_kind=q.kind,computation_method='finite_difference_of_native_ILDE_GetIndex' if derivative else 'native_ILDE_GetIndex',
            selection=dict(method='finite_difference' if derivative else 'index',requested_method=q.method),
            fallback_reason='Native material topic has no selectable material/range interface' if q.method=='auto' else None,
            actual_settings=dict(catalog=catalog,glasses=glasses,resources=resources,samples=q.samples,
                minimum_wavelength_um=q.minimum_wavelength_um,maximum_wavelength_um=q.maximum_wavelength_um,
                **dict(zip(display_keys,display)),
                configuration=task['context']['configuration'],automatic_wavelength_range=automatic_range),
            native_queries=[],series=[],grids=[],sample_count=0,structured_data_available=True,
            units=dict(wavelength='micrometers',value='1/micrometer' if derivative else 'dimensionless',
                       **({'dispersion':'1/micrometer'} if derivative else {'index':'dimensionless'})),
            result_source='Formal ILDE.GetIndex on a task-owned optical-system copy; native topic defaults remain available')
        task['payload']=payload
        copy=None;original=None
        try:
            backend._cancel_boundary(task)
            copy=backend.system.CopySystem()
            if copy is None:raise ZemaxError('COPY_FAILED','材料曲线无法创建独立系统副本。')
            payload['actual_settings'].update(source_system_id=int(backend.system.SystemID),analysis_system_id=int(copy.SystemID))
            copy.New(False)
            catalogs=copy.SystemData.MaterialCatalogs
            current=[str(c) for c in catalogs.GetCatalogsInUse() if str(c).strip()]
            if catalog.casefold() not in {c.casefold() for c in current} and not catalogs.AddCatalog(catalog):
                raise ZemaxError('SETTING_REJECTED','材料副本未添加所选目录。',catalog=catalog)
            for other in current:
                if other.casefold()!=catalog.casefold() and not catalogs.RemoveCatalog(other):
                    raise ZemaxError('SETTING_REJECTED','材料副本未移除其他目录。',catalog=other)
            actual_catalogs=[str(c) for c in catalogs.GetCatalogsInUse() if str(c).strip()]
            if [c.casefold() for c in actual_catalogs]!=[catalog.casefold()]:
                raise ZemaxError('SETTING_REJECTED','材料副本目录最终回读不符。',actual=actual_catalogs)
            environment=copy.SystemData.Environment
            for attr,value in (('AdjustIndexToEnvironment',q.use_temperature_pressure),
                               ('Temperature',q.temperature_c),('Pressure',q.pressure_atm)):
                setattr(environment,attr,value)
                if getattr(environment,attr)!=value:
                    raise ZemaxError('SETTING_REJECTED','材料副本环境设置未采用。',setting=attr,requested=value,actual=getattr(environment,attr))
            payload['environment']=dict(temperature_c=float(environment.Temperature),pressure_atm=float(environment.Pressure),
                use_temperature_pressure=bool(environment.AdjustIndexToEnvironment),source='formal analysis-copy environment readback')
            payload['actual_settings']['environment']=payload['environment']
            payload['actual_settings']['catalogs_in_use']=actual_catalogs
            if derivative:
                payload['differentiation']=dict(algorithm='five-point fourth-order first derivative',
                    nominal_step_um=1e-4,boundaries='one-sided fourth-order inside each material range',
                    source='explicit numerical derivative; native default topic algorithm is not asserted')
            for start in range(0,len(wavelengths),4 if derivative else 20):
                backend._cancel_boundary(task)
                selected=wavelengths[start:start+(4 if derivative else 20)]
                columns=[]
                for material,resource in zip(glasses,resources,strict=True):
                    backend._cancel_boundary(task)
                    positions=[i for i,w in enumerate(selected) if resource['minimum_wavelength_um']<=w<=resource['maximum_wavelength_um']]
                    if not positions:
                        columns.append([None]*len(selected))
                        continue
                    stencils=[derivative_stencil(selected[i],resource['minimum_wavelength_um'],resource['maximum_wavelength_um']) for i in positions] if derivative else None
                    query_wavelengths=[v for nodes,weights in stencils for v in nodes] if derivative else [selected[i] for i in positions]
                    adopted=set_wavelengths(copy.SystemData.Wavelengths,query_wavelengths)
                    surface=copy.LDE.GetSurfaceAt(1)
                    surface.Material=material
                    if str(surface.Material).casefold()!=material.casefold():
                        raise ZemaxError('SETTING_REJECTED','材料副本实际材料不符。',requested=material,actual=str(surface.Material))
                    returned,indices=read_indices(copy,len(adopted))
                    column=[None]*len(selected)
                    values=[math.fsum(w*v for w,v in zip(weights,indices[j*5:(j+1)*5],strict=True)) for j,(nodes,weights) in enumerate(stencils)] if derivative else indices
                    for i,value in zip(positions,values,strict=True):column[i]=value
                    columns.append(column)
                    payload['native_queries'].append(dict(interface='ILDE.GetIndex',surface=1,material=str(surface.Material),
                        wavelengths_um=adopted,returned_count=returned,indices=indices,
                        **(dict(derivative_stencils=[dict(wavelength_um=selected[i],nodes=nodes,weights=weights) for i,(nodes,weights) in zip(positions,stencils,strict=True)]) if derivative else {})))
                    yield
                for i,wavelength in enumerate(selected):
                    valid=[r['minimum_wavelength_um']<=wavelength<=r['maximum_wavelength_um'] for r in resources]
                    task['rows'].append(dict(index=len(task['rows']),wavelength_um=wavelength,valid=valid,
                        **{'dispersion' if derivative else 'refractive_indices':[column[i] if valid[j] else None for j,column in enumerate(columns)]}))
                payload['sample_count']=len(task['rows'])
                task['progress']=int(100*len(task['rows'])/q.samples)
            curve=dict(series=0,description='Selected material dn/dlambda' if derivative else 'Selected material refractive index',x_label='Wavelength',x_unit='micrometers',
                y_label='dn/dlambda' if derivative else 'Refractive index',y_unit='1/micrometer' if derivative else 'dimensionless',labels=glasses,value_units=['1/micrometer' if derivative else 'dimensionless']*len(glasses),
                x=[row['wavelength_um'] for row in task['rows']],y=[row['dispersion' if derivative else 'refractive_indices'] for row in task['rows']])
            if display!=[0,0]:curve['y_limits']=[display[0] or None,display[1] or None]
            payload['series']=[curve]
            payload['invalid_point_count']=sum(not valid for row in task['rows'] for valid in row['valid'])
            payload['invalid_point_reason']='Outside individual catalog wavelength validity; omitted from native queries'
        except BaseException as exc:
            original=exc
            raise
        finally:
            if copy is not None:
                try:
                    if copy.Close(False) is False:raise RuntimeError('Close(False) returned false')
                    task['restoration']=dict(required=False,restored=True,analysis_copy_closed=True,source_model_modified=False)
                except Exception as exc:
                    backend.requires_reconnect=True
                    task['restoration']=dict(required=False,restored=False,analysis_copy_closed=False,error=str(exc))
                    if original is None:raise ZemaxError('RESOURCE_CLOSE_FAILED','材料分析副本关闭失败。',native_error=str(exc)) from exc
                    if isinstance(original,ZemaxError):original.details['cleanup_error']=str(exc)
                    else:original.add_note('Material index copy cleanup failed: '+str(exc))
    return backend._composite(q.kind,q.model_dump(exclude_unset=True),flow)
