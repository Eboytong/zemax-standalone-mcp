from .errors import ZemaxError

class RaysMixin:
    def _extended_trace_flow(self,task,req,target):
        from System import Int32,Double
        direct=req.input_mode=="Direct";pol=req.polarization is not None;api=self.native.api.Tools.RayTrace
        task["summary"]=dict(requested=len(req.rays),coordinate_frame="target surface local",input_frame="start surface local"if direct else"normalized field/pupil",start_surface=req.start_surface if direct else None,target_surface=target,position_unit=task["context"]["lens_units"],direction_unit="dimensionless",opd_available=False,vignetting_status_available=direct,intensity_scope="native polarized losses"if pol else"unpolarized interface excludes coating/Fresnel/bulk loss",succeeded=0,error=0,vignetted=0,missing=0)
        task["summary"]["direction_convention"]="raw native sequential cosines; folded systems require native propagation/sign conventions, not a direction-sign assumption from coordinate frame alone"
        for start in range(0,len(req.rays),1024):
            self._cancel_boundary(task)
            tool=self.system.Tools.OpenBatchRayTrace();holder={"native":tool}
            try:
                rays=req.rays[start:start+1024];kind=self.native.enum(api.RaysType,req.ray_type)
                if pol:
                    p=req.polarization
                    args=[len(rays),kind,p.jx,p.jy,p.x_phase,p.y_phase]
                    data=tool.CreateDirectPol(*args,req.start_surface,target)if direct else tool.CreateNormPol(*args,target)
                else:data=tool.CreateDirectUnpol(len(rays),kind,req.start_surface,target)
                for ray in rays:
                    okay=data.AddRay(ray.wavelength,ray.x,ray.y,ray.z,ray.l,ray.m,ray.n) if direct else data.AddRay(ray.wavelength,ray.hx,ray.hy,ray.px,ray.py,0,0,0,0,0,0)
                    if not okay:raise ZemaxError("RAY_REJECTED","原生接口拒绝光线。")
                if not tool.Run():raise ZemaxError("TASK_START_FAILED",str(tool.ErrorMessage))
                while tool.IsRunning:
                    if task["cancel_requested"] and tool.CanCancel:tool.Cancel()
                    yield
                tool.WaitForCompletion();self._cancel_boundary(task)
                if not tool.Succeeded:raise ZemaxError("TASK_FAILED",str(tool.ErrorMessage))
                data.StartReadingResults();found={}
                ints=3 if direct else 2
                doubles=13 if pol else 10
                while True:
                    out=(data.ReadNextResultFull if pol else data.ReadNextResult)(*([Int32(0)]*ints+[Double(0)]*doubles))
                    if not out[0]:break
                    i=int(out[1])-1
                    if not 0<=i<len(rays) or i in found:raise ZemaxError("INVALID_RESULT_DATA","光线序号重复或越界。")
                    error=int(out[2]);vignette=int(out[3])if direct else None;at=4 if direct else 3
                    row=dict(index=start+i,input=rays[i].model_dump(),error_code=error,vignette_code=vignette,position=list(map(float,out[at:at+3]))if not error else None,direction=list(map(float,out[at+3:at+6]))if not error else None,intensity=float(out[-1])if not error else None,opd=None,state="error"if error else"vignetted"if vignette else"succeeded")
                    if pol:row["electric_field"]={k:float(v)for k,v in zip(("ex_real","ex_imag","ey_real","ey_imag","ez_real","ez_imag"),out[at+6:at+12])}if not error else None
                    else:row["surface_normal"]=list(map(float,out[at+6:at+9]))if not error else None
                    found[i]=row
                for i in range(len(rays)):
                    row=found.get(i,dict(index=start+i,input=rays[i].model_dump(),state="missing",position=None,direction=None,error_code=None,vignette_code=None,intensity=None))
                    task["rows"].append(row);task["summary"][row["state"]]+=1
            finally:self._release_owned(tool)
            task["progress"]=int(100*len(task["rows"])/len(req.rays));yield
