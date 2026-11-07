"""Adapt a saved detector snapshot for the offline report protocol."""
import json,math
from .files import input_path
from .errors import ZemaxError


def saved_detector_result(filename):
    path=input_path(filename,{".json"})
    try:raw=json.loads(path.read_text(encoding="utf-8"))
    except (ValueError,OSError) as exc:raise ZemaxError("INVALID_RESULT_DATA",str(exc),path=str(path)) from exc
    if not isinstance(raw,dict) or not all(k in raw for k in ("detector","detector_type","kind","context")) or not ("values"in raw or "rows"in raw):
        raise ZemaxError("INVALID_RESULT_TYPE","需要get_detector_data保存的完整JSON。",path=str(path))
    _validate_snapshot(raw,path)
    result=dict(task=dict(kind="saved_detector_snapshot",state="snapshot"),context=raw["context"],
        summary={k:v for k,v in raw.items() if k not in {"values","rows","context"}},
        trace_conditions=raw.get("trace_history",[]),grids=[],series=[],rows=[],
        artifacts=[dict(kind="source_json",path=str(path))])
    unit=raw.get("value_unit","native detector units")
    if raw.get("value_unit_prefix","None")!="None":unit=raw["value_unit_prefix"]+" "+unit
    def add_row(i,value,**coordinates):
        if value is not None and (type(value)not in {int,float}or not math.isfinite(value)):
            raise ZemaxError("INVALID_RESULT_DATA","探测器快照包含无效数值。",index=i)
        result["rows"].append(dict(index=i,state="invalid"if value is None else"measured",**coordinates,
            metrics=[]if value is None else[dict(key=raw.get("quantity",raw.get("color_channel",raw["kind"])),value=value,unit=unit)]))
    if "nz"in raw:
        nx,ny,nz=raw["nx"],raw["ny"],raw["nz"]
        result["volume_values"]=raw["values"]
        for z,plane in enumerate(raw["values"]):
            for y,row in enumerate(plane):
                for x,value in enumerate(row):add_row(x+nx*(y+ny*z),value,x=x,y=y,z=z,
                    local_x=raw["x_axis"]["centers"][x],local_y=raw["y_axis"]["centers"][y],local_z=raw["z_axis"]["centers"][z])
        for z in sorted({0,nz//2,nz-1}):
            grid=_grid(raw,raw["values"][z],len(result["grids"]),unit,"Z slice "+str(z))
            grid.update(z_index=z,z_coordinate=raw["z_axis"]["centers"][z],z_unit=raw["z_axis"]["unit"])
            result["grids"].append(grid)
        result["summary"]["plot_preview"]=dict(z_slices=sorted({0,nz//2,nz-1}),total_slices=nz,full_data="volume_values and rows")
    elif "values"in raw:
        result["grids"]=[_grid(raw,raw["values"],0,unit,raw["detector_type"]+" "+raw.get("color_channel",raw["kind"]))]
        nx=raw["nx"]
        for y,row in enumerate(raw["values"]):
            for x,value in enumerate(row):add_row(x+nx*y,value,x=x,y=y)
    else:
        for i,row in enumerate(raw["rows"]):
            if "value"in row:add_row(i,row["value"],pixel=row.get("pixel"))
            else:
                metrics=[dict(key=k,value=v,unit=unit)for k,v in row.items()if k!="wavelength_um"and type(v)in {float,int}and math.isfinite(v)]
                result["rows"].append({**row,"index":i,"state":"invalid"if any(v is None for v in row.values())else"measured","metrics":metrics})
        if raw.get("kind")=="spectral" and raw["rows"]:
            labels=[k for k in raw["rows"][0]if k!="wavelength_um"]
            result["series"]=[dict(series=0,description="native spectral-bin spatial metrics",x_label="wavelength",x_unit="micrometers",
                labels=labels,x=[r["wavelength_um"]for r in raw["rows"]],y=[[r[k]for k in labels]for r in raw["rows"]])]
    return result


def _validate_snapshot(raw,path):
    def fail(message):raise ZemaxError("INVALID_RESULT_DATA",message,path=str(path))
    if not isinstance(raw["context"],dict):fail("探测器context必须为对象。")
    history=raw.get("trace_history",[])
    if not isinstance(history,list)or not all(isinstance(row,dict)and isinstance(row.get("task_id"),str)and row["task_id"].strip()for row in history):
        fail("trace_history必须为包含非空task_id的记录列表。")
    for row in history:
        if "state"in row and not isinstance(row["state"],str):fail("历史任务state必须为字符串。")
        for key in ("model_revision","configuration"):
            if key in row and row[key]is not None and(type(row[key])is not int or row[key]<0):fail("历史任务修订号与配置必须为非负整数。")

    def scalar(value):
        if value is not None and (type(value)not in {int,float}or not math.isfinite(value)):fail("探测器包含无效数值。")
    if "values"in raw:
        names=("nx","ny","nz")if "nz"in raw else("nx","ny")
        if any(type(raw.get(n))is not int or raw[n]<1 for n in names):fail("探测器尺寸必须为正整数。")
        if math.prod(raw[n]for n in names)>1000000:fail("探测器快照超过1000000样本。")
        def block(values,dimensions):
            if not isinstance(values,list)or len(values)!=dimensions[0]:fail("快照必须包含完整探测器数据，维度与尺寸不符。")
            for value in values:
                if len(dimensions)>1:block(value,dimensions[1:])
                else:scalar(value)
        block(raw["values"],[raw[n]for n in reversed(names)])
        for dimension,name in zip(names,("x_axis","y_axis","z_axis")):
            axis=raw.get(name)
            if axis is None:
                if "nz"in raw:fail("体素快照缺少坐标轴。")
                continue
            if not isinstance(axis,dict)or not isinstance(axis.get("centers"),list)or len(axis["centers"])!=raw[dimension]:fail("坐标轴与探测器尺寸不符。")
            if not all(type(v)in {int,float}and math.isfinite(v)for v in axis["centers"]):fail("坐标轴必须包含有限数值。")
            if not isinstance(axis.get("bounds"),list)or len(axis["bounds"])!=raw[dimension]or not all(isinstance(v,list)and len(v)==2 and all(type(x)in {int,float}and math.isfinite(x)for x in v)for v in axis["bounds"]):fail("坐标边界与探测器尺寸不符。")
            if not all(isinstance(axis.get(k),str)for k in ("name","unit")):fail("坐标轴缺少名称或单位。")
    else:
        if not isinstance(raw["rows"],list)or not all(isinstance(r,dict)for r in raw["rows"]):fail("探测器rows必须为记录列表。")
        if raw.get("kind")=="spectral":
            keys={"wavelength_um","centroid_x","centroid_y","rms_radius","rms_x","rms_y"}
            for row in raw["rows"]:
                if not keys.issubset(row):fail("光谱箱记录缺少波长或空间统计量。")
                for key in keys:scalar(row[key])
                if row["wavelength_um"]is None or row["wavelength_um"]<=0:fail("光谱箱波长必须为正数。")
        else:
            for row in raw["rows"]:
                if "value"not in row:fail("探测器行缺少value。")
                scalar(row["value"])


def _grid(raw,values,index,unit,title):
    x,y=raw.get("x_axis"),raw.get("y_axis")
    return dict(grid=index,description=title,nx=raw["nx"],ny=raw["ny"],values=values,
        min_x=x["centers"][0]if x else 0,min_y=y["centers"][0]if y else 0,
        dx=(x["centers"][1]-x["centers"][0]if len(x["centers"])>1 else x["bounds"][0][1]-x["bounds"][0][0])if x else 1,
        dy=(y["centers"][1]-y["centers"][0]if len(y["centers"])>1 else y["bounds"][0][1]-y["bounds"][0][0])if y else 1,
        x_label=x["name"]if x else"X pixel index",y_label=y["name"]if y else"Y pixel index",
        x_unit=x["unit"]if x else"pixel",y_unit=y["unit"]if y else"pixel",value_label=unit,value_unit=unit)
