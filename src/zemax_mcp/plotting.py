"""Single-image exports from saved data, with explicit rendering provenance."""
import shutil
from pathlib import Path
from .errors import ZemaxError


def export_image(result,request,path):
    if request.source=="native":
        images=[a for a in result.get("artifacts",[]) if a.get("kind")=="native_image"]
        if not images:
            raise ZemaxError("UNSUPPORTED_NATIVE_IMAGE","已保存结果没有原生图片；本机通用分析结果接口不提供窗口位图导出。")
        if request.item>=len(images):raise ZemaxError("INDEX_OUT_OF_RANGE","原生图片编号越界。")
        source=Path(images[request.item]["path"])
        if not source.is_file():raise ZemaxError("MISSING_ARTIFACT","原生图片不存在。",path=str(source))
        path.parent.mkdir(parents=True,exist_ok=True)
        if source.resolve()!=path:
            if source.suffix.lower()==path.suffix.lower():shutil.copy2(source,path)
            else:
                try:from PIL import Image
                except ImportError as exc:raise ZemaxError('MISSING_DEPENDENCY','原生图片格式转换需要reports依赖。')from exc
                with Image.open(source)as bitmap:bitmap.save(path)
        return dict(image_source="native",source_file=str(source),plotting_settings=None,
            artifacts=[dict(kind="native_image",path=str(path),image_source="native")])
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as exc:raise ZemaxError("MISSING_DEPENDENCY","绘图需要项目reports依赖。") from exc
    items=[("series",s) for s in result.get("series",[])]+[("grid",g) for g in result.get("grids",[])]+[("scatter",s) for s in result.get("scatter",[]) if s.get("points")]
    if not items and result.get("rows"):
        rows=[r for r in result["rows"] if r.get("metrics")]
        if rows:items=[("metrics",rows)]
    if not items:raise ZemaxError("NO_PLOTTABLE_DATA","结果没有可绘制的曲线、网格、散点或指标。")
    if request.item>=len(items):raise ZemaxError("INDEX_OUT_OF_RANGE","绘图数据编号越界。",count=len(items))
    kind,data=items[request.item]
    plot_settings=dict(item=request.item,data_kind=kind,width=request.width,height=request.height)
    with plt.rc_context({"font.family":"Microsoft YaHei","axes.unicode_minus":False}):
        fig,ax=plt.subplots(figsize=(request.width/100,request.height/100),dpi=100,layout="constrained")
        try:
            if kind=="series":
                for i,label in enumerate(data["labels"]):
                    if data.get('plot_kind')=='bar':
                        width=.8/len(data['labels'])
                        ax.bar([x-.4+width*(i+.5) for x in data['x']],[row[i] for row in data['y']],width=width,label=label)
                    else:ax.plot(data['x'],[row[i] for row in data['y']],label=label,marker='o' if data.get('point_labels') else None)
                if data.get('plot_kind')=='bar':
                    ax.set_xticks(data['x'],data.get('tick_labels',data['x']))
                    ax.set_frame_on(not data.get('suppress_frame',False))
                    plot_settings.update(plot_kind='bar',suppress_frame=data.get('suppress_frame',False))
                ax.set(xlabel=str(data.get("x_label","X"))+" ("+str(data.get("x_unit")or"单位见结果")+")",title=data.get("description",""));ax.legend();ax.grid(alpha=.25)
                if data.get('y_label'):ax.set_ylabel(data['y_label']+' ('+str(data.get('y_unit')or'单位见结果')+')')
                if data.get('axis_limits'):
                    ax.set_xlim(*data['axis_limits']);ax.set_ylim(*data['axis_limits'])
                    plot_settings['axis_limits']=data['axis_limits']
                if data.get('y_limits'):
                    ax.set_ylim(*data['y_limits']);plot_settings['y_limits']=data['y_limits']
                if data.get('aspect'):
                    ax.set_aspect(data['aspect'],adjustable='box');plot_settings['aspect']=data['aspect']
                for i,(x,y,label) in enumerate(zip(data['x'],data['y'],data.get('point_labels',[]))):
                    ax.annotate(label,(x,y[0]),xytext=(4,6 if i%2==0 else -12),textcoords='offset points')
            elif kind=="grid":
                values=np.asarray([[float("nan") if v is None else v for v in row] for row in data["values"]])
                extent=[data["min_x"]-.5*data["dx"],data["min_x"]+(data["nx"]-.5)*data["dx"],data["min_y"]-.5*data["dy"],data["min_y"]+(data["ny"]-.5)*data["dy"]]
                image=ax.imshow(values,origin="lower",extent=extent,aspect="auto")
                ax.set(xlabel=str(data.get("x_label","X"))+" ("+str(data.get("x_unit")or"单位见结果")+")",ylabel=str(data.get("y_label","Y"))+" ("+str(data.get("y_unit")or"单位见结果")+")",title=data.get("description",""))
                fig.colorbar(image,ax=ax,label=data.get("value_unit")or data.get("value_label")or"数值")
                plot_settings.update(extent=extent,origin="lower",array_order="values[y][x]",x_unit=data.get("x_unit"),y_unit=data.get("y_unit"),value_unit=data.get("value_unit"))
            elif kind=="scatter":
                points=data["points"]
                if any("value" in p for p in points):
                    image=ax.scatter([p["x"] for p in points],[p["y"] for p in points],c=[p.get("value",0) for p in points])
                    fig.colorbar(image,ax=ax)
                else:ax.scatter([p["x"] for p in points],[p["y"] for p in points])
                ax.set(xlabel=data.get("x_label","X"),ylabel=data.get("y_label","Y"))
                if data.get("x_axis_direction")=="decreasing_left_to_right":ax.invert_xaxis()
            else:
                for key in dict.fromkeys(m["key"] for row in data for m in row["metrics"]):
                    selected=[(r.get("index",i),m) for i,r in enumerate(data) for m in r["metrics"] if m["key"]==key]
                    ax.plot([x for x,m in selected],[m["value"] for x,m in selected],marker="o",label=key+" ("+str(selected[0][1].get("unit",""))+")")
                ax.set_xlabel("结果行号");ax.legend();ax.grid(alpha=.25)
            path.parent.mkdir(parents=True,exist_ok=True);fig.savefig(path,dpi=100)
        finally:plt.close(fig)
    return dict(image_source="data_plot",plotting_settings=plot_settings,
        artifacts=[dict(kind="plot",path=str(path),image_source="data_plot")])
