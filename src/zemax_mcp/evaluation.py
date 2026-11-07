"""Serial, cooperative evaluation jobs. Native objects stay in the worker."""
import csv
import json
import math
import time
import uuid
from pathlib import Path

from .data import clean, utc_now
from .errors import ZemaxError
from .models import TaskRequest, TaskResult, SurfacePatch, UpdateSurfaces


class Cancelled(Exception):
    pass


MERIT_DEFINITION_FIELDS = ("operand", "type", "target", "weight", "parameters")


def finite_metric(value, metric, **location):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ZemaxError("INVALID_METRIC_VALUE", "指标必须是有限数值。",
                         metric=metric, value=repr(value), **location)
    return value


def interpolate(x, y, target):
    if not x or len(x) != len(y) or any(b <= a for a, b in zip(x, x[1:])):
        raise ZemaxError("INVALID_RESULT_DATA", "MTF 频率轴必须严格递增。")
    if target < x[0] or target > x[-1]:
        raise ZemaxError("FREQUENCY_OUT_OF_RANGE", "请求频率超出结果范围。", frequency=target)
    if target == x[0]:
        return y[0]
    for i in range(1, len(x)):
        if target <= x[i]:
            return y[i-1] + (y[i]-y[i-1]) * (target-x[i-1]) / (x[i]-x[i-1])


class EvaluationMixin:
    def _full_result(self, task_id):
        task = self._task(task_id)
        if task["state"] not in {"succeeded", "failed", "cancelled"}:
            raise ZemaxError("TASK_NOT_FINISHED", "任务尚未结束。")
        if task.get("result_path"):
            try:
                return json.loads(Path(task["result_path"]).read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ZemaxError("RESULT_UNAVAILABLE", str(exc)) from exc
        return task.get("result") or {"task": self._task_view(task)}

    def _composite(self, kind, settings, factory, require_sequential=True):
        if require_sequential:self._require_sequential()
        task = {"task_id": uuid.uuid4().hex, "request_id": self.request_id, "kind": kind,
                "state": "running", "created_at": utc_now(), "settings": settings,
                "context": self.context(), "system_settings": self.get_system_settings(None),
                "progress": 0, "can_cancel": True, "cancel_requested": False,
                "composite": True, "native": None, "rows": [], "result": None}
        task["started_monotonic"] = time.monotonic()
        if kind in {"hammer_optimization", "global_optimization"}:
            task.update(progress=None, phase="optimization", cancellation_effect="retain_candidate")
        task["iterator"] = factory(task)
        self.tasks[task["task_id"]] = task
        self.active = task
        self._record_task_history(task)
        return self._task_view(task)

    def _tick_composite(self, task):
        try:
            child = task.get("child")
            if child and child["state"] not in {"succeeded", "failed", "cancelled"}:
                self.active = child
                try:
                    self.tick()
                finally:
                    self.active = task
                return
            next(task["iterator"])
            return
        except StopIteration:
            task["state"] = "cancelled" if task["cancel_requested"] else "succeeded"
        except Cancelled:
            task["state"] = "cancelled"
        except Exception as exc:
            task["state"] = "failed"
            task["error"] = self._evaluation_error(exc)
        task["finished_at"] = utc_now()
        task["finished_monotonic"] = time.monotonic()
        task["progress"] = 100 if task["state"] == "succeeded" else task["progress"]
        result = {"completed": task["state"] == "succeeded", "rows": task["rows"],
                  "summary": task.get("summary", {}), "restoration": task.get("restoration"),
                  "baseline": task.get("baseline"), "error": task.get("error")}
        result.update(task.get('payload',{}))
        try:
            self._save_task_result(task, result)
        except Exception as exc:
            task["state"] = "failed"
            task["error"] = self._evaluation_error(exc)
            task["result"] = {**result, "task": self._task_view(task)}
        self._record_task_history(task)
        self.active = None

    @staticmethod
    def _evaluation_error(exc):
        return exc.as_dict() if isinstance(exc, ZemaxError) else {"code": "NATIVE_ERROR", "message": str(exc)}

    def _cancel_boundary(self, task):
        if task["cancel_requested"]:
            raise Cancelled()
        if self.requires_reconnect:
            raise ZemaxError("RECONNECT_REQUIRED", "原生资源未确认释放，停止评估。")

    def _child_job(self, parent, method, req, *, cleanup=False):
        if not cleanup:self._cancel_boundary(parent)
        elif self.requires_reconnect:
            raise ZemaxError('RECONNECT_REQUIRED','恢复检查需要先确认原生连接。')
        try:
            view = method(req)
            child = self.tasks[view["task_id"]]
        finally:
            self.active = parent
        parent["child"] = child
        while child["state"] not in {"succeeded", "failed", "cancelled"}:
            yield
        parent["child"] = None
        if not cleanup:self._cancel_boundary(parent)
        if child["state"] != "succeeded":
            raise ZemaxError("CHILD_TASK_FAILED", "分析子任务失败。", task=self._task_view(child))
        return self._full_result(child["task_id"])

    def _evaluate(self, task, spec):
        if spec.focus:
            yield from self._child_job(task, self.run_quick_focus, spec.focus)
        data = {"metrics": [], "analysis_tasks": [], "conditions": {
            "evaluation": spec.model_dump(), "system": {k: v for k, v in self.get_system_settings(None).items() if k not in {"title", "notes"}}}}
        if spec.spot:
            result = yield from self._child_job(task, self.run_spot_analysis, spec.spot)
            data["analysis_tasks"].append(result["task"]["task_id"])
            for row in result["metrics"]:
                for key in ("rms_radius", "geo_radius"):
                    data["metrics"].append({"key": f"spot/field{row['field_number']}/{key}",
                                            "value": row[key], "unit": "micrometers"})
        if spec.mtf:
            result = yield from self._child_job(task, self.run_fft_mtf, spec.mtf)
            data["analysis_tasks"].append(result["task"]["task_id"])
            data["conditions"]["mtf_series"] = [s["description"] for s in result["series"]]
            for series in result["series"]:
                for j, label in enumerate(series["labels"]):
                    for frequency in spec.frequencies:
                        data["metrics"].append({"key": f"mtf/{series['series']}/{label}/{frequency}",
                            "value": interpolate(series["x"], [r[j] for r in series["y"]], frequency), "unit": "dimensionless"})
        if spec.merit:
            value = finite_metric(self.evaluate_merit_function(None)["merit_function"], "merit_function")
            data["metrics"].append({"key": "merit_function", "value": value, "unit": "merit function"})
            operands = []
            start = 1
            while start is not None:
                page = self.get_merit_function(type("Range", (), {"start": start, "count": 500})())
                operands.extend(page["operands"])
                start = page["next_start"]
            data["conditions"]["merit_definition"] = [
                {k: row[k] for k in MERIT_DEFINITION_FIELDS} for row in operands]
            data["merit_operands"] = operands
        if spec.analyses:
            from .analysis_models import RunAnalysis
            results=[]
            data["conditions"]["analyses_actual"]=[]
            for analysis in spec.analyses:
                result=yield from self._child_job(task,self.run_analysis,RunAnalysis(request=analysis))
                results.append(result)
                data["analysis_tasks"].append(result["task"]["task_id"])
                data["conditions"]["analyses_actual"].append(result["task"]["settings"])
            for n,metric in enumerate(spec.analysis_metrics):
                r=results[metric.analysis]
                if metric.kind=="curve":
                    if metric.series>=len(r.get("series",[])): raise ZemaxError("INVALID_METRIC","分析曲线编号越界。")
                    s=r["series"][metric.series]
                    if metric.label not in s["labels"]: raise ZemaxError("INVALID_METRIC","系列标签不存在。",label=metric.label)
                    j=s["labels"].index(metric.label)
                    ys=[finite_metric(row[j],metric.label) for row in s["y"]]
                    value=interpolate(s["x"],ys,metric.x)
                else:
                    if metric.grid>=len(r.get("grids",[])): raise ZemaxError("INVALID_METRIC","分析网格编号越界。")
                    values=[v for row in r["grids"][metric.grid]["values"] for v in row if v is not None]
                    if not values: raise ZemaxError("INVALID_METRIC","网格没有有效值。")
                    value=min(values) if metric.statistic=="minimum" else max(values) if metric.statistic=="maximum" else sum(values)/len(values)
                data["metrics"].append(dict(key=f"analysis/{metric.analysis}/metric/{n}",value=finite_metric(value,f"analysis/{n}"),unit=metric.unit,definition=metric.model_dump()))
        data["context"] = self.context()
        return data

    def run_configuration_evaluation(self,req):
        self._require_sequential()
        for conf in req.configurations:self._configuration_number(conf)
        def flow(task):
            source,work=self.source_path,self.work_path
            snapshot=self._checkpoint("configuration_evaluation")
            task["baseline"]={"path":snapshot,"context":self.context()}
            try:
                for i,conf in enumerate(req.configurations):
                    self._cancel_boundary(task)
                    self._restore_model(task,snapshot,source,work)
                    row={"index":i,"configuration":conf}
                    try:
                        from .configuration_models import ConfigurationSelect
                        self.set_configuration(ConfigurationSelect(configuration=conf))
                        row.update((yield from self._evaluate(task,req.evaluation)))
                        row["state"]="succeeded"
                    except Cancelled:raise
                    except Exception as exc:
                        row.update(state="failed",error=self._evaluation_error(exc))
                        if self.requires_reconnect:raise
                    task["rows"].append(row);task["progress"]=int((i+1)*100/len(req.configurations));yield
            finally:self._restore_model(task,snapshot,source,work)
        return self._composite("configuration_evaluation",req.model_dump(),flow)

    def run_multistart_optimization(self,req):
        self._require_sequential()
        for changes in req.starts:UpdateSurfaces(changes=changes)
        def flow(task):
            source,work=self.source_path,self.work_path
            snapshot=self._checkpoint("multistart_baseline")
            task["baseline"]={"path":snapshot,"context":self.context()}
            best=None;finished=False
            try:
                for i,changes in enumerate(req.starts):
                    self._cancel_boundary(task)
                    self._restore_model(task,snapshot,source,work)
                    row={"index":i}
                    try:
                        self.update_surfaces(UpdateSurfaces(changes=changes))
                        optimized=yield from self._child_job(task,self.run_local_optimization,req.optimization)
                        optimization_merit=finite_metric(optimized["after"]["merit_function"],"merit_function")
                        row.update((yield from self._evaluate(task,req.evaluation)))
                        value=finite_metric(self.evaluate_merit_function(None)["merit_function"],"merit_function")
                        path=self.directory/(task["task_id"]+f"_start_{i}.zos")
                        self.system.SaveAs(str(path));self.system.SaveAs(str(work))
                        row.update(state="succeeded",optimized_merit=optimization_merit,saved_design_merit=value,path=str(path),optimization_task=optimized["task"]["task_id"])
                        if best is None or value<best["value"]:best=dict(index=i,value=value,path=str(path))
                    except Cancelled:raise
                    except Exception as exc:
                        row.update(state="failed",error=self._evaluation_error(exc))
                        if self.requires_reconnect:raise
                    task["rows"].append(row);task["progress"]=int((i+1)*100/len(req.starts));yield
                finished=True
            finally:
                self._restore_model(task,snapshot,source,work)
                if finished and best is not None and not task["cancel_requested"]:
                    self._restore_model(task,best["path"],source,work)
                task["summary"]={"best":best,"retained_best":bool(finished and best and not task["cancel_requested"])}
        return self._composite("multistart_optimization",req.model_dump(),flow)

    def _restore_model(self, task, snapshot, source, work):
        try:
            if self.requires_reconnect:
                raise ZemaxError("CLEANUP_FAILED", "工具释放未确认，保留基线等待重连。")
            self.revision += 1
            if not self.system.LoadFile(snapshot, False):
                raise ZemaxError("RESTORE_FAILED", "基线加载失败。")
            self.system.SaveAs(str(work))
            self.work_path, self.source_path = work, source
            self.get_system_settings(None)
            task["restoration"] = {"restored": True, "checkpoint": snapshot, "context": self.context()}
        except Exception as exc:
            self.requires_reconnect = True
            task["restoration"] = {"restored": False, "checkpoint": snapshot, "error": self._evaluation_error(exc)}
            raise ZemaxError("RESTORE_FAILED", "设计恢复未完成，需要重新连接。", checkpoint=snapshot) from exc

    def _evaluation_flow(self, task, req, scan):
        source, work = self.source_path, self.work_path
        snapshot = self._checkpoint("evaluation_baseline")
        task["baseline"] = {"path": snapshot, "context": self.context()}
        items = req.values if scan else req.paths
        try:
            for i, item in enumerate(items):
                self._cancel_boundary(task)
                row = {"index": i, "value" if scan else "path": item}
                task["status"] = f"评估 {i+1}/{len(items)}"
                try:
                    self.revision += 1
                    if not self.system.LoadFile(snapshot if scan else str(Path(item).resolve()), False):
                        raise ZemaxError("LOAD_FAILED", "评估镜头加载失败。")
                    self._require_sequential()
                    self.work_path = None
                    self.source_path = source if scan else str(Path(item).resolve())
                    self._working_copy()
                    self.get_system_settings(None)
                    if scan:
                        self.update_surfaces(UpdateSurfaces(changes=[SurfacePatch.model_validate({
                            "surface": req.surface, "replace_solves": req.replace_solve,
                            **({"parameters": {int(req.cell[10:]): item}} if req.cell.startswith("parameter_") else {req.cell: item})})]))
                    self._cancel_boundary(task)
                    row.update((yield from self._evaluate(task, req.evaluation)))
                    row["state"] = "succeeded"
                except Cancelled:
                    raise
                except Exception as exc:
                    row.update(state="failed", error=self._evaluation_error(exc))
                    if self.requires_reconnect:
                        task["rows"].append(row)
                        raise
                    if scan and not self.system.LoadFile(snapshot, False):
                        raise ZemaxError("RESTORE_FAILED", "扫描点基线重载失败。")
                task["rows"].append(row)
                task["progress"] = int(100 * (i+1) / len(items))
                yield
        finally:
            task["summary"] = {"requested": len(items), "processed": len(task["rows"]),
                "succeeded": sum(r["state"] == "succeeded" for r in task["rows"]),
                "failed": sum(r["state"] == "failed" for r in task["rows"])}
            self._restore_model(task, snapshot, source, work)

    def run_parameter_scan(self, req):
        cell = self._cell(self._row(req.surface), req.cell)
        self._guard_cell(cell, req.replace_solve)
        return self._composite("parameter_scan", req.model_dump(), lambda t: self._evaluation_flow(t, req, True))

    def run_batch_evaluation(self, req):
        for name in req.paths:
            path = Path(name)
            if not path.is_absolute() or path.suffix.lower() not in {".zos", ".zmx"}:
                raise ZemaxError("INVALID_INPUT_FILE", "批量输入需要绝对 .zos/.zmx 路径。")
        return self._composite("batch_evaluation", req.model_dump(), lambda t: self._evaluation_flow(t, req, False))

    def run_batch_ray_trace(self, req):
        self._require_sequential()
        target = req.target_surface if req.target_surface is not None else self.system.LDE.NumberOfSurfaces - 1
        self._row(target)
        if req.opd and (req.ray_type != "Real" or target != self.system.LDE.NumberOfSurfaces - 1):
            raise ZemaxError("INVALID_ARGUMENT", "OPD 需要真实光线并终止于像面。")
        if any(r.wavelength > self.system.SystemData.Wavelengths.NumberOfWavelengths for r in req.rays):
            raise ZemaxError("INDEX_OUT_OF_RANGE", "波长编号超出范围。")
        if req.input_mode=="Direct" or req.polarization is not None:
            if req.input_mode=="Direct":
                self._row(req.start_surface)
                if target<req.start_surface:raise ZemaxError("INVALID_ARGUMENT","直接追迹目标面不得早于起始面。")
            return self._composite("batch_ray_trace",req.model_dump(),lambda t:self._extended_trace_flow(t,req,target))
        return self._composite("batch_ray_trace", {"ray_count": len(req.rays), "ray_type": req.ray_type, "opd": req.opd, "target_surface": target},
                               lambda t: self._trace_flow(t, req, target))

    def _trace_flow(self, task, req, target):
        from System import Int32, Double
        api = self.native.api.Tools.RayTrace
        task["summary"] = {"requested": len(req.rays), "coordinate_frame": "target surface local",
            "position_unit": task["context"]["lens_units"], "direction_unit": "dimensionless",
            "opd_unit": "waves" if req.opd else None,
            "processed": 0, "succeeded": 0, "error": 0, "vignetted": 0, "missing": 0,
            "intensity_scope": "Unpol ignores bulk absorption, coating losses and Fresnel reflection; not total transmission"}
        for start in range(0, len(req.rays), 1024):
            self._cancel_boundary(task)
            native = self.system.Tools.OpenBatchRayTrace()
            handle = {"native": native}
            try:
                rays = req.rays[start:start+1024]
                data = native.CreateNormUnpol(len(rays), self.native.enum(api.RaysType, req.ray_type), target)
                for ray in rays:
                    if not data.AddRay(ray.wavelength, ray.hx, ray.hy, ray.px, ray.py,
                            self.native.enum(api.OPDMode, "CurrentAndChief" if req.opd else "None")):
                        raise ZemaxError("RAY_REJECTED", "原生接口拒绝添加光线。")
                if not native.Run():
                    raise ZemaxError("TASK_START_FAILED", str(native.ErrorMessage))
                while native.IsRunning:
                    task["status"] = "原生追迹运行中；取消在安全边界生效"
                    if task["cancel_requested"] and native.CanCancel:
                        native.Cancel()
                    yield
                native.WaitForCompletion()
                self._cancel_boundary(task)
                if not native.Succeeded:
                    raise ZemaxError("TASK_FAILED", str(native.ErrorMessage))
                data.StartReadingResults()
                found = {}
                while True:
                    out = data.ReadNextResult(*([Int32(0)] * 3 + [Double(0)] * 11))
                    if not out[0]:
                        break
                    index = int(out[1])-1
                    if index < 0 or index >= len(rays) or index in found:
                        raise ZemaxError("INVALID_RESULT_DATA", "原生光线序号无效或重复。")
                    error, vignette = int(out[2]), int(out[3])
                    valid = error == 0
                    found[index] = {"index": start+index, "input": rays[index].model_dump(),
                        "error_code": error, "vignette_code": vignette,
                        "position": list(map(float, out[4:7])) if valid else None,
                        "direction": list(map(float, out[7:10])) if valid else None,
                        "surface_normal": list(map(float, out[10:13])) if valid else None,
                        "opd": float(out[13]) if valid and req.opd else None,
                        "intensity": float(out[14]) if valid else None,
                        "state": "error" if error else "vignetted" if vignette else "succeeded"}
                task["rows"].extend(found.get(i, {"index": start+i, "input": rays[i].model_dump(),
                    "state": "missing", "position": None, "direction": None, "error_code": None,
                    "vignette_code": None, "opd": None, "intensity": None}) for i in range(len(rays)))
                task["summary"]["processed"] = len(task["rows"])
                for state in ("succeeded", "error", "vignetted", "missing"):
                    task["summary"][state] = sum(r["state"] == state for r in task["rows"])
            finally:
                if not self._close_task_native(handle):
                    task["cleanup_warnings"] = handle["cleanup_warnings"]
                    raise ZemaxError("CLEANUP_FAILED", "批量追迹资源释放未确认。")
            task["progress"] = int(100 * len(task["rows"]) / len(req.rays))
            yield

    def compare_results(self, req):
        if any(self._task(t)["state"] != "succeeded" for t in (req.left_task_id, req.right_task_id)):
            raise ZemaxError("INCOMPATIBLE_RESULTS", "比较要求评估任务成功结束。")
        left, right = self._full_result(req.left_task_id), self._full_result(req.right_task_id)
        a, b = left.get("rows", []), right.get("rows", [])
        if not a or not b or any("conditions" not in r for r in a+b):
            raise ZemaxError("INCOMPATIBLE_RESULTS", "比较需要全部成功的评估结果。")
        if all("configuration"in row for row in a+b):
            ma={r["configuration"]:r for r in a};mb={r["configuration"]:r for r in b}
            if len(ma)!=len(a)or len(mb)!=len(b)or ma.keys()!=mb.keys():
                raise ZemaxError("INCOMPATIBLE_RESULTS","配置集合不同或存在重复配置。")
            a=[ma[k]for k in sorted(ma)];b=[mb[k]for k in sorted(mb)]
        for task_id, rows in ((req.left_task_id, a), (req.right_task_id, b)):
            for i, row in enumerate(rows):
                for metric in row["metrics"]:
                    finite_metric(metric["value"], metric["key"], task_id=task_id, row=i)
        differences = []
        output = []
        if len(a) != len(b):
            differences.append("评估行数不同")
        for i, (x, y) in enumerate(zip(a, b)):
            for side,row in (("left",x),("right",y)):
                if "system" in row["conditions"]:
                    required=("material_catalogs","files","polarization","ray_aiming","field_normalization","fields")
                    for key in required:
                        if key not in row["conditions"]["system"]:
                            differences.append(f"第 {i} 行 {side} 缺少系统条件 {key}")
                    for field in row["conditions"]["system"].get("fields",[]):
                        for key in ("vdx","vdy","vcx","vcy","van"):
                            if key not in field: differences.append(f"第 {i} 行 {side} 视场 {field.get('number')} 缺少 {key}")
            if x["conditions"] != y["conditions"]:
                differences.append(f"第 {i} 行的系统、分析、焦位策略或评价函数定义不同")
            mx = {m["key"]: m for m in x["metrics"]}
            my = {m["key"]: m for m in y["metrics"]}
            if mx.keys() != my.keys():
                differences.append(f"第 {i} 行的指标集合不同")
            for key in mx.keys() & my.keys():
                u, v = mx[key], my[key]
                if u["unit"] != v["unit"]:
                    differences.append(f"{key} 单位不同")
                delta = finite_metric(v["value"]-u["value"], key, row=i, operation="difference")
                output.append({"index": i, "key": key, "left": u["value"], "right": v["value"],
                               "delta": delta, "unit": u["unit"]})
        return {"compatible": not differences, "differences": differences,
                "metrics": output if not differences else [],
                "left_task_id": req.left_task_id, "right_task_id": req.right_task_id}

    def export_evaluation_report(self, req):
        results=[];seen=set();pending=list(req.task_ids)
        from .saved_detector import saved_detector_result
        for filename in req.detector_files:
            result=saved_detector_result(filename)
            results.append(dict(task_id="detector_snapshot_"+uuid.uuid4().hex[:12],result=result))
            unavailable=[]
            for reference in result.get("trace_conditions",[]):
                related=reference["task_id"]
                if related in self.tasks and self.tasks[related].get("state")in {"succeeded","failed","cancelled"}:pending.append(related)
                else:unavailable.append(reference)
            if unavailable:result["unavailable_trace_tasks"]=unavailable
        while pending:
            task_id=pending.pop(0)
            if task_id in seen:continue
            if len(seen)>=1000:raise ZemaxError("REPORT_TOO_LARGE","报告关联分析超过 1000 个任务，请选择较小的结果集合。")
            seen.add(task_id);result=self._full_result(task_id)
            results.append(dict(task_id=task_id,result=result))
            unavailable=[]
            for row in result.get("rows",[]):
                pending.extend(row.get("analysis_tasks",[]))
                if row.get("optimization_task"):pending.append(row["optimization_task"])
                for reference in row.get("trace_conditions",[]):
                    related=reference["task_id"]
                    task=self.tasks.get(related)
                    if task and task.get("state") in {"succeeded","failed","cancelled"}:
                        pending.append(related)
                    elif related not in seen:
                        unavailable.append(dict(task_id=related, state=reference.get("state","unknown"),
                            error=reference.get("error"), reason="关联任务不存在或尚未结束；保留累计表中的历史快照。"))
            if unavailable:
                result={**result,"unavailable_trace_tasks":unavailable}
                results[-1]["result"]=result
        folder = self.directory / ("report_" + uuid.uuid4().hex[:10])
        folder.mkdir()
        if not req.background and not req.include_charts and "pdf" not in req.formats:
            from .reports import export_saved_report
            return export_saved_report(folder,results,req.title,req.include_charts,req.formats)
        from .report_worker import ReportProcess
        request_file=folder/"request.json"
        response_file=folder/"response.json"
        request_file.write_text(json.dumps(clean(dict(folder=str(folder),results=results,title=req.title,include_charts=req.include_charts,formats=req.formats)),ensure_ascii=False,allow_nan=False),encoding="utf-8")
        process=ReportProcess(request_file,response_file)
        if not req.background:
            import time
            process.Run();deadline=time.monotonic()+45
            try:
                while process.IsRunning:
                    if time.monotonic()>=deadline:
                        process.Cancel();process.WaitForCompletion()
                        raise ZemaxError("REPORT_TIMEOUT","同步报告超过45秒；可使用background=true。")
                    time.sleep(.02)
                if not process.Succeeded:raise ZemaxError("REPORT_FAILED",process.ErrorMessage)
                return json.loads(response_file.read_text(encoding="utf-8"))
            finally:process.Close()
        def collect(task):
            if not process.Succeeded:
                raise ZemaxError("REPORT_FAILED",process.ErrorMessage)
            return json.loads(response_file.read_text(encoding="utf-8"))
        return self._start_task("evaluation_report",process,req.model_dump(),collector=collect)
