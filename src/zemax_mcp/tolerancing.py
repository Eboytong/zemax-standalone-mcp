import math,re
from pathlib import Path
from .data import dotnet_array
from .analyses import scalar_settings
from .errors import ZemaxError

WIZARD_FIELDS={"surface_radius":("IsSurfaceRadiusUsed","SurfaceRadius"),"surface_thickness":("IsSurfaceThicknessUsed","SurfaceThickness"),"surface_decenter_x":("IsSurfaceDecenterXUsed","SurfaceDecenterX"),"surface_decenter_y":("IsSurfaceDecenterYUsed","SurfaceDecenterY"),"surface_tilt_x_degrees":("IsSurfaceTiltXUsed","SurfaceTiltXDegrees"),"surface_tilt_y_degrees":("IsSurfaceTiltYUsed","SurfaceTiltYDegrees"),"element_decenter_x":("IsElementDecenterXUsed","ElementDecenterX"),"element_decenter_y":("IsElementDecenterYUsed","ElementDecenterY"),"element_tilt_x_degrees":("IsElementTiltXUsed","ElementTiltXDegrees"),"element_tilt_y_degrees":("IsElementTiltYUsed","ElementTiltYDegrees")}

def distribution_scope(rows,global_distribution):
    current=dict(type=global_distribution,source="global",sigma_extreme=2 if global_distribution=="Normal"else None)
    output=[]
    for row in rows:
        if row.get("ignore"):continue
        if row["type"]=="STAT":
            params=row["parameters"];kind=params.get(1,params.get("1"))
            n=params.get(2,params.get("2"))
            current=dict(type={0:"Normal",1:"Uniform",2:"Parabolic",3:"UserDefined"}.get(kind,"Unknown"),source_operand=row["operand"],sigma_extreme=min(n,10)if kind==0 and n is not None else None,distribution_file=row.get("comment")if kind==3 else None)
        elif row["type"].startswith("T")and row["minimum"]is not None and row["maximum"]is not None:
            output.append(dict(operand=row["operand"],type=row["type"],minimum=row["minimum"],maximum=row["maximum"],distribution=dict(current)))
    return output

def traceable_trials(text):
    match=re.search(r"^可追迹的蒙特卡罗文件产生数:\s*(\d+)\s*$",text,re.MULTILINE)
    return int(match[1])if match else None


def verified_trial_table(text,requested,rows,columns,criterion_column):
    """2024 R2 Chinese table; unknown layouts/row correspondences remain unavailable."""
    if type(text)is not str or type(requested)is not int or requested<1 or len(rows)!=requested:
        return None
    criteria=[i for i,column in enumerate(columns)if not column.get("is_operand",True)]
    if not criteria or criterion_column!=criteria[0]:return None
    headings=list(re.finditer(r"^蒙特卡罗分析:\s*$",text,re.MULTILINE))
    endings=list(re.finditer(r"^可追迹的蒙特卡罗文件产生数:\s*(\d+)\s*$",text,re.MULTILINE))
    if len(headings)!=1 or len(endings)!=1 or headings[0].end()>=endings[0].start():return None
    body=text[headings[0].end():endings[0].start()]
    counts=re.findall(r"^测试数:\s*(\d+)\s*$",body,re.MULTILINE)
    header=re.search(r"^\s*测试\s+标准\s+改变\s*$",body,re.MULTILINE)
    if counts!=[str(requested)]or header is None:return None
    number=r"[-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?"
    trials=[]
    for line in body[header.end():].splitlines():
        if not line.strip():continue
        success=re.fullmatch(r"\s*(\d+)\s+("+number+r")\s+("+number+r")\s*",line)
        failure=re.fullmatch(r"\s*(\d+)\s+不能追迹透镜，公差可能太宽松!\s*",line)
        if not success and not failure:return None
        trial=int((success or failure)[1])
        if trial!=len(trials)+1 or trial>requested:return None
        row=rows[trial-1]
        if type(row.get("index"))is not int or row["index"]!=trial-1:return None
        values=row.get("values")
        if type(values)is not list or criterion_column>=len(values):return None
        actual=values[criterion_column]
        if success:
            displayed=float(success[2])
            if type(actual)not in (float,int)or not math.isfinite(actual)or not math.isfinite(displayed)or not math.isfinite(float(success[3])):return None
            mantissa,_,exponent=success[2].lower().partition("e")
            decimals=len(mantissa.partition(".")[2])
            precision=.5*10.**(int(exponent or 0)-decimals)
            if abs(actual-displayed)>precision+4*math.ulp(displayed):return None
        trials.append(dict(trial=trial,row_index=trial-1,state="traceable"if success else"untraceable"))
    if len(trials)!=requested or sum(t["state"]=="traceable"for t in trials)!=int(endings[0][1]):return None
    return dict(source_format="OpticStudio 2024 R2 Chinese Monte Carlo summary",criterion_column=criterion_column,trials=trials)

class TolerancingMixin:
    def get_tolerances(self,req):
        from .tolerance_editor import read_tolerances
        return read_tolerances(self,req)

    def update_tolerances(self,req):
        from .tolerance_editor import edit_tolerances
        return edit_tolerances(self,req)

    def generate_tolerances(self,req):
        self._require_sequential();end=req.end_surface if req.end_surface is not None else self.system.LDE.NumberOfSurfaces-2
        self._row(req.start_surface);self._row(end)
        if end<req.start_surface or end>=self.system.LDE.NumberOfSurfaces-1:raise ZemaxError("INDEX_OUT_OF_RANGE","公差向导范围须在物像面之间。")
        self._mutate("tolerance_wizard")
        wizard=self.system.TDE.SEQToleranceWizard
        settings=wizard.ToleranceSettings
        for key,(flag,attr) in WIZARD_FIELDS.items():
            value=getattr(req,key);setattr(settings,flag,value is not None)
            if value is not None:setattr(settings,attr,value)
        settings.IsSurfaceSandAIrregularityUsed=False;settings.IsSurfaceZernikeIrregularityUsed=False
        settings.IsIndexUsed=False;settings.IsIndexAbbePercentageUsed=False;settings.IsFocusCompensationUsed=req.focus_compensation
        settings.StartAtSurface=req.start_surface;settings.StopAtSurface=end
        settings.CommonSettings.OK()
        return self.get_tolerances(None)

    def _tolerance_viewer(self,path):
        viewer=self.system.Tools.OpenToleranceDataViewer()
        try:
            if Path(path).is_file(): viewer.FileName=str(path)
            else: viewer.UseSystemTolerances()
            if not viewer.RunAndWaitForCompletion() or not viewer.Succeeded:raise ZemaxError("TOLERANCE_RESULT_FAILED",str(viewer.ErrorMessage))
            data={"summary_text":str(viewer.Summary),"rows":[],"columns":[],"sensitivity":[]}
            mc=viewer.MonteCarloData
            if mc is not None:
                a=dotnet_array(mc.Values.Data)
                for i,row in enumerate(a):data["rows"].append(dict(index=i,values=[v if math.isfinite(v) else None for v in row]))
                if a:
                    for c in range(len(a[0])):
                        meta=mc.GetMetadata(c)
                        data["columns"].append(dict(column=c,name=str(meta.Name),is_operand=bool(meta.IsOperand)))
            sensitivity=viewer.SensitivityData
            if sensitivity is not None:
                for i in range(sensitivity.NumberOfCriteria):
                    crit=sensitivity.GetCriterion(i)
                    effects=[]
                    for j in range(crit.NumberOfOperands):
                        effect=crit.GetEffectByOperand(j)
                        effects.append(dict(operand_index=j,minimum=float(effect.EstimatedChangeMinimum),maximum=float(effect.EstimatedChangeMaximum)))
                    data["sensitivity"].append(dict(criterion=str(crit.Name),nominal=float(crit.NominalValue),effects=effects))
            return data
        finally:self._release_owned(viewer)

    def run_tolerance_analysis(self,req):
        self._require_sequential();self._require_work()
        from .hpc import prepare_hpc, open_execution_tool, check_tool_values, close_failed_setup
        hpc=prepare_hpc(self,getattr(req,'hpc',None))
        api=self.native.api.Tools.Tolerancing
        self.native.enum(api.Criterions,req.criterion);self.native.enum(api.CriterionComps,req.compensation)
        if req.configuration:self._configuration_number(req.configuration)
        def flow(task):
            source,work=self.source_path,self.work_path
            snapshot=self._checkpoint("tolerance_baseline")
            task["baseline"]={"path":snapshot,"context":self.context()}
            tde=[];start=1
            while start is not None:
                from .tolerance_models import ToleranceRange
                page=self.get_tolerances(ToleranceRange(start=start,count=1000));tde.extend(page["rows"]);start=page["next_start"]
            def launch(_):
                self.revision+=1
                tool=open_execution_tool(self,'OpenTolerancing',hpc)
                try:
                    modes=dict(sensitivity="Sensitivity",inverse_limit="InverseLimit",inverse_increment="InverseIncrement",monte_carlo="SkipSensitivity")
                    for name,value in (("SetupMode",modes[req.mode]),("Criterion",req.criterion),("CriterionComp",req.compensation),("MonteCarloStatistic",req.distribution)):
                        self.native.set_enum(tool,name,value)
                    tool.CriterionSampling=req.sampling;tool.CriterionCycle=req.cycles;tool.CriterionConfiguration=req.configuration
                    tool.MTFFrequency=req.frequency;tool.MaximumCriteria=req.maximum_criterion
                    tool.NumberOfRuns=req.samples if req.mode=="monte_carlo" else 0;tool.NumberToSave=req.save_samples if req.mode=="monte_carlo" else 0
                    tool.FilePrefix=task["task_id"]+"_"
                    tool.UseDataRetention=True;tool.SaveTolDataFile=True;tool.OpenDataViewer=False
                    tool.TolDataFile=task["task_id"]+".ztd"
                    tool.OutputFile=str(self.directory/(task["task_id"]+"_tolerance.txt"))
                    actual=scalar_settings(tool)
                    if hpc is not None:
                        values=dict(SetupMode=modes[req.mode],Criterion=req.criterion,CriterionComp=req.compensation,
                            MonteCarloStatistic=req.distribution,CriterionSampling=req.sampling,CriterionCycle=req.cycles,
                            CriterionConfiguration=req.configuration,MTFFrequency=req.frequency,MaximumCriteria=req.maximum_criterion,
                            NumberOfRuns=req.samples if req.mode=='monte_carlo' else 0,
                            NumberToSave=req.save_samples if req.mode=='monte_carlo' else 0,
                            UseDataRetention=True,SaveTolDataFile=True,OpenDataViewer=False,
                            FilePrefix=task['task_id']+'_',TolDataFile=task['task_id']+'.ztd',
                            OutputFile=str(self.directory/(task['task_id']+'_tolerance.txt')))
                        check_tool_values(self,tool,values)
                        actual['hpc']=hpc['actual']
                except Exception as exc:close_failed_setup(self,tool,exc);raise
                def collect(child):
                    if not tool.Succeeded:raise ZemaxError("TASK_FAILED",str(tool.ErrorMessage))
                    filename=str(tool.TolDataFile);report=str(tool.ResultFilename)
                    if not Path(filename).is_absolute():filename=str(self.directory/filename)
                    if not self._close_task_native(child):raise ZemaxError("CLEANUP_FAILED","公差工具释放失败。")
                    return dict(tolerance_data=filename,report=report,actual=actual)
                return self._start_task("tolerance_native",tool,actual,collector=collect)
            updated=None
            try:
                result=yield from self._child_job(task,launch,None)
                data=self._tolerance_viewer(result["tolerance_data"])
                task["rows"].extend(data.pop("rows"))
                criteria=[i for i,column in enumerate(data["columns"])if not column["is_operand"]]
                sample_status=verified_trial_table(data["summary_text"],req.samples,task["rows"],data["columns"],criteria[0])if req.mode=="monte_carlo"and criteria else None
                if sample_status:
                    for row,trial in zip(task["rows"],sample_status["trials"]):
                        row.update(trial_number=trial["trial"],state="succeeded"if trial["state"]=="traceable"else"failed",
                                   native_trial_status=trial["state"])
                report_path=self.directory/(task["task_id"]+"_summary.txt")
                report_path.write_text(data["summary_text"],encoding="utf-8")
                samples=[str(p)for p in self.directory.glob(task["task_id"]+"_MC*")if p.suffix.lower()in {".zmx",".zos"}]
                task["summary"]={
                    **data,**result,
                    "native_traceable_trials":traceable_trials(data["summary_text"]),
                    "sample_status":dict(source_format=sample_status["source_format"],criterion_column=sample_status["criterion_column"],
                        traceable=sum(t["state"]=="traceable"for t in sample_status["trials"]),
                        untraceable=sum(t["state"]=="untraceable"for t in sample_status["trials"]))if sample_status else dict(state="unavailable"),
                    "saved_summary":str(report_path),
                    "tolerance_data_file_exists":Path(result["tolerance_data"]).is_file(),
                    "tolerances":tde,
                    "distribution_by_operand":distribution_scope(tde,req.distribution),
                    "compensators":[r for r in tde if r["type"]in {"COMP","CPAR","CMCO","CNPA","CNPS","CEDV"}],
                    "requested_samples":req.samples if req.mode=="monte_carlo"else 0,
                    "saved_samples":samples,
                    "requested_saved_samples":req.save_samples if req.mode=="monte_carlo"else 0,
                    "sample_save_shortfall":max(0,req.save_samples-len(samples))if req.mode=="monte_carlo"else 0,
                    "random_seed":{"tool_setter_available":False,"tde_seed_operands":[r for r in tde if r["type"]=="SEED"],"reason":"种子通过 TDE SEED 操作数表达；ITolerancing 无单独 setter。"},
                    "input_distribution":"全局分布及 TDE STAT 的后续作用域共同决定；原始 TDE 随结果保留。",
                }
                if req.mode.startswith("inverse"):
                    updated=self.directory/(task["task_id"]+"_inverse.tol");self.system.TDE.SaveToleranceFile(str(updated))
                yield
            finally:
                self._restore_model(task,snapshot,source,work)
                if updated is not None and not task["cancel_requested"]:
                    self.revision+=1
                    if not self.system.TDE.LoadToleranceFile(str(updated)):
                        self.requires_reconnect=True;raise ZemaxError("RESTORE_FAILED","逆公差范围加载失败。")
        return self._composite("tolerance_analysis",req.model_dump(),flow)

    def summarize_tolerance_results(self,req):
        result=self._full_result(req.task_id)
        if result.get("task",{}).get("kind")!="tolerance_analysis":raise ZemaxError("INVALID_RESULT_TYPE","需要公差任务结果。")
        columns=result.get("summary",{}).get("columns",[])
        if req.criterion_column>=len(columns) or columns[req.criterion_column]["is_operand"]:
            raise ZemaxError("INVALID_METRIC","需要选择原生准则列，不能使用公差操作数列。")
        summary=result.get("summary",{})
        native_traceable=summary.get("native_traceable_trials")
        requested=summary.get("requested_samples")
        rows=result.get("rows",[]);observed=len(rows)
        sample_status=verified_trial_table(summary.get("summary_text"),requested,rows,columns,req.criterion_column)
        untraceable=[t["row_index"]for t in sample_status["trials"]if t["state"]=="untraceable"]if sample_status else []
        if (type(requested)is not int or requested<1 or type(native_traceable)is not int
                or native_traceable<0 or native_traceable>requested or observed>requested
                or sample_status is not None and sum(t["state"]=="traceable"for t in sample_status["trials"])!=native_traceable
                or native_traceable!=requested and sample_status is None):
            raise ZemaxError("SAMPLE_STATUS_UNAVAILABLE",
                "当前格式不能将全部请求试验及失败状态可靠对应到准则行。",
                requested=requested,native_traceable=native_traceable,observed=observed,
                finite_values=sum(type(row["values"][req.criterion_column])in (float,int)and math.isfinite(row["values"][req.criterion_column])for row in rows if req.criterion_column<len(row.get("values",[]))),
                nonfinite_indices=[row.get("index")for row in rows if req.criterion_column<len(row.get("values",[]))and (type(row["values"][req.criterion_column])not in (float,int)or not math.isfinite(row["values"][req.criterion_column]))],
                missing=max(0,requested-observed)if type(requested)is int else None)
        values=[];failed=[];untraceable_set=set(untraceable)
        for row in rows:
            if req.criterion_column>=len(row["values"]):raise ZemaxError("INDEX_OUT_OF_RANGE","准则列越界。")
            if row["index"]in untraceable_set:continue
            value=row["values"][req.criterion_column]
            if type(value) not in {float,int} or not math.isfinite(value):failed.append(row["index"])
            else:values.append(value)
        ordered=sorted(values)
        def percentile(p):
            if not ordered:return None
            x=(len(ordered)-1)*p;i=int(x);fraction=x-i
            return (1-fraction)*ordered[i]+fraction*ordered[min(i+1,len(ordered)-1)]
        passed=sum(v<=req.threshold if req.pass_when=="less_equal" else v>=req.threshold for v in values)
        complete_values=observed==requested and not failed
        return dict(criterion_column=req.criterion_column,unit=req.unit,threshold=req.threshold,
            pass_when=req.pass_when,requested=requested,observed=observed,missing=requested-observed,
            native_traceable_trials=native_traceable,finite_values=len(values),nonfinite_indices=failed,
            native_untraceable_trials=len(untraceable),failed_trial_numbers=[i+1 for i in untraceable],
            passed=passed,pass_fraction_of_requested=passed/requested,
            pass_fraction_scope="requested_sample_set_untraceable_counted_as_failed"if untraceable else"complete_requested_sample_set"if complete_values else"lower_bound_missing_or_nonfinite_criteria",
            mean=math.fsum(v/len(values)for v in values)if values else None,
            quantiles={str(p):percentile(p)for p in (.05,.5,.95)},
            sample_status_scope="已验证中文原生试验表逐行对应；不可追迹试验计为失败，均值及分位数仅用可追迹有限值，合格率分母为请求数。"if untraceable else"原生汇总确认全部请求样本可追迹；均值及分位数使用有限准则值，合格率分母为请求数。",
            conditions=summary)
