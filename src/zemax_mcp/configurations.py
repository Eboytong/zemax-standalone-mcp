"""MCE editing and finite native global searches."""
from .errors import ZemaxError
from .analyses import scalar_settings

CONFIG_SOLVES={"fixed":"Fixed","variable":"Variable","config_pickup":"ConfigPickup","thermal_pickup":"ThermalPickup"}

def write_configuration_cell(backend,cell,value):
    """Account for the installed MCE DoubleValue getter's nine significant digits."""
    try:
        backend._write_cell(cell,value)
    except ZemaxError as exc:
        if exc.code!='SETTING_REJECTED' or str(cell.DataType)!='Double' or type(value)not in (int,float):
            raise
        from .detectors import check_setting_value
        # The native setter retains more precision than its getter exposes (probe538).
        # Compare only the confirmed getter representation, preserving genuine rejections.
        expected=float(format(value,'.9g'))
        try:check_setting_value(str(cell.Header),expected,float(cell.DoubleValue))
        except Exception:raise exc

class ConfigurationsMixin:
    def _configuration_number(self,number):
        if not 1<=number<=self.system.MCE.NumberOfConfigurations:
            raise ZemaxError("INDEX_OUT_OF_RANGE","结构编号越界。",configuration=number)

    def get_configurations(self,req):
        self._require_sequential()
        m=self.system.MCE
        start=req.start if req else 1; count=req.count if req else 200
        end=min(m.NumberOfOperands+1,start+count)
        rows=[]
        for i in range(start,end):
            row=m.GetOperandAt(i); cells=[]
            for c in range(1,m.NumberOfConfigurations+1):
                cell=row.GetOperandCell(c)
                solve={"mode":str(cell.Solve)}
                if str(cell.Solve) in {"ConfigPickup","ThermalPickup"}:
                    obj=getattr(cell.GetSolveData(),"_S_"+str(cell.Solve))
                    solve.update(configuration=int(obj.Configuration))
                    if str(cell.Solve)=="ConfigPickup":
                        solve.update(operand=int(obj.Operand),scale=float(obj.ScaleFactor) if obj.SupportsScale else None,offset=float(obj.Offset) if obj.SupportsOffset else None)
                cells.append(dict(configuration=c,value=self._cell_value(cell),writable=bool(cell.IsActive and not cell.IsReadOnly),header=str(cell.Header),data_type=str(cell.DataType),solve=solve,available_solves=[str(x) for x in cell.GetAvailableSolveTypes()]))
                if str(cell.DataType)=='Double':
                    cells[-1]['value_readback']=dict(source='native MCE DoubleValue',significant_digits=9,
                        internal_precision='may exceed getter precision; controlled CRVT projects to full-precision LDE radius',
                        evidence='verification/development/ED-03/probe538-mce.json')
            rows.append(dict(operand=i,type=str(row.Type),parameters={j:int(getattr(row,"Param"+str(j))) for j in range(1,4) if getattr(row,"Param"+str(j)+"Enabled")},cells=cells))
        return dict(current_configuration=int(m.CurrentConfiguration),configuration_count=int(m.NumberOfConfigurations),rows=rows,total=int(m.NumberOfOperands),next_start=end if end<=m.NumberOfOperands else None)

    def set_configuration(self,req):
        self._require_sequential(); self._configuration_number(req.configuration)
        self._mutate("configuration")
        if not self.system.MCE.SetCurrentConfiguration(req.configuration):
            raise ZemaxError("CONFIGURATION_FAILED","原生结构切换失败。")
        status=str(self.system.UpdateStatus())
        if status:raise ZemaxError("CONFIGURATION_FAILED","结构更新报告错误。",status=status)
        return self.get_system_summary(None)

    def update_configurations(self,req):
        self._require_sequential(); m=self.system.MCE
        count=int(m.NumberOfConfigurations)
        for a in req.actions:
            if a.action!="add" and (a.configuration is None or not 1<=a.configuration<=count+(a.action=="insert")):
                raise ZemaxError("INDEX_OUT_OF_RANGE","结构操作编号越界。")
            count+=-1 if a.action=="delete" else 1
            if count<1 or count>100: raise ZemaxError("INVALID_ARGUMENT","结构总数须为 1..100。")
        for p in req.operands:
            if p.type: self.native.enum(self.native.api.Editors.MCE.MultiConfigOperandType,p.type)
            if p.operand is None and p.type is None: raise ZemaxError("INVALID_ARGUMENT","新增操作数需要 type。")
            if len({c.configuration for c in p.cells})!=len(p.cells): raise ZemaxError("INVALID_ARGUMENT","重复配置单元格。")
            if any(c.configuration>count for c in p.cells): raise ZemaxError("INDEX_OUT_OF_RANGE","结构单元格编号越界。")
        self._validate_config_graph(req,count)
        self._mutate("mce")
        for a in req.actions:
            okay=m.AddConfiguration(a.copy_current) if a.action=="add" else m.InsertConfiguration(a.configuration,a.copy_current) if a.action=="insert" else m.DeleteConfiguration(a.configuration)
            if not okay: raise ZemaxError("CONFIGURATION_FAILED","结构编辑失败。")
        if not req.actions and not req.delete_operands:
            for p in req.operands:
                if p.operand is None: continue
                row=m.GetOperandAt(p.operand)
                for c in p.cells:
                    cell=row.GetOperandCell(c.configuration)
                    if str(cell.Solve) not in {"Fixed","Variable"} and (c.replace_solve or req.replace_solves):
                        if not cell.MakeSolveFixed(): raise ZemaxError("SOLVE_UPDATE_FAILED","解除旧 MCE 依赖失败。")
        for p in req.operands:
            if p.operand is None: row=m.AddOperand()
            else:
                if p.operand>m.NumberOfOperands: raise ZemaxError("INDEX_OUT_OF_RANGE","MCE 操作数越界。")
                row=m.GetOperandAt(p.operand)
            if p.type:
                if not req.replace_solves and any(str(row.GetOperandCell(c).Solve) not in {"Fixed","Variable"} for c in range(1,count+1)):
                    raise ZemaxError("SOLVE_PROTECTED","改变 MCE 类型会影响求解关系。")
                if not row.ChangeType(self.native.enum(self.native.api.Editors.MCE.MultiConfigOperandType,p.type)):
                    raise ZemaxError("OPERAND_UPDATE_FAILED","MCE 类型设置失败。")
            for key,value in p.parameters.items():
                if not getattr(row,f"Param{key}Enabled"): raise ZemaxError("CELL_NOT_WRITABLE","MCE 参数未启用。",parameter=key)
                setattr(row,f"Param{key}",value)
            for c in p.cells:
                cell=row.GetOperandCell(c.configuration)
                self._guard_cell(cell,c.replace_solve or req.replace_solves)
                if c.value is not None:
                    if str(cell.Solve) not in {"Fixed","Variable"}: cell.MakeSolveFixed()
                    write_configuration_cell(self,cell,c.value)
                if c.solve:
                    spec=c.solve; kind=CONFIG_SOLVES[spec.mode]
                    enum=self.native.enum(self.native.api.Editors.SolveType,kind)
                    if not cell.IsSolveTypeSupported(enum): raise ZemaxError("UNSUPPORTED_SOLVE","MCE 单元格不支持此求解。")
                    data=cell.CreateSolveType(enum)
                    if "pickup" in spec.mode:
                        self._configuration_number(spec.configuration)
                        if spec.configuration==c.configuration and (spec.operand is None or spec.operand==row.OperandNumber):
                            raise ZemaxError("INVALID_SOLVE","禁止自身拾取。")
                        obj=getattr(data,"_S_"+kind); obj.Configuration=spec.configuration
                        if kind=="ConfigPickup":
                            if spec.operand>m.NumberOfOperands: raise ZemaxError("INDEX_OUT_OF_RANGE","拾取操作数越界。")
                            obj.Operand=spec.operand
                            if obj.SupportsScale: obj.ScaleFactor=spec.scale
                            elif spec.scale!=1: raise ZemaxError("UNSUPPORTED_SOLVE_PARAMETER","不支持比例。")
                            if obj.SupportsOffset: obj.Offset=spec.offset
                            elif spec.offset!=0: raise ZemaxError("UNSUPPORTED_SOLVE_PARAMETER","不支持偏移。")
                    self._checked_set_solve(cell,data)
        for i in sorted(set(req.delete_operands),reverse=True):
            if not 1<=i<=m.NumberOfOperands: raise ZemaxError("INDEX_OUT_OF_RANGE","删除操作数越界。")
            if not m.RemoveOperandAt(i): raise ZemaxError("OPERAND_UPDATE_FAILED","删除 MCE 操作数失败。")
        status=str(self.system.UpdateStatus())
        if status:raise ZemaxError("CONFIGURATION_FAILED","MCE 更新报告错误。",status=status)
        self.get_system_settings(None)
        return self.get_configurations(None)

    def _validate_config_graph(self,req,count):
        m=self.system.MCE
        has_pickups=any(c.solve and "pickup" in c.solve.mode for p in req.operands for c in p.cells)
        if has_pickups and (req.actions or req.delete_operands):
            raise ZemaxError("INVALID_ARGUMENT","结构增删与拾取设置须分别调用，使用编辑后回读的编号。")
        if req.actions or req.delete_operands: return
        edges={}; planned=set(); next_row=int(m.NumberOfOperands)
        for i in range(1,m.NumberOfOperands+1):
            for conf in range(1,m.NumberOfConfigurations+1):
                cell=m.GetOperandAt(i).GetOperandCell(conf)
                if str(cell.Solve) in {"ConfigPickup","ThermalPickup"}:
                    s=getattr(cell.GetSolveData(),"_S_"+str(cell.Solve))
                    edges[(i,conf)]=(int(s.Operand) if str(cell.Solve)=="ConfigPickup" else i,int(s.Configuration))
        total=int(m.NumberOfOperands)+sum(p.operand is None for p in req.operands)
        for p in req.operands:
            if p.operand is None: next_row+=1; i=next_row
            else:
                i=p.operand
                if i>m.NumberOfOperands: raise ZemaxError("INDEX_OUT_OF_RANGE","MCE 操作数越界。")
            for c in p.cells:
                key=(i,c.configuration)
                if key in planned: raise ZemaxError("INVALID_ARGUMENT","重复的 MCE 单元格。")
                planned.add(key)
                if i<=m.NumberOfOperands:
                    self._guard_cell(m.GetOperandAt(i).GetOperandCell(c.configuration),c.replace_solve or req.replace_solves)
                edges.pop(key,None)
                if c.solve and "pickup" in c.solve.mode:
                    source=(c.solve.operand if c.solve.mode=="config_pickup" else i,c.solve.configuration)
                    if not 1<=source[0]<=total or not 1<=source[1]<=count: raise ZemaxError("INDEX_OUT_OF_RANGE","MCE 拾取来源越界。")
                    edges[key]=source
        finished=set()
        for start in edges:
            visiting=set(); key=start
            while key in edges and key not in finished:
                if key in visiting: raise ZemaxError("INVALID_SOLVE","MCE 拾取循环。")
                visiting.add(key); key=edges[key]
            finished.update(visiting)

    def get_constraint_coverage(self,req):
        self._require_sequential()
        rows=[]; current=int(self.system.MCE.CurrentConfiguration)
        for i in range(1,self.system.MFE.NumberOfOperands+1):
            op=self.system.MFE.GetOperandAt(i)
            if str(op.Type)=="CONF":
                current=int(op.GetOperandCell(self.native.enum(self.native.api.Editors.MFE.MeritColumn,"Param1")).IntegerValue)
            else:
                rows.append(dict(operand=i,type=str(op.Type),configuration=current,weight=float(op.Weight),target=float(op.Target)))
        return dict(rows=rows,configuration_count=int(self.system.MCE.NumberOfConfigurations),interpretation="CONF 作用于其后的操作数直到下一个 CONF；列出评价函数作用域，不自动判断每个操作数是否为设计约束。")

    def _global_search(self,req,hammer):
        self._require_sequential(focused=True); self._require_work()
        from .hpc import prepare_hpc, open_execution_tool, check_tool_values, close_failed_setup
        hpc = prepare_hpc(self,getattr(req,'hpc',None))
        diagnostics=self._optimization_preflight()
        def launch(_):
            before={**self.evaluate_merit_function(None),"diagnostics":diagnostics}
            self._mutate("before_hammer" if hammer else "before_global")
            tool=open_execution_tool(self,'OpenHammerOptimization' if hammer else 'OpenGlobalOptimization',hpc)
            try:
                self.native.set_enum(tool,"Algorithm",req.algorithm)
                if req.number_of_cores>tool.MaxCores: raise ZemaxError("INVALID_ARGUMENT","核心数超出本机工具限制。")
                tool.NumberOfCores=req.number_of_cores
                if not hammer:self.native.set_enum(tool,"NumberToSave",req.number_to_save)
                actual=scalar_settings(tool);actual["runtime_seconds"]=req.runtime_seconds
                if hpc is not None:
                    values=dict(Algorithm=req.algorithm,NumberOfCores=req.number_of_cores)
                    if not hammer:values['NumberToSave']=req.number_to_save
                    check_tool_values(self,tool,values)
                    actual['hpc']=hpc['actual']
            except Exception as exc:close_failed_setup(self,tool,exc);raise
            def collect(task):
                if not tool.Succeeded and not task.get("budget_stop_requested"):raise ZemaxError("TASK_FAILED",str(tool.ErrorMessage))
                native=scalar_settings(tool)
                if not self._close_task_native(task):raise ZemaxError("CLEANUP_FAILED","优化工具释放失败。")
                final=self.evaluate_merit_function(None)
                path=self.directory/(task["task_id"]+"_optimized.zos")
                self.system.SaveAs(str(path));self.system.SaveAs(str(self.work_path))
                return dict(native=native,termination="time_budget"if task.get("budget_stop_requested")else"native_completion",after=final,variables=self.get_variables(None),artifacts=[dict(kind="lens",path=str(path))])
            return self._start_task("optimization_native",tool,actual,before=before,collector=collect,budget_seconds=req.runtime_seconds)
        def flow(task):
            from .models import Evaluation,Spot,FftMtf
            task["baseline"]={"path":self._checkpoint("search_baseline"),"context":self.context()}
            try:
                optimized=yield from self._child_job(task,launch,None)
                task["phase"] = "verification"
                task["status"] = "搜索已停止，正在独立核对像质；此阶段不计入搜索预算"
                task["summary"]={"optimization":optimized,"validation_settings":{"spot_reference":"ChiefRay","mtf_sampling":"S_64x64","mtf_maximum_frequency":50},"retained_final_design":True,"budget_scope":"native_optimization_only"}
                spec=Evaluation(spot=Spot(reference="ChiefRay"),mtf=FftMtf(sampling="S_64x64",maximum_frequency=50,frequency_unit=str(self.system.SystemData.Units.MTFUnits)),frequencies=[25,50],merit=True)
                verification=yield from self._evaluate(task,spec)
                task["rows"].append(dict(index=0,state="succeeded",**verification))
                task["summary"]["independent_validation_completed"]=True
            finally:
                if task["cancel_requested"]and not self.requires_reconnect:
                    path=self.directory/(task["task_id"]+"_cancelled_candidate.zos")
                    self.system.SaveAs(str(path));self.system.SaveAs(str(self.work_path))
                    task.setdefault("summary",{}).update(retained_final_design=True,cancelled_candidate=str(path),independent_validation_completed=False)
        return self._composite("hammer_optimization"if hammer else"global_optimization",req.model_dump(),flow)

    def run_global_optimization(self,req):
        return self._global_search(req,False)
    def run_hammer_optimization(self,req):
        return self._global_search(req,True)
