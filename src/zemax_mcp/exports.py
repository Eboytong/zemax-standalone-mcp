from .files import output_path
from .analyses import scalar_settings
from .errors import ZemaxError
from .data import dotnet_array
import json,math,subprocess,sys,uuid,os

CAD_EXTENSIONS={"STEP":{".step",".stp"},"IGES":{".iges",".igs"},"SAT":{".sat"},"STL":{".stl"},"SAB":{".sab"},"OBJ":{".obj"},"VRML":{".wrl"},"VisualizationJSON":{".json"}}
CAD_EXTENSIONS.update({name:{extension}for name,extension in dict(ASAT=".asat",ASAB=".asab",MODEL=".model",CATPART=".catpart",CATPRODUCT=".catproduct",XCGM=".xcgm",ZMO=".zmo",XT=".x_t",XB=".x_b",PRC=".prc",JT=".jt",N3MF=".3mf",U3D=".u3d").items()})

def acis_metadata(path,format,requested_version=None):
    """Read the native SAT/SAB format declaration after its writer has closed."""
    if format not in {'SAT','SAB'}:return None
    import struct
    with path.open('rb')as stream:prefix=stream.read(256)
    try:
        if format=='SAT':code=int(prefix.split(None,1)[0])
        else:
            magic=b'ACIS BinaryFile'
            if not prefix.startswith(magic):raise ValueError('missing ACIS binary signature')
            code=struct.unpack_from('<I',prefix,len(magic))[0]
        if not 100<=code<=100000:raise ValueError('invalid version code')
    except (ValueError,IndexError,struct.error)as exc:
        raise ZemaxError('INVALID_RESULT_DATA','原生ACIS文件头无法读取版本。',path=str(path),format=format)from exc
    actual=dict(format=format,version_code=code,major=code//100,source='native ACIS file header')
    if requested_version not in {None,'Current'} and code!=int(requested_version[1:])*100:
        raise ZemaxError('SETTING_REJECTED','ACIS实际文件版本未采用显式请求。',setting='file_version',requested=requested_version,actual=actual,path=str(path))
    return actual


def iges_layer_metadata(path,requested_levels):
    """Read direct IGES DE field5 after writer close for an explicit lens-only layer request."""
    levels=set();pointers=set();records=0
    try:
        with path.open('r',encoding='ascii') as stream:
            for line in stream:
                if len(line)<73 or line[72]!='D':continue
                sequence=int(line[73:80])
                if sequence%2==0:continue
                records+=1
                field=line[32:40].strip();level=int(field) if field else 0
                if level<0:pointers.add(-level)
                else:levels.add(level)
    except (ValueError,UnicodeError) as exc:
        raise ZemaxError('INVALID_RESULT_DATA','IGES目录层号无法读取。',path=str(path),native_error=str(exc)) from exc
    actual=dict(source='native IGES directory entry field5, columns33–40 of first DE record',
        directory_entries=records,levels=sorted(levels),indirect_level_pointers=sorted(pointers),
        requested_levels=sorted(requested_levels),scope='explicit sequential lens layers with no exported rays')
    if records==0:raise ZemaxError('INVALID_RESULT_DATA','IGES未提供目录层号记录。',path=str(path),actual=actual)
    if pointers:
        raise ZemaxError('SETTING_UNAVAILABLE','IGES使用间接层定义，当前未能确认请求层号采用。',setting='lens_layer',path=str(path),actual=actual)
    meaningful=levels if requested_levels=={0} else levels-{0}
    if meaningful!=requested_levels:
        raise ZemaxError('SETTING_REJECTED','IGES实际层号未采用请求。',setting='lens_layer',
            requested=sorted(requested_levels),actual=actual,path=str(path))
    actual['adopted']=True
    return actual


class ExportsMixin:
    def export_point_cloud(self,req):
        from .point_cloud import export
        return export(self,req)

    def run_speos_export(self,req):
        from .speos import run_speos_export
        return run_speos_export(self,req.request)

    def export_analysis_image(self,req):
        from .plotting import export_image
        result=self._full_result(req.task_id)
        path=output_path(req.path,{".png"},req.overwrite)
        if req.source=="native":return dict(task_id=req.task_id,path=str(path),**export_image(result,req,path))
        packet=self.directory/("image_request_"+uuid.uuid4().hex+".json")
        response=packet.with_name(packet.stem+"_result.json")
        packet.write_text(json.dumps(dict(request=req.model_dump(),result=result),ensure_ascii=False,allow_nan=False),encoding="utf-8")
        log=packet.with_suffix(".log")
        try:
            with log.open("w",encoding="utf-8")as stream:
                child=subprocess.run([sys.executable,"-B","-m","zemax_mcp.image_worker",str(packet),str(response)],
                    stdout=stream,stderr=stream,stdin=subprocess.DEVNULL,cwd=self.directory,
                    env={**os.environ,"PYTHONUTF8":"1"},
                    timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        except subprocess.TimeoutExpired as exc:raise ZemaxError("IMAGE_EXPORT_TIMEOUT","离线绘图进程超过45秒。",log=str(log)) from exc
        if child.returncode or not response.is_file():raise ZemaxError("IMAGE_EXPORT_FAILED","离线图片生成失败。",log=str(log),stderr=log.read_text(encoding="utf-8",errors="replace")[-6000:])
        return dict(task_id=req.task_id,path=str(path),**json.loads(response.read_text(encoding="utf-8")))

    def run_layout_export(self,req):
        self._require_work()
        sequential=str(self.system.Mode)=="Sequential"
        if sequential==req.kind.startswith("nsc_"):
            raise ZemaxError("UNSUPPORTED_MODE","布局类型与当前系统模式不符。")
        path=output_path(req.path,{".png"},req.overwrite)
        if sequential:
            last=self.system.LDE.NumberOfSurfaces-1
            end=last if req.end is None else req.end
            if not req.start<=end<=last:raise ZemaxError("INDEX_OUT_OF_RANGE","布局曲面范围越界。")
            if req.field>self.system.SystemData.Fields.NumberOfFields or req.wavelength>self.system.SystemData.Wavelengths.NumberOfWavelengths:
                raise ZemaxError("INDEX_OUT_OF_RANGE","布局视场或波长编号越界。")
        methods=dict(cross_section="OpenCrossSectionExport",viewer_3d="Open3DViewerExport",shaded_model="OpenShadedModelExport",nsc_3d="OpenNSC3DLayoutExport",nsc_shaded="OpenNSCShadedModelExport")
        owner=getattr(self.system.Tools,"Layouts",None)
        method=getattr(owner,methods[req.kind],None)
        if method is None:raise ZemaxError("UNSUPPORTED_INTERFACE","本机不提供请求的布局导出接口。",kind=req.kind)
        tool=method()
        try:
            tool.SaveImageAsFile=True;tool.OutputFileName=str(path)
            # 2024 R2 leaves IsValidFileName false even after a successful PNG export.
            # Use validated output_path and the native Run/Succeeded outcome instead.
            tool.OutputPixelWidth=req.width;tool.OutputPixelHeight=req.height
            if sequential:
                tool.StartSurface=req.start;tool.EndSurface=end;tool.NumberOfRays=req.number_of_rays
                for attr,value,setall in (("Field",req.field,"SetFieldsAll"),("Wavelength",req.wavelength,"SetWavelengthsAll")):
                    if value==0 and hasattr(tool,setall):getattr(tool,setall)()
                    else:setattr(tool,attr,value)
            if req.kind=="cross_section":tool.Configuration=self.system.MCE.CurrentConfiguration
            else:
                tool.ConfigurationAll=False;tool.ConfigurationCurrent=True
                tool.SetCameraViewpoint(self.native.enum(self.native.api.Tools.Layouts.CameraViewpointOptions,req.viewpoint))
            path.parent.mkdir(parents=True,exist_ok=True)
            actual=dict(kind=req.kind,requested=req.model_dump(),native=scalar_settings(tool))
        except Exception:self._release_owned(tool);raise
        def collect(task):
            if not tool.Succeeded:raise ZemaxError("LAYOUT_EXPORT_FAILED",str(tool.ErrorMessage))
            if not path.is_file():raise ZemaxError("EXPORT_FAILED","原生布局未生成请求的图片。",path=str(path))
            return dict(path=str(path),kind=req.kind,render_source="native OpticStudio layout export",artifacts=[dict(kind="native_image",path=str(path))])
        return self._start_task("layout_export",tool,actual,collector=collect)

    def run_cad_export(self,req):
        self._require_work();path=output_path(req.path,CAD_EXTENSIONS[req.format],req.overwrite)
        sequential=str(self.system.Mode)=="Sequential"
        total=self.system.LDE.NumberOfSurfaces-2 if sequential else self.system.NCE.NumberOfObjects
        end=req.end if req.end is not None else total
        if not req.start<=end<=total:raise ZemaxError("INDEX_OUT_OF_RANGE","CAD 导出范围越界。")
        if req.format=="VisualizationJSON":return self._visualization_export(req,path,end,sequential)
        if req.configuration is not None and req.configuration>self.system.MCE.NumberOfConfigurations:
            raise ZemaxError("INDEX_OUT_OF_RANGE","CAD configuration is out of range.",configuration=req.configuration)
        if not sequential and req.ray_pattern=="SolidRing":
            raise ZemaxError("UNSUPPORTED_SETTING","SolidRing requires a sequential system.",setting="ray_pattern")
        if not sequential and req.number_of_rays:
            raise ZemaxError("INACTIVE_SETTING","NSC CAD光线数量由各光源NumberOfLayoutRays控制。",setting="number_of_rays",condition="IExportCAD.SequentialSettingsEnabled=false; per-source layout ray counts")
        mode=req.configuration_mode or ('single'if req.configuration is not None else'current')
        configurations=int(self.system.MCE.NumberOfConfigurations)
        encoding={'current':0,'single':req.configuration,'all_by_file':configurations+1,'all_by_layer':configurations+2,'all_at_once':configurations+3}[mode]
        multi_directory=None;native_path=path
        if mode=='all_by_file':
            # The native multi-file writer requires its canonical STEP/IGES extension.
            multi_directory=path.parent/(path.stem+'_configs_'+uuid.uuid4().hex[:12])
            multi_directory.mkdir(parents=True)
            native_path=multi_directory/(path.stem+{'STEP':'.stp','IGES':'.igs'}.get(req.format,path.suffix))
        tool=self.system.Tools.OpenExportCAD()
        try:
            self.native.set_enum(tool,"FileType",req.format);self.native.set_enum(tool,"Tolerance",req.tolerance)
            if sequential:tool.FirstSurface=req.start;tool.LastSurface=end
            else:tool.FirstObject=req.start;tool.LastObject=end
            tool.SurfacesAsSolids=req.surfaces_as_solids;tool.ExportDummySurfaces=req.export_dummy_surfaces;tool.NumberOfRays=req.number_of_rays
            if mode=='current':tool.SetCurrentConfiguration()
            elif mode=='single':tool.SetSingleConfiguration(req.configuration)
            else:getattr(tool,{'all_by_file':'SetConfigurationAllByFile','all_by_layer':'SetConfigurationAllByLayer','all_at_once':'SetConfigurationAllAtOnce'}[mode])()
            if req.field:tool.Field=req.field
            else:tool.SetFieldAll()
            if req.wavelength:tool.Wavelength=req.wavelength
            else:tool.SetWavelengthAll()
            path.parent.mkdir(parents=True,exist_ok=True);tool.OutputFileName=str(native_path)
            scalar_options=dict(DeleteVignetted=req.delete_vignetted,RayLayer=req.ray_layer,LensLayer=req.lens_layer,
                DummyThickness=req.dummy_thickness,ScatterNSCRays=req.scatter_nsc_rays,SplitNSCRays=req.split_nsc_rays,
                UsePolarization=req.use_polarization,AutoNameFaces=req.auto_name_faces)
            enum_options=dict(RayPattern=req.ray_pattern,SplineSegments=req.spline_segments,
                AngularTolerance=req.angular_tolerance,FileVersion=req.file_version)
            for name,value in scalar_options.items():
                if value is not None:setattr(tool,name,value)
            for name,value in enum_options.items():
                if value is not None:self.native.set_enum(tool,name,value)
            expected=dict(SurfacesAsSolids=req.surfaces_as_solids,ExportDummySurfaces=req.export_dummy_surfaces,
                          NumberOfRays=req.number_of_rays,Field=req.field,Wavelength=req.wavelength,
                          Configuration=encoding,OutputFileName=str(native_path))
            expected.update(dict(FirstSurface=req.start,LastSurface=end)if sequential else dict(FirstObject=req.start,LastObject=end))
            expected.update({name:value for name,value in scalar_options.items()if value is not None})
            from .detectors import check_setting_value
            for name,value in expected.items():check_setting_value(name,value,getattr(tool,name))
            enums=dict(FileType=req.format,Tolerance=req.tolerance)|{name:value for name,value in enum_options.items()if value is not None}
            for name,value in enums.items():
                enum_type=tool.GetType().GetProperty(name).PropertyType
                wanted=self.native.enum(enum_type,value);adopted=getattr(tool,name)
                if not (adopted.Equals(wanted)if hasattr(adopted,"Equals")else adopted==wanted):
                    raise ZemaxError("SETTING_REJECTED","CAD原生枚举未采用。",setting=name,requested=value,actual=str(adopted))
            actual=scalar_settings(tool)
            actual["checked_fields"]=list(expected)+list(enums)
            actual["requested"]=req.model_dump()
            actual["configuration_selection"]=dict(mode=mode,
                resolved_configuration=(int(self.system.MCE.CurrentConfiguration)if mode=="current"else req.configuration)if mode in {"current","single"}else list(range(1,configurations+1)),
                native_encoding=int(tool.Configuration))
        except Exception as original:
            try:self._release_owned(tool)
            except Exception as cleanup:
                error=original if isinstance(original,ZemaxError)else ZemaxError("CAD_SETUP_FAILED",str(original),native_type=type(original).__name__)
                error.details["cleanup_error"]=cleanup.as_dict()if isinstance(cleanup,ZemaxError)else dict(message=str(cleanup))
                raise error from original
            raise
        def collect(task):
            if not tool.Succeeded:raise ZemaxError("CAD_EXPORT_FAILED",str(tool.ErrorMessage))
            if not self._close_task_native(task):raise ZemaxError("CLEANUP_FAILED","CAD工具关闭未确认。",cleanup_warnings=task.get("cleanup_warnings"))
            if multi_directory is not None:
                import re
                files=sorted(p for p in multi_directory.iterdir()if p.is_file())
                selected=[]
                for file in files:
                    match=re.fullmatch(re.escape(path.stem)+r'_config(\d+)\.[^.]+',file.name,re.IGNORECASE)
                    if match:selected.append(dict(configuration=int(match[1]),path=str(file)))
                if sorted(p['configuration']for p in selected)!=list(range(1,configurations+1)):
                    raise ZemaxError('NO_RESULT_DATA','CAD多配置文件集合与请求配置不符。',directory=str(multi_directory),expected_configurations=configurations,files=[str(p)for p in files])
                metadata=[dict(path=str(p),metadata=acis_metadata(p,req.format,req.file_version))for p in files]if req.format in {'SAT','SAB'}else []
                if sequential and req.format=='IGES' and req.lens_layer is not None and req.number_of_rays==0:
                    metadata=[dict(path=str(p),metadata=iges_layer_metadata(p,{req.lens_layer}))for p in files]
                return dict(file_metadata=metadata,path=str(multi_directory),paths=[str(p)for p in files],configurations=selected,format=req.format,artifacts=[dict(kind='cad',path=str(p))for p in files])
            if not path.is_file():raise ZemaxError("NO_RESULT_DATA","CAD原生工具报告成功但没有生成输出文件。",path=str(path))
            metadata=acis_metadata(path,req.format,req.file_version)
            if sequential and req.format=='IGES' and req.lens_layer is not None and req.number_of_rays==0:
                expected_layers={req.lens_layer+i for i in range(configurations)} if mode=='all_by_layer' else {req.lens_layer}
                metadata=iges_layer_metadata(path,expected_layers)
            return dict(path=str(path),format=req.format,**({"file_metadata":metadata}if metadata else {}),artifacts=[dict(kind="cad",path=str(path))])
        return self._start_task("cad_export",tool,actual,collector=collect)

    def _visualization_export(self,req,path,end,sequential):
        if req.number_of_rays or req.field or req.wavelength:
            raise ZemaxError("UNSUPPORTED_SETTING","三角网格导出不提供光线、视场或波长设置。")
        if not sequential and req.start!=end:
            raise ZemaxError("UNSUPPORTED_SETTING","非序列三角网格每次选择一个对象。")
        tool=self.system.Tools.OpenShadedModelVisualizationExport()
        try:
            if sequential:tool.StartSurface=req.start;tool.EndSurface=end
            else:tool.Object=req.start
            actual=scalar_settings(tool)
        except Exception:self._release_owned(tool);raise
        def collect(task):
            if not tool.Succeeded:raise ZemaxError("GEOMETRY_EXPORT_FAILED",str(tool.ErrorMessage))
            result=tool.GetResults()
            if result is None:raise ZemaxError("GEOMETRY_EXPORT_FAILED","无原生三角形结果。")
            vectors={key:dotnet_array(getattr(result,attr).Data)for key,attr in dict(x="XCoords",y="YCoords",z="ZCoords",nx="XNormals",ny="YNormals",nz="ZNormals",surface="SurfaceIndex",object="ObjectIndex").items()}
            if any(not math.isfinite(v)for key in ("x","y","z","nx","ny","nz")for v in vectors[key]):
                raise ZemaxError("INVALID_RESULT_DATA","三角网格包含非有限坐标。")
            data=dict(triangles=int(result.NumberOfTriangles),surfaces=int(result.NumberOfSurfaces),objects=int(result.TotalNumberOfObjects),vectors=vectors,position_unit=str(self.system.SystemData.Units.LensUnits),coordinate_frame="native shaded-model visualization coordinates",ordering="native triangle-list vectors")
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False),encoding="utf-8")
            return {k:v for k,v in data.items()if k!="vectors"}|dict(artifacts=[dict(kind="geometry",path=str(path))])
        return self._start_task("visualization_export",tool,actual,collector=collect)
