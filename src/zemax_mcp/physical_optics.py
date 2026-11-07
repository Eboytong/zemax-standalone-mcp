import math,struct,shutil,uuid
from pathlib import Path
from .data import unwrap
from .analyses import scalar_settings
from .files import input_path
from .errors import ZemaxError
from .detectors import checked_setting,check_setting_value


from .beam_files import read_beam
from .pop_dll import parameter_names


class OwnedInputsAnalysis:
    """Release generated input copies after the native analysis closes."""
    def __init__(self,analysis,paths):self.analysis=analysis;self.paths=paths
    def __getattr__(self,name):return getattr(self.analysis,name)
    def Close(self):
        status=self.analysis.Close()
        if status is False:return False
        for path in self.paths:path.unlink(missing_ok=True)
        return status


class PhysicalOpticsMixin:
    def get_beam_file(self,req):return read_beam(req.path,req.start,req.count,req.include_coordinates)

    def run_pop(self,req):
        self._require_sequential();self._require_work()
        end=req.end_surface or self.system.LDE.NumberOfSurfaces-1
        self._row(req.start_surface);self._row(end)
        if end<req.start_surface:raise ZemaxError("INVALID_ARGUMENT","终止面不得早于起始面。")
        if req.field>self.system.SystemData.Fields.NumberOfFields or req.wavelength>self.system.SystemData.Wavelengths.NumberOfWavelengths:
            raise ZemaxError("INDEX_OUT_OF_RANGE","POP 视场或波长越界。")
        copies=[];selected={}
        try:
            for role,value in (("beam",req.beam_file),("fiber",req.fiber_file)):
                if value and Path(value).is_absolute():
                    extension=".zmm" if role=="beam" and req.beam_type=="Multimode" else ".zbf"
                    original=input_path(value,{extension})
                    destination=Path(str(self.native.application.POPDir))/("mcp_input_"+uuid.uuid4().hex+extension)
                    with destination.open("xb")as target:
                        # Register ownership before source open/copy can fail.
                        copies.append(destination)
                        with original.open("rb")as source:shutil.copyfileobj(source,target)
                    selected[role]=destination.name
                else:selected[role]=value
            tool=self.system.Analyses.New_Analysis(self.native.api.Analysis.AnalysisIDM.PhysicalOpticsPropagation)
        except Exception:
            for path in copies:path.unlink(missing_ok=True)
            raise
        if copies:tool=OwnedInputsAnalysis(tool,copies)
        try:
            s=unwrap(tool.GetSettings());s.Field.SetFieldNumber(req.field);s.Wavelength.SetWavelengthNumber(req.wavelength)
            s.StartSurface.SetSurfaceNumber(req.start_surface);s.EndSurface.SetSurfaceNumber(end)
            for name,requested,actual_number in (("field",req.field,s.Field.GetFieldNumber()),("wavelength",req.wavelength,s.Wavelength.GetWavelengthNumber()),("start_surface",req.start_surface,s.StartSurface.GetSurfaceNumber()),("end_surface",end,s.EndSurface.GetSurfaceNumber())):
                check_setting_value(name,requested,actual_number)
            for key,value in (("BeamType",req.beam_type),("XSampling",req.x_sampling),("YSampling",req.y_sampling),("DataType",req.data_type),("ShowAs","FalseColor"),("Project","AlongBeam")):
                checked_setting(self.native,s,key,value)
            for key,value in dict(XWidth=req.x_width,YWidth=req.y_width,SurfaceToBeam=req.surface_to_beam,
                UsePolarization=req.use_polarization,SeparateXY=req.separate_xy,UseTotalPower=True,
                UsePeakIrradiance=False,TotalPower=req.total_power).items():checked_setting(self.native,s,key,value)
            if req.beam_file is not None:
                if selected["beam"] not in [str(x) for x in s.GetBeamTypeFiles()]:raise ZemaxError("INVALID_RESOURCE","原生POP未识别输入光束文件。")
                checked_setting(self.native,s,"BeamTypeFilename",selected["beam"])
            beam_names,beam_query=parameter_names(s,"beam",req.beam_type,
                getattr(self.native.application,"ZemaxDataDir",None),selected["beam"])
            beam_parameter_count=len(beam_names)
            for i,value in req.beam_parameters.items():
                if i>=beam_parameter_count:raise ZemaxError("INDEX_OUT_OF_RANGE","光束参数越界。")
                s.SetParameterValue(i,value)
                check_setting_value("beam_parameter_"+str(i),value,s.GetParameterValue(i))
            filename="mcp_pop_"+uuid.uuid4().hex+".zbf"
            for key,value in dict(SaveOutputBeam=req.save_output_beam,SaveBeamAtAllSurfaces=req.save_all_surfaces,
                OutputBeamFile=filename,ComputeFiberCouplingIntegral=req.fiber_type is not None).items():checked_setting(self.native,s,key,value)
            if req.fiber_type:
                for key,value in dict(FiberType=req.fiber_type,FiberPosition=req.fiber_position,
                    IgnoreFiberPolarization=req.ignore_fiber_polarization,TiltAboutX=req.fiber_tilt_x,
                    TiltAboutY=req.fiber_tilt_y).items():checked_setting(self.native,s,key,value)
                if req.fiber_file is not None:
                    if selected["fiber"] not in [str(x) for x in s.GetFiberTypeFiles()]:raise ZemaxError("INVALID_RESOURCE","原生POP未识别接收模式文件。")
                    checked_setting(self.native,s,"FiberTypeFilename",selected["fiber"])
                fiber_names,fiber_query=parameter_names(s,"fiber",req.fiber_type,
                    getattr(self.native.application,"ZemaxDataDir",None),selected["fiber"])
                fiber_parameter_count=len(fiber_names)
                for i,value in req.fiber_parameters.items():
                    if i>=fiber_parameter_count:raise ZemaxError("INDEX_OUT_OF_RANGE","光纤参数越界。")
                    s.SetFiberParameterValue(i,value)
                    check_setting_value("fiber_parameter_"+str(i),value,s.GetFiberParameterValue(i))
            actual=scalar_settings(s)
            actual["file_dependencies"]=[dict(role=role,path=path) for role,path in
                (("beam",req.beam_file),("fiber",req.fiber_file)) if path is not None]
            actual["managed_input_files"]=[str(path) for path in copies]
            actual["beam_parameters"]=[dict(index=i,name=name,value=float(s.GetParameterValue(i))) for i,name in enumerate(beam_names)]
            actual["fiber_parameters"]=[dict(index=i,name=name,value=float(s.GetFiberParameterValue(i))) for i,name in enumerate(fiber_names)] if req.fiber_type else []
            actual["parameter_metadata"]={"beam":beam_query,"fiber":fiber_query if req.fiber_type else None}
        except Exception:self._release_owned(tool);raise
        def collect(task):
            result=self._collect_general_analysis(task)
            result["propagation_frame"]="plane perpendicular to chief ray; start before start surface, end after end surface"
            metrics={}
            if req.data_type=="Irradiance" and result["grids"]:
                g=result["grids"][0];values=[v for row in g["values"] for v in row if v is not None]
                if values:
                    metrics["integrated_power"]=sum(values)*abs(g["dx"]*g["dy"])
                    metrics["peak_irradiance"]=max(values)
            if not self._close_task_native(task):raise ZemaxError("CLEANUP_FAILED","POP 资源释放失败。")
            if req.save_output_beam:
                # Native POP writes beam files beneath the application POP directory.
                native_path=Path(str(self.native.application.POPDir))/filename
                alternate=Path(str(self.system.SystemFile)).parent/filename
                beam=native_path if native_path.is_file() else alternate
                if beam.is_file():
                    dest=self.directory/filename
                    if beam!=dest:beam.rename(dest)
                    info=read_beam(dest,0,1)
                    result["beam_metadata"]={k:v for k,v in info.items() if k!="rows"}
                    result["artifacts"].append(dict(kind="beam",path=str(dest)))
                    if req.fiber_type:
                        metrics.update(receiver_efficiency=info["receiver_efficiency_raw"],system_efficiency=info["system_efficiency_raw"],total_coupling_efficiency=info["receiver_efficiency_raw"]*info["system_efficiency_raw"])
                else:raise ZemaxError("EXPORT_FAILED","未找到原生输出光束文件。",requested=filename)
                if req.save_all_surfaces:
                    surface_files=[]
                    for base in {native_path.parent,alternate.parent}:
                        for saved in base.glob(Path(filename).stem+"_*.ZBF"):
                            destination=self.directory/saved.name
                            if saved!=destination:saved.rename(destination)
                            surface_files.append(str(destination))
                            result["artifacts"].append(dict(kind="intermediate_beam",path=str(destination)))
                    result["intermediate_beam_files"]=surface_files
            result["metrics"]=metrics
            if req.fiber_type:
                result["coupling_definition"]=dict(
                    receiver_efficiency="incident-power-weighted mean of independently normalized X/Y complex overlap efficiencies when polarized; scalar X overlap when unpolarized",
                    ignore_fiber_polarization=req.ignore_fiber_polarization,
                    receiver_component="receiver Ex for both incident components"if req.ignore_fiber_polarization else"matching receiver Ex/Ey independently",
                    vector_inner_product=False,
                    total_coupling="system_efficiency * receiver_efficiency",
                    source="OpticStudio 2024 R2 section 3.3.3.16, manual lines 21118 and 21130")
            return result
        return self._start_task("pop",tool,actual,analysis=True,collector=collect)

    def run_pop_convergence(self,req):
        def flow(task):
            records=[]
            pairs=req.sampling_pairs or [(s,s)for s in req.samplings]
            for width in req.widths:
                for sx,sy in pairs:
                    self._cancel_boundary(task)
                    settings=req.settings.model_copy(update=dict(x_width=width[0],y_width=width[1],x_sampling=sx,y_sampling=sy))
                    result=yield from self._child_job(task,self.run_pop,settings)
                    value=result["metrics"].get(req.metric)
                    if type(value) not in {int,float} or not math.isfinite(value):raise ZemaxError("INVALID_METRIC","POP 没有请求的有限指标。",metric=req.metric)
                    row=dict(index=len(records),x_sampling=sx,y_sampling=sy,width=list(width),metric=req.metric,value=value,task_id=result["task"]["task_id"])
                    records.append(row);task["rows"].append(row);yield
            reference=records[-1]["value"]
            for row in records:
                row["delta_to_final"]=row["value"]-reference
                row["within_tolerance"]=abs(row["delta_to_final"])<=req.absolute_tolerance+req.relative_tolerance*abs(reference)
            task["summary"]=dict(reference_index=len(records)-1,reference_rule="explicit list final sampling and final window",all_within_tolerance=all(r["within_tolerance"] for r in records),absolute_tolerance=req.absolute_tolerance,relative_tolerance=req.relative_tolerance)
        return self._composite("pop_convergence",req.model_dump(),flow)
