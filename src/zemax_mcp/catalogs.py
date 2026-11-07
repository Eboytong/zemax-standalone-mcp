"""Native stock lens discovery, search and identity-selected loading."""
import math
from .analyses import scalar_settings
from .detectors import checked_setting, check_setting_readback
from .errors import ZemaxError
from .catalog_models import CatalogSearch

FILTERS=dict(equi='IncShapeEqui',bi='IncShapeBi',plano='IncShapePlano',meniscus='IncShapeMeniscus',spherical='IncTypeSpherical',grin='IncTypeGRIN',aspheric='IncTypeAspheric',toroidal='IncTypeToroidal')

def catalog_settings(backend, tool, q):
    vendors=[str(x) for x in tool.GetAllVendors() if str(x).strip()]
    matches=[v for v in vendors if v.casefold()==q.vendor.casefold()]
    if len(matches)!=1:
        raise ZemaxError('INVALID_RESOURCE','镜头厂商目录不存在或不唯一。',vendor=q.vendor,available=vendors)
    values=dict(SelectedVendor=matches[0],UseEFL=q.efl_mm is not None,UseEPD=q.epd_mm is not None)
    if q.efl_mm:values.update(MinEFL=q.efl_mm.minimum,MaxEFL=q.efl_mm.maximum)
    if q.epd_mm:
        if q.epd_mm.minimum<0:raise ZemaxError('INVALID_ARGUMENT','入口瞳直径范围必须非负。')
        values.update(MinEPD=q.epd_mm.minimum,MaxEPD=q.epd_mm.maximum)
    values.update({native:getattr(q,key) for key,native in FILTERS.items()})
    if q.number_of_elements is None:tool.SetNumberOfElementsAny()
    else:values['NumberOfElements']=q.number_of_elements
    for name,value in values.items():checked_setting(backend.native,tool,name,value)
    for name,value in values.items():check_setting_readback(tool,name,value)
    actual=scalar_settings(tool)
    actual['number_of_elements_mode']='any' if q.number_of_elements is None else 'explicit'
    return actual

def lens_data(lens, index):
    if lens is None:raise ZemaxError('INVALID_RESULT_DATA','原生目录返回空镜头。',native_index=index)
    row=dict(native_index=index,vendor=str(lens.Vendor),lens_name=str(lens.LensName),efl_mm=float(lens.EFL),epd_mm=float(lens.EPD),
        shape=str(lens.Shape),type=str(lens.Type),number_of_elements=int(lens.NumberOfElements),telecentric=bool(lens.Telecentric))
    if any(not math.isfinite(row[k])for k in ('efl_mm','epd_mm')):
        raise ZemaxError('INVALID_RESULT_DATA','镜头目录包含非有限尺寸。',row=row)
    return row

class CatalogsMixin:
    def get_lens_catalogs(self, req):
        self._require_sequential()
        tool=self.system.Tools.OpenLensCatalogs()
        try:
            result=dict(vendors=[str(x)for x in tool.GetAllVendors()if str(x).strip()],settings=scalar_settings(tool),
                source='native stock catalogs',dimension_unit='millimeters',native_adoption='runtime discovery')
        except Exception:
            self._close_task_native({'native':tool});raise
        self._release_owned(tool)
        return result

    def run_lens_catalog_search(self, req):
        self._require_sequential()
        tool=self.system.Tools.OpenLensCatalogs()
        try:actual=catalog_settings(self,tool,req)
        except Exception:
            self._close_task_native({'native':tool});raise
        def collect(task):
            native=task['native']
            if not native.Succeeded:raise ZemaxError('TASK_FAILED',str(native.ErrorMessage))
            total=int(native.MatchingLenses)
            if total<0:raise ZemaxError('INVALID_RESULT_DATA','原生匹配数量为负。',total=total)
            rows=[lens_data(native.GetResult(index),index)for index in range(min(total,req.max_results))]
            return dict(rows=rows,total_matches=total,returned=len(rows),truncated=len(rows)<total,settings=scalar_settings(native),
                source='ZOS-API LensCatalogs',dimension_unit='millimeters',native_result_index_base=0)
        return self._start_task('lens_catalog_search',tool,dict(request=req.model_dump(),actual=actual),collector=collect)

    def run_catalog_lens(self, req):
        self._require_sequential()
        if req.action=='insert' and req.at_surface>=self.system.LDE.NumberOfSurfaces:
            raise ZemaxError('INDEX_OUT_OF_RANGE','插入位置超出当前LDE。',at_surface=req.at_surface)
        before=self._design_snapshot()
        self._mutate('catalog_'+req.action)
        tool=self.system.Tools.OpenLensCatalogs()
        try:actual=catalog_settings(self,tool,CatalogSearch(vendor=req.vendor))
        except Exception:
            self._close_task_native({'native':tool});raise
        def collect(task):
            native=task['native']
            if not native.Succeeded:raise ZemaxError('TASK_FAILED',str(native.ErrorMessage))
            total=int(native.MatchingLenses)
            if total<0 or total>100000:
                raise ZemaxError('INVALID_RESULT_DATA','原生目录数量超出可读取范围。',total=total)
            matches=[]
            for index in range(total):
                lens=native.GetResult(index)
                if str(lens.LensName)==req.lens_name:matches.append((lens,lens_data(lens,index)))
            if len(matches)!=1:
                raise ZemaxError('INVALID_SELECTION','镜头名称在所选厂商目录中不存在或不唯一。',vendor=req.vendor,lens_name=req.lens_name,matches=len(matches))
            lens,selected=matches[0]
            if selected['vendor'].casefold()!=req.vendor.casefold():
                raise ZemaxError('INVALID_RESULT_DATA','原生候选厂商与请求不符。',selected=selected)
            if req.action=='load':lens.LoadLens(False)
            elif lens.InsertLensSeq(req.at_surface,req.ignore_object,req.reverse_surface_geometry)is False:
                raise ZemaxError('CATALOG_INSERT_FAILED','原生镜头插入返回false。',selected=selected,checkpoint=self.last_checkpoint)
            if not self._close_task_native(task):raise ZemaxError('CLEANUP_FAILED','镜头目录资源释放未确认。')
            self._require_sequential()
            if req.action=='load':
                self.source_path=None
                self._working_copy()
            settings=self.get_system_settings(None)
            return dict(action=req.action,selected=selected,before=before,after=self._design_snapshot(),system_settings_after=settings,
                checkpoint=self.last_checkpoint,source='ZOS-API catalog lens',dimension_unit='millimeters',working_file=str(self.work_path))
        return self._start_task('catalog_'+req.action,tool,dict(request=req.model_dump(),actual=actual),before=before,collector=collect)

    def run_catalog_evaluation(self, req):
        from .models import UpdateSurfaces, SurfacePatch
        from .evaluation import Cancelled
        self._require_sequential()
        def flow(task):
            source,work=self.source_path,self.work_path
            snapshot=self._checkpoint('catalog_evaluation')
            task['baseline']=dict(path=snapshot,context=self.context())
            comparison=None
            try:
                for index,candidate in enumerate(req.candidates):
                    self._cancel_boundary(task)
                    self._restore_model(task,snapshot,source,work)
                    row=dict(index=index,name=candidate.name)
                    try:
                        if candidate.lens:
                            loaded=yield from self._child_job(task,self.run_catalog_lens,candidate.lens)
                            row.update(selected=loaded['selected'],catalog_task=loaded['task']['task_id'])
                        if candidate.materials:
                            patch=UpdateSurfaces(changes=[SurfacePatch(surface=item.surface,material=item.material,replace_solves=item.replace_solve)for item in candidate.materials])
                            row['materials']=self.update_surfaces(patch)
                        if req.common_settings:
                            row['common_settings_actual']=self.update_system_settings(req.common_settings)
                        row.update((yield from self._evaluate(task,req.evaluation)))
                        system=row.get('conditions',{}).get('system',{})
                        keys=('mode','configuration','lens_units','mtf_units','afocal_image_space','aperture','field_type','field_normalization','fields','wavelengths','temperature_c','pressure_atm','adjust_index_to_environment','polarization','ray_aiming')
                        current={k:system[k]for k in keys if k in system}
                        if comparison is None:
                            comparison=current
                            task['payload']=dict(comparison_settings=comparison)
                        elif current!=comparison:
                            raise ZemaxError('CONDITION_MISMATCH','候选评价条件与首个候选不同，请通过common_settings统一条件。',expected=comparison,actual=current)

                        if req.save_candidates:
                            path=self.directory/(task['task_id']+f'_candidate_{index}.zos')
                            self.system.SaveAs(str(path));self.system.SaveAs(str(self.work_path))
                            row['saved_design']=str(path)
                        row['state']='succeeded'
                    except Cancelled:raise
                    except Exception as exc:
                        row.update(state='failed',error=self._evaluation_error(exc))
                        if self.requires_reconnect:
                            task['rows'].append(row);raise
                    task['rows'].append(row)
                    task['progress']=int((index+1)*100/len(req.candidates))
                    yield
            finally:
                task['summary']=dict(requested=len(req.candidates),processed=len(task['rows']),succeeded=sum(r['state']=='succeeded'for r in task['rows']),failed=sum(r['state']=='failed'for r in task['rows']))
                self._restore_model(task,snapshot,source,work)
        return self._composite('catalog_evaluation',req.model_dump(),flow)
