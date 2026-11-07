"""Read local native catalog data and apply checked transmission settings."""
import math
from contextlib import contextmanager
from .data import unwrap
from .errors import ZemaxError
from .detectors import check_setting_value
from .analyses import scalar_settings
from .imaging import new_analysis,checked,check,collect_imaging


def choose(values,name,label):
    matches=[str(x)for x in values if str(x).casefold()==name.casefold()]
    if len(matches)!=1:raise ZemaxError('INVALID_RESOURCE','材料资源名称不存在或不唯一。',resource=label,requested=name,available=[str(x)for x in values])
    return matches[0]


def choose_catalog(values,name):
    wanted=name.casefold().removesuffix('.agf')
    matches=[str(value) for value in values if str(value).casefold().removesuffix('.agf')==wanted]
    if len(matches)!=1:
        raise ZemaxError('INVALID_RESOURCE','材料目录名称不存在或不唯一。',requested=name,available=[str(value) for value in values])
    return matches[0]


@contextmanager
def owned_catalog(backend):
    tool=backend.system.Tools.OpenMaterialsCatalog()
    holder={'native':tool};error=None
    try:yield tool
    except Exception as exc:
        error=exc if isinstance(exc,ZemaxError) else ZemaxError('NATIVE_ERROR',str(exc),type=type(exc).__name__)
        if error is exc:raise
        raise error from exc
    finally:
        if not backend._close_task_native(holder):
            if error is None:raise ZemaxError('CLEANUP_FAILED','材料目录工具关闭未确认。',cleanup_warnings=holder.get('cleanup_warnings'))
            if isinstance(error,ZemaxError):error.details['cleanup_warnings']=holder.get('cleanup_warnings')


def material_table(data,fields,start=0,count=200):
    total=int(data.NumberOfPoints)
    if not 0<=total<=100000:raise ZemaxError('INVALID_RESULT_DATA','材料表点数无效。',count=total)
    rows=[]
    for index in range(start,min(total,start+count)):
        point=data.GetDataPoint(index)
        row=dict(native_index=index,**{field:float(getattr(point,name))for field,name in fields.items()})
        if any(not math.isfinite(v)for v in row.values()):raise ZemaxError('INVALID_RESULT_DATA','材料表包含非有限数值。',native_index=index)
        rows.append(row)
    return rows


def table_page(data,q):
    total=int(data.NumberOfPoints);end=min(total,q.table_start+q.table_count)
    return dict(start=q.table_start,count=max(0,end-q.table_start),total=total,next_start=end if end<total else None)


def resolve_glasses(backend,q):
    catalogs=backend.system.SystemData.MaterialCatalogs
    loaded=[str(x)for x in catalogs.GetCatalogsInUse()if str(x).strip()]
    selected=choose_catalog(loaded,q.catalog)
    tables={c:[str(x)for x in catalogs.GetMaterialsInCatalog(c)]for c in loaded}
    names=[choose(tables[selected],name,'material')for name in q.glasses]
    for name in names:
        sources=[c for c,glasses in tables.items()if any(x.casefold()==name.casefold()for x in glasses)]
        if len(sources)!=1:raise ZemaxError('AMBIGUOUS_MATERIAL','多个已加载目录包含同名材料，原生Glass字符串不能确定目录身份。',material=name,catalogs=sources)
    return selected,names


def configure_transmission(backend,s,q):
    catalog,glasses=resolve_glasses(backend,q)
    values={f'Glass{i+1}':glasses[i]if i<len(glasses)else ''for i in range(4)}
    values.update(MinimumWave=q.minimum_wavelength_um,MaximumWave=q.maximum_wavelength_um,
        MinimumTransmission=q.minimum_transmission,MaximumTransmission=q.maximum_transmission,Thickness=q.thickness_mm)
    for name,value in values.items():checked(backend.native,s,name,value)
    for name,value in values.items():check(backend.native,s,name,value)
    actual=scalar_settings(s)
    if actual.get('unavailable_fields'):raise ZemaxError('SETTING_UNAVAILABLE','材料透过率设置回读失败。',details=actual['unavailable_fields'])
    return dict(kind=q.kind,requested=q.model_dump(),native=actual,catalog=catalog,glasses=glasses,units=dict(wavelength='micrometers',thickness='millimeters',transmittance='dimensionless internal transmittance excluding surface Fresnel loss'))


def run_internal_transmission(backend,q):
    backend._require_sequential()
    # Resolve resources before opening an analysis owned by the task.
    resolve_glasses(backend,q)
    tool=new_analysis(backend,'InternalTransmissionvsWavelength')
    try:settings=configure_transmission(backend,unwrap(tool.GetSettings()),q)
    except Exception:
        backend._close_task_native({'native':tool});raise
    return backend._start_task('analysis',tool,settings,analysis=True,collector=lambda task:collect_imaging(backend,task))


class MaterialsMixin:
    def get_material_properties(self,q):
        with owned_catalog(self)as tool:
            catalog=choose_catalog(tool.GetAllCatalogs(),q.catalog)
            tool.SelectedCatalog=catalog
            check_setting_value('SelectedCatalog',catalog,str(tool.SelectedCatalog))
            material=choose(tool.GetAllMaterials(),q.material,'material')
            tool.SelectedMaterial=material
            check_setting_value('SelectedMaterial',material,str(tool.SelectedMaterial))
            count=int(tool.NumberOfFitCoefficients)
            if not 0<=count<=1000:raise ZemaxError('INVALID_RESULT_DATA','材料拟合系数数量无效。',count=count)
            coefficients=[dict(native_index=i,name=str(tool.GetCoefficientName(i)),value=float(tool.GetFitCoefficient(i)))for i in range(count)]
            if any(not math.isfinite(c['value'])for c in coefficients):raise ZemaxError('INVALID_RESULT_DATA','材料系数包含非有限值。')
            actual=scalar_settings(unwrap(tool))
            if actual.get('unavailable_fields'):raise ZemaxError('SETTING_UNAVAILABLE','材料属性回读失败。',details=actual['unavailable_fields'])
            result=dict(catalog=catalog,material=material,properties=actual,coefficients=coefficients,
                source='IMaterialsCatalog; no SaveCatalog invocation',native_indexing='zero-based coefficient/table API; actual indices and coefficient names retained',
                units=dict(wavelength='micrometers',transmission_thickness='millimeters',thermal_and_mechanical='native property definitions and catalog reference conditions'))
            if q.include_internal_transmission:
                table=tool.GetInternalTransmissionData()
                result['internal_transmission']=material_table(table,dict(wavelength_um='Wavelength',transmission='Transmission',thickness_mm='Thickness'),q.table_start,q.table_count)
                result['internal_transmission_page']=table_page(table,q)
            if q.include_birefringence:
                table=tool.GetInternalBirefringenceData()
                result['birefringence']=material_table(table,dict(wavelength_um='Wavelength',k='K',k11='K11',k12='K12'),q.table_start,q.table_count)
                result['birefringence_page']=table_page(table,q)
            if q.star_samples:
                from .star_materials import evaluate_material
                result['star_samples'] = evaluate_material(self,catalog,material,q.star_samples)
            check_setting_value('SelectedCatalog',catalog,str(tool.SelectedCatalog));check_setting_value('SelectedMaterial',material,str(tool.SelectedMaterial))
            return result
