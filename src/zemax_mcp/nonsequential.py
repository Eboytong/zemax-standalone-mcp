import json,math,uuid,copy,re
from functools import wraps
from pathlib import Path
from .analyses import scalar_settings,native_setting
from .data import unwrap,dotnet_array
from .files import input_path,output_path
from .errors import ZemaxError
from .detectors import checked_setting, check_setting_readback, polar_coordinates, detector_metadata

OBJECT_FIELDS=dict(x="XPosition",y="YPosition",z="ZPosition",tilt_x="TiltAboutX",tilt_y="TiltAboutY",tilt_z="TiltAboutZ",ref_object="RefObject",inside_of="InsideOf",material="Material",comment="Comment")


def object_scope(method):
    """Temporarily select a mixed-mode group only for synchronous object tools."""
    @wraps(method)
    def scoped(self,req):
        target=getattr(req,'nsc_surface',None)
        nested=getattr(self,'_active_nsc_surface',None)
        if nested is not None:
            if target is not None and target!=nested:raise ZemaxError('INVALID_ARGUMENT','嵌套对象请求不能切换NSC组。')
            return method(self,req)
        if str(self.system.Mode)=='NonSequential':
            if target is not None:raise ZemaxError('INVALID_ARGUMENT','纯非序列系统不接受nsc_surface。')
            return method(self,req)
        if target is None:raise ZemaxError('UNSUPPORTED_MODE','混合模式对象操作需要显式nsc_surface。')
        row=self._row(target)
        if str(row.Type)!='NonSequential':raise ZemaxError('INVALID_NSC_GROUP','指定曲面不是NonSequential组件。',surface=target,actual_type=str(row.Type))
        previous=int(self.system.NCE.ActiveSurface)
        operation_error=None
        try:
            self._select_nsc_group(target)
            self._active_nsc_surface=target
            data=method(self,req)
            data['nsc_surface']=target
            return data
        except ZemaxError as exc:
            exc.details['nsc_surface']=target
            operation_error=exc.as_dict()
            raise
        finally:
            self._active_nsc_surface=None
            if int(self.system.NCE.ActiveSurface)!=previous:
                try:self._select_nsc_group(previous)
                except Exception as exc:
                    self.requires_reconnect=True
                    raise ZemaxError('RESTORE_FAILED','NSC编辑器原活动组恢复失败；请重新连接。',requested_surface=target,restore_surface=previous,checkpoint=self.last_checkpoint,native_error=str(exc),operation_error=operation_error)from exc
    return scoped


def wavelength_filter_validation():
    """Native predicate scope, separate from header or reconstructed wavelengths."""
    return dict(status="partial_native_validation", wavelength_unit="micrometers", endpoints="inclusive",
        verified="Seven unconverted fixed wavelengths; matched DetectorPolar/DetectorRectangle/DetectorColor models in uniform N-BK7; closed intervals, shared/exact endpoints, empty selection and pagination",
        known_difference="Installed 2024 R2 sample_3 fluorescence ZRD: converted rays pass X_WAVERANGE near 0.55 um despite independent segment wavelengths spanning 0.500-0.734 um; fine-band selection is not validated",
        known_difference_formats=["UncompressedFullData","CompressedFullData"],
        detector_types_tested=["DetectorPolar","DetectorRectangle","DetectorColor"],
        native_paths_tested=["Ray Database Reader (property and legacy wrappers)","Detector Viewer replay"],
        trace_options_tested=[dict(use_polarization=False,split_rays=False),dict(use_polarization=True,split_rays=False),dict(use_polarization=True,split_rays=True)],
        internal_root_cause="unconfirmed; no reliable native fine-band workaround established for the recorded sample_3 model",
        selection_scope="native ray/path selection; returned segments are not individually filtered",
        fallback="none; native filter expressions and results are preserved",
        reference="docs/nonsequential-validation.md#原生波长区间过滤")

class NonSequentialMixin:
    @object_scope
    def get_nsc_object_geometry(self,req):
        from .object_geometry import get_object_geometry
        return get_object_geometry(self,req)

    def _select_nsc_group(self,target):
        n=self.system.NCE
        accepted=n.SetActiveSurface(target)
        if accepted and int(n.ActiveSurface)==target:return
        raise ZemaxError('NSC_GROUP_SELECTION_FAILED','原生编辑器未采用请求的NSC组。',requested_surface=target,active_surface=int(n.ActiveSurface),native_return=bool(accepted))

    def _reset_detector_history(self, known=False):
        self.detector_history = []
        self.detector_history_known = known
        self.detector_records = {}
        self.detector_clear_context=(self.revision, self.system_context.get("configuration",1))

    def _detector_record(self, index):
        if index not in self.detector_records:
            self.detector_records[index] = dict(
                known=self.detector_history_known, traces=[],
                cleared_revision=self.detector_clear_context[0],
                cleared_configuration=self.detector_clear_context[1])
        return self.detector_records[index]

    def _clear_detector_records(self, detector=0):
        if detector:
            self.detector_records[detector] = dict(
                known=True, traces=[], cleared_revision=self.revision,
                cleared_configuration=self.system_context.get("configuration", 1))
        else:
            self._reset_detector_history(True)

    def _mark_detector_clear_unknown(self,detector,reason):
        if not detector:self.detector_history_known=False
        indices=[detector]if detector else [i for i in range(1,self.system.NCE.NumberOfObjects+1)if str(self._object(i).Type).startswith("Detector")]
        for index in indices:
            record=self._detector_record(index)
            record["known"]=False;record["clear_failure"]=str(reason)

    def _detector_provenance(self, index, completing=None):
        record = self._detector_record(index)
        entries = list(record["traces"])
        if completing and not any(t["task_id"] == completing["task_id"] for t in entries):
            entries.append(dict(task_id=completing["task_id"],
                model_revision=completing["context"]["model_revision"],
                configuration=completing["context"].get("configuration", 1),
                trace_options=completing["settings"]["trace_options"]))
        history = []
        for entry in entries:
            task = self.tasks.get(entry["task_id"], {})
            own = completing is not None and entry["task_id"] == completing["task_id"]
            history.append({**entry,
                "trace_options":entry.get("trace_options", task.get("settings", {}).get("trace_options")),
                "state":"succeeded" if own else task.get("state", "unknown"),
                "error":None if own else task.get("error"),
                "native_trace_complete":task.get("native_trace_complete"),
                "native_dead_ray_errors":task.get("native_dead_ray_errors"),
                "finished_at":task.get("finished_at")})
        configuration = self.system_context.get("configuration", 1)
        contexts = {(t["model_revision"], t["configuration"]) for t in history}
        current = (self.revision, configuration)
        matches = (contexts == {current}) if history else (
            record["cleared_revision"], record["cleared_configuration"]) == current
        required = {"use_polarization","split_rays","scatter_rays","ignore_errors",
                    "number_of_cores","random_seed","filter"}
        options_known = all(isinstance(t["trace_options"], dict)
                            and required <= t["trace_options"].keys() for t in history)
        mixed = len(contexts)>1 or any(t["trace_options"] != history[0]["trace_options"] for t in history[1:])
        return dict(trace_history=history, history_known=record["known"],
                    clear_failure=record.get("clear_failure"),
                    loaded_sources=copy.deepcopy(record.get("loaded_sources",[])),
                    trace_options_known=options_known, mixed_conditions=mixed,
                    model_matches_history=matches,
                    complete=record["known"] and matches and options_known and not mixed
                    and all(t["state"] == "succeeded" and t["native_trace_complete"]is not False for t in history))

    def _write_object_field(self, row, index, field, attribute, value):
        setattr(row, attribute, value)
        try:
            check_setting_readback(row, attribute, value)
        except ZemaxError as exc:
            exc.details.update(object=index, field=field, checkpoint=self.last_checkpoint)
            raise

    def _fix_nsc_cell(self,cell):
        accepted=cell.MakeSolveFixed();actual=str(cell.Solve)
        if not accepted or actual!="Fixed":raise ZemaxError("SOLVE_UPDATE_FAILED","对象单元格未解除原有求解。",requested="Fixed",actual=actual,native_return=bool(accepted))

    def _nsc_transform(self, index):
        result = self.system.NCE.GetMatrix(index, *([0.0]*12))
        if not result or not result[0] or len(result) != 13:
            raise ZemaxError("GEOMETRY_READ_FAILED", "原生对象全局矩阵读取失败。", object=index)
        values = [float(v) for v in result[1:]]
        if not all(math.isfinite(v) for v in values):
            raise ZemaxError("INVALID_RESULT_DATA", "对象全局矩阵包含非有限数值。", object=index)
        group=getattr(self,'_active_nsc_surface',None)
        return dict(rotation=[values[i:i+3] for i in (0,3,6)], translation=values[9:],
                    formula="global_position = rotation @ local_position + translation; global_direction = rotation @ local_direction",
                    frame="NSC global"if group is None else"NSC group entrance coordinates", nsc_surface=group,
                    position_unit=str(self.system.SystemData.Units.LensUnits))

    def _guard_nsc_cell(self, cell, replace=False):
        if cell is None:raise ZemaxError('CELL_NOT_WRITABLE','对象参数不存在。')
        if str(cell.Solve) == "None":
            if cell.IsReadOnly or not cell.IsActive:
                raise ZemaxError("CELL_NOT_WRITABLE","对象单元格只读或未启用。")
            return
        self._guard_cell(cell,replace)

    def _nsc_cell(self,index,name):
        row=self._object(index)
        names=self.native.enum_names(self.native.api.Editors.NCE.ObjectColumn)
        if name not in names:raise ZemaxError("INVALID_CELL","对象列名无效。",available=names)
        return row.GetObjectCell(self.native.enum(self.native.api.Editors.NCE.ObjectColumn,name))

    def _nsc_variables(self):
        variables=[]
        for i in range(1,self.system.NCE.NumberOfObjects+1):
            row=self._object(i)
            for name in self.native.enum_names(self.native.api.Editors.NCE.ObjectColumn):
                cell=row.GetObjectCell(self.native.enum(self.native.api.Editors.NCE.ObjectColumn,name))
                if cell is not None and cell.IsActive and str(cell.Solve)=="Variable":
                    variables.append(dict(scope="object",object=i,cell=name,value=self._cell_value(cell)))
        return dict(variables=variables)

    def _object_parameters(self,row,start=1,count=20):
        cells={}
        for i in range(start,min(251,start+count)):
            cell=row.GetObjectCell(self.native.enum(self.native.api.Editors.NCE.ObjectColumn,'Par'+str(i)))
            if cell is not None and cell.IsActive:
                cells[str(i)]=dict(value=self._cell_value(cell),header=str(cell.Header),writable=not bool(cell.IsReadOnly),
                    solve=str(cell.Solve),available_solves=[str(x)for x in cell.GetAvailableSolveTypes()])
        return cells

    def _require_nsc(self):
        if str(self.system.Mode)!="NonSequential"and getattr(self,'_active_nsc_surface',None)is None:raise ZemaxError("UNSUPPORTED_MODE","需要纯非序列系统。")

    def _object(self,index):
        self._require_nsc()
        if not 1<=index<=self.system.NCE.NumberOfObjects:raise ZemaxError("INDEX_OUT_OF_RANGE","非序列对象编号越界。")
        return self.system.NCE.GetObjectAt(index)

    @object_scope
    def get_nsc_objects(self,req):
        self._require_nsc();n=self.system.NCE
        end=min(n.NumberOfObjects+1,req.start+req.count);rows=[]
        for i in range(req.start,end):
            r=self._object(i)
            faces=[]
            if r.CoatScatterData.IsCoatScatterAvailable:
                for face in range(r.CoatScatterData.NumberOfFaces):
                    f=r.CoatScatterData.GetFaceData(face)
                    model=str(f.CurrentScatterModel)
                    faces.append(dict(face=face,fields=scalar_settings(f),scatter_model=model,settings=scalar_settings(getattr(f.CurrentScatterModelSettings,"_S_"+model))))
            volume=None
            if r.VolumePhysicsData.IsVolumePhysicsAvailable:
                v=r.VolumePhysicsData;model=str(v.Model)
                volume=dict(model=model,settings=scalar_settings(getattr(v.ModelSettings,"_S_"+model)))
                if model=="DLLDefinedScattering":
                    obj=v.ModelSettings._S_DLLDefinedScattering
                    volume["parameters"]=[dict(index=j,name=str(obj.GetParameterName(j)),value=float(obj.GetParameterValue(j)))for j in range(obj.NumberOfParameters)]
            spectrum=None
            if r.SourcesData.IsSourcesAvailable:
                mode=str(r.SourcesData.SourceColor)
                spectrum=dict(mode=mode,settings=scalar_settings(getattr(r.SourcesData.SourceColorSettings,"_S_"+mode)))
            rows.append(dict(object=i,type=str(r.Type),**{k:getattr(r,v) for k,v in OBJECT_FIELDS.items()},data=scalar_settings(unwrap(r.ObjectData)),sources=scalar_settings(r.SourcesData),type_settings=scalar_settings(r.TypeData),faces=faces,volume=volume,diffraction=scalar_settings(r.DiffractionData)if r.DiffractionData.IsDiffractionAvailable else None,available_types=[str(x) for x in r.AvailableObjectTypes()],file1=str(r.CurrentTypeSettings.FileName1),file2=str(r.CurrentTypeSettings.FileName2),available_files1=[str(x)for x in r.CurrentTypeSettings.GetFileNames1()]if r.CurrentTypeSettings.RequiresFile1 else [],available_files2=[str(x)for x in r.CurrentTypeSettings.GetFileNames2()]if r.CurrentTypeSettings.RequiresFile2 else []))
            rows[-1]["spectrum"]=spectrum
            rows[-1]['parameter_cells']=self._object_parameters(r,getattr(req,'parameter_start',1),getattr(req,'parameter_count',20))
            rows[-1]["global_transform"]=self._nsc_transform(i)
        return dict(rows=rows,total=int(n.NumberOfObjects),next_start=end if end<=n.NumberOfObjects else None,geometry_unit=str(self.system.SystemData.Units.LensUnits),angle_unit="degrees",available_columns=self.native.enum_names(self.native.api.Editors.NCE.ObjectColumn),available_source_spectra=self.native.enum_names(self.native.api.Editors.NCE.SourceColorMode))

    @object_scope
    def insert_nsc_objects(self,req):
        self._require_nsc();n=self.system.NCE
        if req.at>n.NumberOfObjects+1:raise ZemaxError("INDEX_OUT_OF_RANGE","插入位置越界。")
        self._mutate("nsc_insert")
        self._reset_detector_history(False)
        before=int(n.NumberOfObjects);inserted=0
        for i in range(req.count):
            failure=None
            try:
                row=n.InsertNewObjectAt(req.at+i)
            except Exception as exc:
                row=None;failure=exc
            total=int(n.NumberOfObjects)
            if failure is not None or row is None or total!=before+inserted+1:
                details=dict(requested=req.count,inserted=inserted,total=total,start=req.at,
                             failed_at=req.at+i,observed_change=total-before,
                             returned_row=row is not None)
                if failure is not None:details["native_error"]=str(failure)
                raise ZemaxError("PARTIAL_UPDATE"if total!=before else"OBJECT_INSERT_FAILED",
                                 "原生对象插入未得到有效对象行及预期数量；已停止后续插入。",**details)from failure
            inserted+=1
        return dict(total=int(n.NumberOfObjects),inserted=inserted,start=req.at)

    @object_scope
    def delete_nsc_objects(self,req):
        self._object(req.at);n=self.system.NCE
        if req.at+req.count>n.NumberOfObjects+1 or req.count==n.NumberOfObjects:raise ZemaxError("INDEX_OUT_OF_RANGE","范围越界或删除全部对象。")
        self._mutate("nsc_delete");self._reset_detector_history(False);deleted=n.RemoveObjectsAt(req.at,req.count)
        if deleted!=req.count:raise ZemaxError("PARTIAL_UPDATE","原生删除数量不符。",deleted=deleted)
        return dict(deleted=deleted,total=int(n.NumberOfObjects))

    @object_scope
    def copy_nsc_objects(self,req):
        self._object(req.start);n=self.system.NCE
        if req.start+req.count>n.NumberOfObjects+1 or req.at>n.NumberOfObjects+1:raise ZemaxError("INDEX_OUT_OF_RANGE","复制范围越界。")
        self._mutate("nsc_copy");self._reset_detector_history(False);copied=n.CopyObjects(req.start,req.count,req.at)
        if copied!=req.count:raise ZemaxError("PARTIAL_UPDATE","原生复制数量不符。",copied=copied)
        return dict(copied=copied,start=req.at,total=int(n.NumberOfObjects))

    @object_scope
    def update_nsc_objects(self,req):
        self._require_nsc();n=self.system.NCE
        graph={i:int(self._object(i).RefObject) for i in range(1,n.NumberOfObjects+1)}
        inside={i:int(self._object(i).InsideOf) for i in range(1,n.NumberOfObjects+1)}
        for p in req.changes:
            r=self._object(p.object)
            if p.object_type:self.native.enum(self.native.api.Editors.NCE.ObjectType,p.object_type)
            if p.ref_object is not None:graph[p.object]=p.ref_object
            if p.inside_of is not None:inside[p.object]=p.inside_of
            for key,attr in OBJECT_FIELDS.items():
                if getattr(p,key) is not None:
                    cell=getattr(r,attr+"Cell")
                    if p.object_type and p.object_type!=str(r.Type):
                        if cell.IsActive and str(cell.Solve)not in {"Fixed","Variable","None"}and not p.replace_solves:
                            raise ZemaxError("SOLVE_PROTECTED","改变对象类型会影响原有求解关系。")
                    else:self._guard_nsc_cell(cell,p.replace_solves)
            if p.object_type and not p.replace_solves:
                for col in range(1,251):
                    cell=r.GetObjectCell(self.native.enum(self.native.api.Editors.NCE.ObjectColumn,"Par"+str(col)))
                    if cell is not None and cell.IsActive and str(cell.Solve) not in {"Fixed","Variable","None"}:raise ZemaxError("SOLVE_PROTECTED","改变对象类型影响现有参数求解。")
            if p.data:
                for col in range(1,251):
                    cell=r.GetObjectCell(self.native.enum(self.native.api.Editors.NCE.ObjectColumn,"Par"+str(col)))
                    if cell is not None and cell.IsActive and str(cell.Solve) not in {"Fixed","Variable","None"}:
                        raise ZemaxError("SOLVE_PROTECTED","类型参数存在拾取；先用原生设计明确解除后再写入 data。")
            if not p.object_type or p.object_type==str(r.Type):
                for index in p.parameters:
                    cell=r.GetObjectCell(self.native.enum(self.native.api.Editors.NCE.ObjectColumn,'Par'+str(index)))
                    self._guard_nsc_cell(cell,p.replace_solves)
        for relation in (graph,inside):
            for start in relation:
                seen=set();i=start
                while i:
                    if i in seen or i not in relation:raise ZemaxError("INVALID_REFERENCE","对象参考/包含关系循环或编号越界。")
                    seen.add(i);i=relation[i]
        self._mutate("nsc_objects")
        from .nsc_state import verify_patch,failure
        completed=[];prepared=[]
        # Detach replaced edges before reversing dependencies in the final graph.
        for p in req.changes:
            try:
                row=self._object(p.object)
                for key,attr in (("ref_object","RefObject"),("inside_of","InsideOf")):
                    value=getattr(p,key)
                    if value is not None and int(getattr(row,attr))!=value:
                        cell=getattr(row,attr+"Cell")
                        if str(cell.Solve)not in {"Fixed","Variable","None"}:self._fix_nsc_cell(cell)
                        self._write_object_field(row,p.object,key,attr,0)
                prepared.append(p.object)
            except Exception as exc:
                error=failure(self,exc,p.object,completed,prepared,'detach_references')
                if error is exc:raise
                raise error from exc
        for p in req.changes:
            try:
                r=self._object(p.object)
                if p.object_type or p.file1 is not None or p.file2 is not None:
                    kind=self.native.enum(self.native.api.Editors.NCE.ObjectType,p.object_type or str(r.Type))
                    setting=r.GetObjectTypeSettings(kind)
                    for key,attr,files in (("file1","FileName1","GetFileNames1"),("file2","FileName2","GetFileNames2")):
                        value=getattr(p,key)
                        if value is not None:
                            if value not in [str(x) for x in getattr(setting,files)()]:raise ZemaxError("INVALID_RESOURCE","对象文件不在本机列表中。",field=key)
                            checked_setting(self.native,setting,attr,value)
                    self._reset_detector_history(False)
                    if not r.ChangeType(setting):raise ZemaxError("OBJECT_UPDATE_FAILED","原生对象类型设置失败。")
                    check_setting_readback(r,"Type",p.object_type or str(kind))
                    for key,attr in (("file1","FileName1"),("file2","FileName2")):
                        if getattr(p,key) is not None:check_setting_readback(r.CurrentTypeSettings,attr,getattr(p,key))
                for key,attr in OBJECT_FIELDS.items():
                    value=getattr(p,key)
                    if value is not None:
                        cell=getattr(r,attr+"Cell")
                        self._guard_nsc_cell(cell,p.replace_solves)
                        if str(cell.Solve) not in {"Fixed","Variable","None"}:
                            self._fix_nsc_cell(cell)
                        self._write_object_field(r,p.object,key,attr,value)
                for patch,obj in ((p.data,unwrap(r.ObjectData)),(p.sources,r.SourcesData),(p.type_settings,r.TypeData)):
                    for key,value in patch.items():
                        try:checked_setting(self.native,obj,key,value)
                        except ZemaxError as exc:
                            exc.details.update(object=p.object,checkpoint=self.last_checkpoint)
                            raise
                for index,value in p.parameters.items():
                    cell=r.GetObjectCell(self.native.enum(self.native.api.Editors.NCE.ObjectColumn,'Par'+str(index)))
                    self._guard_nsc_cell(cell,p.replace_solves)
                    if str(cell.Solve)not in ('Fixed','Variable','None'):self._fix_nsc_cell(cell)
                    self._write_cell(cell,value)
                    from .detectors import check_setting_value
                    check_setting_value('parameter_'+str(index),value,self._cell_value(cell))
                for face in p.faces:
                    if not r.CoatScatterData.IsCoatScatterAvailable or face.face>=r.CoatScatterData.NumberOfFaces:raise ZemaxError("INDEX_OUT_OF_RANGE","对象光学面编号越界。")
                    f=r.CoatScatterData.GetFaceData(face.face)
                    if not f.UseCustomSettings():raise ZemaxError("OBJECT_UPDATE_FAILED","无法设置自定义光学面属性。")
                    if face.coating is not None:
                        if face.coating not in [str(x)for x in f.GetAvailableCoatings()]:raise ZemaxError("INVALID_RESOURCE","镀膜不可用。")
                        checked_setting(self.native,f,"Coating",face.coating)
                    if face.scatter_model:
                        setting=f.CreateScatterModelSettings(self.native.enum(self.native.api.Editors.NCE.ObjectScatteringTypes,face.scatter_model))
                        obj=getattr(setting,"_S_"+face.scatter_model)
                        for key,value in face.settings.items():checked_setting(self.native,obj,key,value)
                        if not f.ChangeScatterModelSettings(setting):raise ZemaxError("OBJECT_UPDATE_FAILED","散射模型设置失败。")
                        check_setting_readback(f,"CurrentScatterModel",face.scatter_model)
                        applied=getattr(f.CurrentScatterModelSettings,"_S_"+face.scatter_model)
                        for key,value in face.settings.items():check_setting_readback(applied,key,value)
                    elif face.settings:raise ZemaxError("INVALID_ARGUMENT","散射参数需要 scatter_model。")
                    if face.number_of_rays is not None:checked_setting(self.native,f,"NumberOfRays",face.number_of_rays)
                if p.volume:
                    v=r.VolumePhysicsData
                    if not v.IsVolumePhysicsAvailable:raise ZemaxError("UNSUPPORTED_SETTING","此对象无体物理设置。")
                    checked_setting(self.native,v,"Model",p.volume.model)
                    obj=getattr(v.ModelSettings,"_S_"+p.volume.model)
                    for key,value in p.volume.settings.items():checked_setting(self.native,obj,key,value)
                    for index,value in p.volume.parameters.items():
                        if index>=obj.NumberOfParameters:raise ZemaxError("INDEX_OUT_OF_RANGE","体散射DLL参数越界。",parameter=index)
                        if not obj.SetParameterValue(index,value):raise ZemaxError("SETTING_REJECTED","体散射DLL参数写入失败。",parameter=index)
                        from .detectors import check_setting_value
                        check_setting_value("volume_parameter_"+str(index),value,obj.GetParameterValue(index))
                if p.spectrum:
                    if not r.SourcesData.IsSourcesAvailable:raise ZemaxError("UNSUPPORTED_SETTING","此对象无光源设置。")
                    checked_setting(self.native,r.SourcesData,"SourceColor",p.spectrum.mode)
                    obj=getattr(r.SourcesData.SourceColorSettings,"_S_"+p.spectrum.mode)
                    for key,value in p.spectrum.settings.items():checked_setting(self.native,obj,key,value)
                if p.diffraction:
                    if not r.DiffractionData.IsDiffractionAvailable:raise ZemaxError("UNSUPPORTED_SETTING","此对象无衍射设置。")
                    for key,value in p.diffraction.items():checked_setting(self.native,r.DiffractionData,key,value)
                completed.append(p.object)
            except Exception as exc:
                error=failure(self,exc,p.object,completed,prepared,'write_properties')
                if error is exc:raise
                raise error from exc
        for p in req.changes:
            try:verify_patch(self,self._object(p.object),p,OBJECT_FIELDS)
            except Exception as exc:
                error=failure(self,exc,p.object,completed,prepared,'final_readback')
                if error is exc:raise
                raise error from exc
        return self.get_nsc_objects(type("Range",(),{"start":1,"count":200})())

    def clear_detectors(self,req):
        self._require_nsc()
        if req.detector:self._object(req.detector)
        tool=self.system.Tools.OpenNSCRayTrace()
        try:
            try:status=str(tool.ClearDetectors(0) if req.detector==0 else tool.ClearDetectorObject(req.detector))
            except Exception as exc:
                self._mark_detector_clear_unknown(req.detector,exc)
                raise ZemaxError("DETECTOR_CLEAR_FAILED","探测器清空结果未确认。",reason=str(exc))from exc
            if status!="Success":
                self._mark_detector_clear_unknown(req.detector,status)
                raise ZemaxError("DETECTOR_CLEAR_FAILED","原生探测器清空失败。",status=status)
            self._clear_detector_records(req.detector)
            return dict(cleared="all" if req.detector==0 else [req.detector])
        finally:self._release_owned(tool)

    def _detector_file_extension(self, index):
        kind=str(self._object(index).Type)
        extensions={"DetectorRectangle":".ddr","DetectorPolar":".ddp",
                    "DetectorColor":".ddc","DetectorVolume":".ddv"}
        if kind not in extensions:
            raise ZemaxError("UNSUPPORTED_DETECTOR","本机原生保存/加载支持 Rectangle、Polar、Color、Volume。",detector_type=kind)
        return kind,extensions[kind]

    def save_detector_data(self,req):
        self._require_work()
        kind,extension=self._detector_file_extension(req.detector)
        path=output_path(req.path,{extension},req.overwrite)
        path.parent.mkdir(parents=True,exist_ok=True)
        if not self.system.NCE.SaveDetector(req.detector,str(path)) or not path.is_file():
            raise ZemaxError("DETECTOR_SAVE_FAILED","原生探测器数据未保存。",detector=req.detector,path=str(path))
        return dict(detector=req.detector,detector_type=kind,path=str(path),
                    **self._detector_provenance(req.detector),artifacts=[dict(kind="detector_data",path=str(path))])

    def load_detector_data(self,req):
        self._require_work()
        kind,extension=self._detector_file_extension(req.detector)
        path=input_path(req.path,{extension})
        backup=self.directory/("detector_before_load_"+uuid.uuid4().hex+extension)
        if not self.system.NCE.SaveDetector(req.detector,str(backup)) or not backup.is_file():
            raise ZemaxError("CHECKPOINT_FAILED","加载前无法保存当前探测器数据。",detector=req.detector)
        previous=copy.deepcopy(self._detector_record(req.detector))
        record=copy.deepcopy(previous) if req.mode=="accumulate" else dict(
            traces=[],cleared_revision=self.revision,cleared_configuration=self.system_context.get("configuration",1))
        record["known"]=False
        record.setdefault("loaded_sources",[]).append(dict(path=str(path),mode=req.mode,
            model_revision=self.revision,configuration=self.system_context.get("configuration",1),
            history_known=False))
        self.detector_records[req.detector]=record
        try:
            if not self.system.NCE.LoadDetector(req.detector,str(path),req.mode=="accumulate"):
                raise ZemaxError("DETECTOR_LOAD_FAILED","原生探测器数据加载失败。")
        except Exception as exc:
            try:
                if not self.system.NCE.LoadDetector(req.detector,str(backup),False):
                    raise RuntimeError("原生恢复返回 false")
                self.detector_records[req.detector]=previous
            except Exception as restore:
                self.requires_reconnect=True
                raise ZemaxError("RESTORE_FAILED","探测器数据恢复失败，需要重新连接。",
                    detector=req.detector,checkpoint=str(backup),cause=str(exc),restoration_error=str(restore),
                    detector_data_changes_possible=True) from exc
            raise ZemaxError("DETECTOR_LOAD_FAILED",str(exc),detector=req.detector,
                checkpoint=str(backup),restored=True,detector_data_changes_possible=False) from exc
        return dict(detector=req.detector,detector_type=kind,path=str(path),mode=req.mode,
                    checkpoint=str(backup),**self._detector_provenance(req.detector))

    def run_nsc_ray_trace(self,req):
        self._require_nsc();self._require_work()
        from .hpc import prepare_hpc, open_execution_tool, check_tool_values, close_failed_setup
        hpc=prepare_hpc(self,getattr(req,'hpc',None))
        model_rows=[]
        try:
            for start in range(1,self.system.NCE.NumberOfObjects+1,200):
                model_rows.extend(self.get_nsc_objects(type("Range",(),dict(start=start,count=200))())["rows"])
            for row in model_rows:
                for key in ("available_types","available_files1","available_files2"):row.pop(key,None)
            optical_model=dict(state="captured",objects=model_rows)
        except Exception as exc:
            optical_model=dict(state="unavailable",reason=str(exc),captured_objects=model_rows)
        try:
            dependency_rows=[];start=0
            while start is not None:
                page=self.get_external_dependencies(type("Range",(),dict(start=start,count=200))())
                dependency_rows.extend(page["rows"]);start=page["next_start"]
            optical_model["external_dependencies"]=dict(state="captured",rows=dependency_rows)
        except Exception as exc:optical_model["external_dependencies"]=dict(state="unavailable",reason=str(exc))
        if self.requires_reconnect:raise ZemaxError("RECONNECT_REQUIRED","快照资源释放未确认，停止追迹。",optical_model_snapshot=optical_model)
        from .data import clean
        model_snapshot=self.directory/("nsc_model_snapshot_"+uuid.uuid4().hex+".json")
        model_snapshot.write_text(json.dumps(clean(optical_model),ensure_ascii=False,allow_nan=False),encoding="utf-8")
        zrd=output_path(req.save_zrd,{".zrd"}) if req.save_zrd else None
        if zrd:zrd.parent.mkdir(parents=True,exist_ok=True)
        tool=open_execution_tool(self,'OpenNSCRayTrace',hpc)
        def clear_requested_detectors():
            if req.detector_policy=="clear":
                try:status=str(tool.ClearDetectors(0))
                except Exception as exc:
                    self._mark_detector_clear_unknown(0,exc)
                    raise ZemaxError("DETECTOR_CLEAR_FAILED","追迹前清空结果未确认。",reason=str(exc))from exc
                if status!="Success":
                    self._mark_detector_clear_unknown(0,status)
                    raise ZemaxError("DETECTOR_CLEAR_FAILED","清空失败。",status=status)
                self._clear_detector_records()
        try:
            if hpc is None:clear_requested_detectors()
            tool.UsePolarization=req.use_polarization;tool.SplitNSCRays=req.split_rays;tool.ScatterNSCRays=req.scatter_rays;tool.IgnoreErrors=req.ignore_errors;tool.NumberOfCores=req.number_of_cores
            if req.random_seed is not None:tool.SetRandomSeed(req.random_seed)
            else:tool.ResetRandomSeed()
            tool.SaveRays=bool(zrd)
            native_zrd=None
            requested_native_zrd=None
            if zrd:
                requested_native_zrd="mcp_"+uuid.uuid4().hex+".zrd"
                tool.SaveRaysFile=requested_native_zrd
                native_zrd=Path(str(self.system.SystemFile)).parent/str(tool.SaveRaysFile)
            tool.Filter=req.filter
            actual=scalar_settings(tool);actual.update(detector_policy=req.detector_policy,random_seed=req.random_seed)
            actual["optical_model_snapshot"]=dict(state=optical_model["state"],object_count=len(model_rows),path=str(model_snapshot))
            actual["trace_options"] = dict(
                use_polarization=bool(tool.UsePolarization), split_rays=bool(tool.SplitNSCRays),
                scatter_rays=bool(tool.ScatterNSCRays), ignore_errors=bool(tool.IgnoreErrors),
                number_of_cores=int(tool.NumberOfCores), random_seed=req.random_seed, filter=str(tool.Filter))
            if hpc is not None:
                values=dict(UsePolarization=req.use_polarization,SplitNSCRays=req.split_rays,ScatterNSCRays=req.scatter_rays,
                    IgnoreErrors=req.ignore_errors,NumberOfCores=req.number_of_cores,SaveRays=bool(zrd),Filter=req.filter)
                if zrd:values['SaveRaysFile']=requested_native_zrd
                check_tool_values(self,tool,values)
                actual['hpc']=hpc['actual'];actual['trace_options']['hpc']=hpc['actual']
                clear_requested_detectors()
        except Exception as exc:close_failed_setup(self,tool,exc);raise
        def collect(task):
            if not tool.Succeeded:raise ZemaxError("TASK_FAILED",str(tool.ErrorMessage))
            error_energy=float(tool.DeadRayErrors)
            if not math.isfinite(error_energy) or error_energy<0:
                raise ZemaxError("INVALID_RESULT_DATA","原生错误光线能量无有效数值。",dead_ray_errors=str(error_energy))
            task["native_dead_ray_errors"]=error_energy
            task["native_trace_complete"]=error_energy==0
            if error_energy>0 and not req.ignore_errors:
                raise ZemaxError("NSC_TRACE_ERRORS","原生追迹出现错误光线；Succeeded不代表请求光线均已完成。",
                                 dead_ray_errors=error_energy,native_succeeded=True,
                                 native_zrd=str(native_zrd)if native_zrd and native_zrd.is_file()else None)
            result=dict(total_ray_energy=float(tool.GetTotalRayEnergy()),dead_ray_errors=error_energy,dead_ray_threshold=float(tool.DeadRayThreshold),complete=task["native_trace_complete"],
                optical_model_snapshot=optical_model,artifacts=[dict(kind="model_settings_json",path=str(model_snapshot))])
            if hpc is not None:result['hpc']=hpc['actual']
            if not self._close_task_native(task):raise ZemaxError("CLEANUP_FAILED","追迹资源释放失败。")
            # Save scalar detector power with the trace for offline reports.
            # This is accumulated detector state, not energy attributed only to this Run.
            power_rows=[]
            for index in detectors:
                detector_type=str(self._object(index).Type)
                if detector_type=="DetectorPolar":
                    status,value=self.system.NCE.GetPolarDetectorData(index,0,
                        self.native.enum(self.native.api.Editors.NCE.PolarDetectorDataType,"Power"),0.0)
                elif detector_type=="DetectorRectangle":
                    status,value=self.system.NCE.GetDetectorData(index,0,0,0.0)
                elif detector_type=="DetectorColor":
                    status,value=self.system.NCE.GetColorDetectorData(index,0,False,1,0,0.,0.)
                elif detector_type=="DetectorSurface":
                    status,value=self.system.NCE.GetDetectorData(index,0,0,0.)
                else:continue
                if not status or not math.isfinite(float(value)):
                    raise ZemaxError("DETECTOR_READ_FAILED","追迹后的探测器总功率读取失败。",detector=index)
                # Published only if collection and task persistence succeed.
                provenance=self._detector_provenance(index, completing=task)
                references=provenance.pop("trace_history")
                units=self.system.SystemData.Units
                descriptor=detector_metadata("flux",None,str(units.SourceUnits),str(units.SourceUnitPrefix),
                    str(units.AnalysisUnits),str(units.AnalysisUnitPrefix),detector_type="DetectorPolar" if detector_type=="DetectorColor" else detector_type)
                label=(descriptor["value_unit_prefix"]+" "if descriptor["value_unit_prefix"]!="None"else"")+descriptor["value_unit"]
                power_rows.append(dict(index=len(power_rows),value=index,state="measured",
                    detector=index,detector_type=detector_type,
                    metrics=[dict(key="accumulated_detector_flux",value=float(value),
                        unit=label,
                        unit_prefix=descriptor["value_unit_prefix"])],
                    accumulated_total_flux=float(value),
                    value_unit=descriptor["value_unit"],
                    value_unit_prefix=descriptor["value_unit_prefix"],
                    trace_conditions=references, **provenance))
            result["rows"]=power_rows
            result["summary"]=dict(quantity="accumulated detector flux or energy at end of native trace",
                detector_policy=req.detector_policy,
                supported_detector_types=["DetectorRectangle","DetectorPolar","DetectorColor","DetectorSurface"],
                excluded_detector_types={"DetectorVolume":"incident voxel flux repeats per path; no unique-input-power total is inferred"},
                completeness_rule="use the final task state and trace_conditions; values include explicit prior accumulation")
            if zrd:
                if not native_zrd.is_file():raise ZemaxError("EXPORT_FAILED","原生工具未输出 ZRD。",native_path=str(native_zrd))
                native_zrd.rename(zrd)
                result["artifacts"].append(dict(kind="zrd",path=str(zrd)))
            return result
        detectors = [i for i in range(1, self.system.NCE.NumberOfObjects+1)
                     if str(self._object(i).Type).startswith("Detector")]
        # Snapshot before Run: failure and partial propagation must also remain attributable.
        for i in detectors:self._detector_record(i)
        task = None
        try:
            task = self._start_task("nsc_ray_trace",tool,actual,collector=collect)
            return task
        except ZemaxError as exc:
            if exc.details.get("task_id"):task = dict(task_id=exc.details["task_id"])
            raise
        finally:
            if task:
                entry = dict(task_id=task["task_id"], model_revision=self.revision,
                             configuration=self.system_context.get("configuration",1),
                             trace_options=dict(actual["trace_options"]))
                self.detector_history.append(task["task_id"])
                for i in detectors:self._detector_record(i)["traces"].append(dict(entry))


    def get_detector_data(self,req):
        r=self._object(req.detector);detector_type=str(r.Type);n=self.system.NCE
        if getattr(req,'read_mode','full')=='region':
            from .detector_regions import read_region
            return read_region(self,req,r)
        if req.include_geometry and detector_type!='DetectorSurface':
            raise ZemaxError('UNSUPPORTED_DETECTOR_GEOMETRY','三角面几何仅适用于DetectorSurface。',detector_type=detector_type)
        if detector_type in {"DetectorColor","DetectorVolume","DetectorSurface"}:
            from .detector_readers import read_special
            return read_special(self,req,r)
        if req.color_channel or req.angle_space or req.z_start or req.depth!=1 or req.kind in {"spectral","absorbed_flux","absorbed_density"}:
            raise ZemaxError("UNSUPPORTED_DETECTOR_DATA","此选项不适用于当前探测器。",detector_type=detector_type)
        coordinates={}
        if detector_type=="DetectorPolar":
            if req.kind not in {"flux","intensity"}:
                raise ZemaxError("UNSUPPORTED_DETECTOR_DATA","Polar 首批支持 flux/intensity。",detector_type=detector_type,kind=req.kind)
            data=unwrap(r.ObjectData)
            np,na=int(data.NumberPPixels),int(data.NumberAPixels)
            coordinates=polar_coordinates(np,na,float(data.MaxAngle))
            native_type={"flux":"Power","intensity":"PowerSolidAngle"}[req.kind]
            array=n.GetAllPolarDetectorDataSafe(req.detector,self.native.enum(self.native.api.Editors.NCE.PolarDetectorDataType,native_type))
            expected=(na,np)
        elif detector_type=="DetectorRectangle":
            if req.kind=="coherent":
                if not req.coherent_type:raise ZemaxError("INVALID_ARGUMENT","相干数据需要 coherent_type。")
                native_type=req.coherent_type
                array=n.GetAllCoherentDataSafe(req.detector,self.native.enum(self.native.api.Editors.NCE.DetectorDataType,req.coherent_type))
            else:
                native_type={"flux":0,"irradiance":1,"intensity":2}[req.kind]
                array=n.GetAllDetectorDataSafe(req.detector,native_type)
            data=unwrap(r.ObjectData) if hasattr(r,"ObjectData") else None
            expected=(int(data.NumberYPixels),int(data.NumberXPixels)) if data is not None else None
            coordinates=dict(coordinate_system="native detector spatial or angular matrix",
                             definition="row 0 follows native detector ordering; no image flip applied")
        else:
            raise ZemaxError("UNSUPPORTED_DETECTOR","数值适配 DetectorRectangle、DetectorPolar、DetectorColor、DetectorVolume 和 DetectorSurface；其他类型须使用专用数据路径。",detector_type=detector_type)
        if array is None or getattr(array,"Rank",None)!=2:
            raise ZemaxError("INVALID_DETECTOR_DATA","原生探测器未返回二维矩阵。",detector=req.detector)
        values=dotnet_array(array);ny=len(values);nx=len(values[0])if ny else 0
        if not nx or not ny or any(len(row)!=nx for row in values) or expected and expected!=(ny,nx):
            raise ZemaxError("INVALID_DETECTOR_DATA","原生矩阵为空或维度与探测器设置不符。",expected=expected,actual=[ny,nx])
        if req.x_start>=nx or req.y_start>=ny:
            raise ZemaxError("INDEX_OUT_OF_RANGE","探测器区域起点越界。",nx=nx,ny=ny)
        xend=min(nx,req.x_start+req.width);yend=min(ny,req.y_start+req.height)
        invalid=sum(not math.isfinite(v) for row in values for v in row)
        values=[[v if math.isfinite(v) else None for v in row] for row in values]
        units=self.system.SystemData.Units
        source_units=str(units.SourceUnits);prefix=str(units.SourceUnitPrefix)
        metadata=detector_metadata(req.kind,req.coherent_type,source_units,prefix,
                                   str(units.AnalysisUnits),str(units.AnalysisUnitPrefix),detector_type=detector_type)
        full=dict(detector=req.detector,detector_type=detector_type,kind=req.kind,
                  coherent_type=req.coherent_type,native_data_type=native_type,nx=nx,ny=ny,
                  values=values,context=self.context(),invalid_count=invalid,
                  array_order="rows azimuth, columns polar"if detector_type=="DetectorPolar"else"native matrix dimensions; row 0 follows native detector ordering",
                  units=str(units.AnalysisUnits),source_units=source_units,source_unit_prefix=prefix,
                  analysis_unit_prefix=str(units.AnalysisUnitPrefix),
                  unit_interpretation="value_unit/value_unit_prefix describe this quantity; units retains native AnalysisUnits.",
                  **coordinates,**metadata,**self._detector_provenance(req.detector))
        if detector_type=="DetectorRectangle"and hasattr(r,"TypeData"):
            full["coherence"]=dict(normalize_coherent_power=bool(r.TypeData.NormalizeCoherentPower),
                                   polarization_flag=int(data.Polarization) if data is not None and hasattr(data,"Polarization") else None,
                                   use_pixel_interpolation=bool(r.TypeData.UsePixelInterpolation),
                                   interpretation="OpticStudio NSC coherent ray model; Power applies the detector normalization",
                                   real_imaginary="native Real/Imaginary display components; retain pixel-count and normalization conditions when relating these values to coherent Power or raw field sums",
                                   amplitude="native DetectorDataType.Amplitude display value; the validated 1x1 case differs from unnormalized S_amp; retain pixel-count and normalization conditions",
                                   polarization_scope="Polarization=0 sums scalar ray intensity and geometric phase, including orthogonal-Jones inputs; flags 1/2/3 select local Ex/Ey/Ez and component phase. Native Power is not an automatic vector-field sum.",
                                   polarization_definition_source="OpticStudio 2024 R2 Detector Rectangle parameter 16 and About parameter Polarization flag; manual lines 14132 and 14229-14237",
                                   phase_convention="negative optical-path/initial phase; phase is undefined at destructive cancellation")
        path=self.directory/("detector_"+uuid.uuid4().hex+".json")
        path.write_text(json.dumps(full,ensure_ascii=False,allow_nan=False),encoding="utf-8")
        return {**full,"values":[row[req.x_start:xend] for row in values[req.y_start:yend]],
                "x_start":req.x_start,"y_start":req.y_start,"next_x":xend if xend<nx else None,
                "next_y":yend if yend<ny else None,
                "total_flux":sum(v for row in values for v in row if v is not None)if req.kind=="flux"else None,
                "artifacts":[dict(kind="json",path=str(path))]}

    def read_zrd(self,req):
        self._require_nsc();path=input_path(req.path,{".zrd"})
        def flow(task):
            tool=self.system.Tools.OpenRayDatabaseReader()
            task.setdefault('payload',{})['native_closed']=False
            try:
                tool.ZRDFile=str(path)
                tool.Filter=req.filter
                check_setting_readback(tool,"Filter",req.filter)
                actual_filter=str(tool.Filter)
                if not tool.RunAndWaitForCompletion() or not tool.Succeeded:raise ZemaxError("ZRD_READ_FAILED",str(tool.ErrorMessage))
                data=tool.GetResults();ray_index=-1;count=0;next_read=None;work=0
                while data.ReadNextRay():
                    ray_index+=1
                    work+=1
                    if work>=256:self._cancel_boundary(task);yield;work=0
                    if ray_index<req.start_ray:continue
                    segment=-1
                    while data.ReadNextRaySegment():
                        segment+=1
                        work+=1
                        if work>=256:self._cancel_boundary(task);yield;work=0
                        if ray_index==req.start_ray and segment<req.start_segment:continue
                        if count>=req.max_segments:
                            next_read=dict(start_ray=ray_index,start_segment=segment);break
                        row=dict(ray_index=ray_index,segment_index=segment)
                        for k in ("RayNumber","WaveIndex","WlUM","NumSegments","SegmentLevel","SegmentParent","HitObject","HitFace","InsideOf","X","Y","Z","L","M","N","Intensity","PathLength","OpticalPathW","OpticalPathLU","RayError","SegTerminated","SegReflected","SegTransmitted","SegScattered"):
                            row[k]=getattr(data,k)
                        for k in ("SegBulkScattered","SegDiffracted","XNorm","YNorm","ZNorm","Index","HasOrderX","HasOrderY"):
                            row[k]=getattr(data,k,None)
                        for axis in ("X","Y"):row["Order"+axis]=getattr(data,"Order"+axis,None)if row["HasOrder"+axis]else None
                        task["rows"].append(row);count+=1
                    if next_read:break
                    self._cancel_boundary(task)
                task["summary"]=dict(source=str(path),filter=req.filter,next_read=next_read,truncated=next_read is not None,segments=count,coordinate_frame="NSC global",position_unit=str(self.system.SystemData.Units.LensUnits),wavelength_scope="WlUM is the native ray-header wavelength; wavelength conversion is not inferred for individual segments")
                task["summary"].update(actual_filter=actual_filter,filter_scope="native ray/path selection; all returned path segments retain their native meaning")
                if re.search(r"\bX_WAVERANGE\s*\(",req.filter,re.IGNORECASE):
                    task["summary"]["wavelength_filter_validation"]=wavelength_filter_validation()
            finally:
                self._release_owned(tool)
                task['payload']['native_closed']=True
        # Composite execution is also valid for a non-sequential model.
        return self._composite("zrd_read",req.model_dump(),flow,require_sequential=False)

    def run_zrd_replay(self,req):
        self._require_nsc();self._object(req.detector)
        path=input_path(req.path,{".zrd"})
        import shutil
        working=Path(str(self.system.SystemFile)).parent/("replay_"+uuid.uuid4().hex+".zrd")
        shutil.copyfile(path,working)
        self.system.UpdateFileLists()
        tool=self.system.Analyses.New_Analysis(self.native.api.Analysis.AnalysisIDM.DetectorViewer)
        try:
            s=unwrap(tool.GetSettings());s.Detector.SetDetectorNumber(req.detector)
            s.RayDatabaseFilename=working.name;s.Filter=req.filter
            check_setting_readback(s,"RayDatabaseFilename",working.name)
            check_setting_readback(s,"Filter",req.filter)
            if int(s.Detector.GetDetectorNumber())!=req.detector:
                raise ZemaxError("SETTING_REJECTED","原生回放未采用探测器编号。",requested=req.detector,actual=int(s.Detector.GetDetectorNumber()))
            self.native.set_enum(s,"DataType",req.data_type);self.native.set_enum(s,"ShowAs","FalseColor")
            from .zrd_replay import check_replay_enum
            check_replay_enum(self.native,s,"DataType",req.data_type)
            check_replay_enum(self.native,s,"ShowAs","FalseColor")
            actual=scalar_settings(s);actual.update(source_zrd=str(path),working_zrd=str(working),result_source="Detector Viewer ZRD replay; separate from current detector accumulation")
            actual["requested_data_type"]=req.data_type
        except Exception:self._release_owned(tool);raise
        def collect(task):
            from .zrd_replay import replay_text_summary
            result=self._collect_general_analysis(task)
            result["native_replay_summary"]=replay_text_summary(result["native_preamble"])
            result["native_replay_summary"].update(source_zrd=str(path),filter=str(s.Filter),detector=req.detector)
            if re.search(r"\bX_WAVERANGE\s*\(",req.filter,re.IGNORECASE):
                result["wavelength_filter_validation"]=wavelength_filter_validation()
            return result
        return self._start_task("zrd_replay",tool,actual,analysis=True,collector=collect)
