"""Offline plots and PDF generated solely from saved task results."""
import csv,json,shutil
from html import escape
from pathlib import Path
from .data import clean
from .errors import ZemaxError

PDF_ROW_LIMIT=200


def pdf_preview(value):
    """Keep nested metadata previews bounded and identify every omitted list."""
    if isinstance(value,dict):return {k:pdf_preview(v)for k,v in value.items()}
    if isinstance(value,list):
        if len(value)>12:return dict(total_items=len(value),preview=[pdf_preview(v)for v in value[:12]],
            omitted_items=len(value)-12,full_data="results.json")
        return [pdf_preview(v)for v in value]
    return value

def report_assets(folder,results,title,charts,pdf):
    artifacts=[];figures=[]
    plt=None
    if charts:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            plt.rcParams["font.family"]="Microsoft YaHei"
            plt.rcParams["axes.unicode_minus"]=False
        except ImportError as exc:raise ZemaxError("MISSING_DEPENDENCY","图表需要安装项目 reports 依赖。") from exc
    for item in results:
        task_id=item["task_id"];r=item["result"]
        for artifact in r.get("artifacts",[]):
            if artifact.get("kind")in {"beam","intermediate_beam"}:
                from .beam_files import iter_beam_samples
                original=Path(artifact["path"])
                path=folder/(task_id+"_"+original.stem+"_field.csv")
                with path.open("w",encoding="utf-8-sig",newline="")as stream:
                    writer=csv.DictWriter(stream,fieldnames=["index","ix","iy","x","y","length_unit","ex_real","ex_imag","ey_real","ey_imag"])
                    writer.writeheader();writer.writerows(iter_beam_samples(original,include_coordinates=True))
                artifacts.append(dict(kind="csv",path=str(path),quantity="complex field in native file order",source_file=str(original)))
            if artifact.get("kind")=="native_image":
                original=Path(artifact["path"])
                if not original.is_file():raise ZemaxError("MISSING_ARTIFACT","已保存的原生图片不存在。",path=str(original))
                saved=folder/(task_id+"_"+original.name)
                shutil.copy2(original,saved)
                artifacts.append(dict(kind="native_image",path=str(saved)))
                figures.append(saved)
        if r.get("rows"):
            path=folder/(task_id+"_rows.csv")
            columns=list(dict.fromkeys(k for row in r["rows"]for k in row))
            with path.open("w",encoding="utf-8-sig",newline="")as stream:
                writer=csv.writer(stream);writer.writerow(columns)
                for row in r["rows"]:
                    writer.writerow([json.dumps(clean(row[k]),ensure_ascii=False)if isinstance(row.get(k),(dict,list))else row.get(k)for k in columns])
            artifacts.append(dict(kind="csv",path=str(path)))
        if plt:
            for index,scatter in enumerate(r.get('scatter',[])):
                points=scatter['points']
                fig,ax=plt.subplots(figsize=(6,4),layout='constrained')
                try:
                    image=ax.scatter([p['x']for p in points],[p['y']for p in points],c=[p.get('value',0)for p in points])
                    ax.set(xlabel=scatter['x_label'],ylabel=scatter['y_label'],title=scatter['description'])
                    fig.colorbar(image,ax=ax)
                    png=folder/(task_id+f'_scatter{index}.png');fig.savefig(png,dpi=180);figures.append(png)
                finally:plt.close(fig)
        for s in r.get("series",[]):
            path=folder/(task_id+f"_series{s['series']}.csv")
            with path.open("w",encoding="utf-8-sig",newline="") as f:
                writer=csv.writer(f);writer.writerow([s["x_label"],*s["labels"]]);writer.writerows([x,*y]for x,y in zip(s["x"],s["y"]))
            artifacts.append(dict(kind="csv",path=str(path)))
            if plt:
                fig,ax=plt.subplots(figsize=(7,4),layout="constrained")
                for j,label in enumerate(s["labels"]):ax.plot(s["x"],[row[j] for row in s["y"]],label=label)
                xlabel=(s["x_label"]if s["x_label"]not in {"None",""}else "原生横轴")+f" ({s.get('x_unit','单位见分析设置')})"
                ax.set(xlabel=xlabel,title=s["description"]);ax.grid(alpha=.25);ax.legend(fontsize=8)
                png=path.with_suffix(".png");fig.savefig(png,dpi=180);plt.close(fig);figures.append(png)
        for g in r.get("grids",[]):
            if g.get("pupil_mapping"):
                mapping=g["pupil_mapping"];mapping_file=folder/(task_id+f"_grid{g['grid']}_pupil_mapping.csv")
                with mapping_file.open("w",encoding="utf-8-sig",newline="")as f:
                    writer=csv.writer(f);writer.writerow(["ix","iy","px","py","valid","reason","mapping_status","coordinate_error","error_unit","iterations","opd_error_waves"])
                    for iy,row in enumerate(mapping["points"]):
                        for ix,point in enumerate(row):writer.writerow([ix,iy,point["px"],point["py"],point["valid"],point["reason"],mapping["status"],point.get("coordinate_error",mapping.get("coordinate_error")),point.get('error_unit'),point.get('iterations'),point.get('opd_error_waves')])
                artifacts.append(dict(kind="csv",path=str(mapping_file),quantity="pupil coordinate mapping and validity"))
            path=folder/(task_id+f"_grid{g['grid']}.csv")
            with path.open("w",encoding="utf-8-sig",newline="") as f:csv.writer(f).writerows(g["values"])
            artifacts.append(dict(kind="csv",path=str(path)))
            coordinate_file=folder/(task_id+f"_grid{g['grid']}_coordinates.csv")
            with coordinate_file.open("w",encoding="utf-8-sig",newline="")as f:
                writer=csv.writer(f);writer.writerow(["x","y","z","value","x_unit","y_unit","z_unit","value_unit"])
                for iy,row in enumerate(g["values"]):
                    for ix,value in enumerate(row):writer.writerow([g["min_x"]+ix*g["dx"],g["min_y"]+iy*g["dy"],g.get("z_coordinate"),value,g.get("x_unit"),g.get("y_unit"),g.get("z_unit"),g.get("value_unit")])
            artifacts.append(dict(kind="csv",path=str(coordinate_file)))
            if plt:
                fig,ax=plt.subplots(figsize=(6,4),layout="constrained")
                import numpy as np
                values=np.array([[float("nan")if v is None else v for v in row]for row in g["values"]])
                im=ax.imshow(values,origin="lower",extent=[g["min_x"]-.5*g["dx"],g["min_x"]+(g["nx"]-.5)*g["dx"],g["min_y"]-.5*g["dy"],g["min_y"]+(g["ny"]-.5)*g["dy"]],aspect="auto")
                ax.set(xlabel=(g["x_label"]if g["x_label"]not in {"None",""}else"X")+f" ({g.get('x_unit','原生网格坐标')})",ylabel=(g["y_label"]if g["y_label"]not in {"None",""}else"Y")+f" ({g.get('y_unit','原生网格坐标')})",title=g["description"]);fig.colorbar(im,ax=ax,label=g["value_label"]if g["value_label"]not in {"None",""}else g.get("value_unit","原生数值（单位见结果原文）"))
                png=path.with_suffix(".png");fig.savefig(png,dpi=180);plt.close(fig);figures.append(png)
    for p in figures:
        if not any(a["path"]==str(p)for a in artifacts):artifacts.append(dict(kind="plot",path=str(p),image_source="data_plot"))
    if pdf:
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,PageBreak
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.pagesizes import A4
        except ImportError as exc:raise ZemaxError("MISSING_DEPENDENCY","PDF 需要安装项目 reports 依赖。") from exc
        if "ZemaxChinese"not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont("ZemaxChinese",r"C:\Windows\Fonts\msyh.ttc",subfontIndex=0))
        body=ParagraphStyle("body",fontName="ZemaxChinese",fontSize=8,leading=12,wordWrap="CJK",spaceAfter=4)
        heading=ParagraphStyle("heading",parent=body,fontSize=14,leading=20,spaceAfter=10)
        story=[Paragraph(escape(title),heading),Paragraph("根据已保存结果生成。完整设置、数据和失败信息见同目录 results.json。",body)]
        row_previews=[]
        for item in results:
            r=item["result"]
            story.append(Spacer(1,8));story.append(Paragraph("任务 "+escape(item["task_id"]),heading))
            for key in ("task","context","system_settings","baseline","restoration","error","artifacts","native_preamble","unavailable_trace_tasks","coupling_definition"):
                if r.get(key)is not None:
                    story.append(Paragraph(escape(key),body))
                    for line in json.dumps(pdf_preview(clean(r[key])),ensure_ascii=False,indent=2).splitlines():story.append(Paragraph(escape(line),body))
            if r.get("metrics")is not None:story.append(Paragraph(escape(json.dumps(clean(r["metrics"]),ensure_ascii=False)),body))
            rows=r.get("rows",[])
            shown=min(len(rows),PDF_ROW_LIMIT)
            preview=dict(task_id=item["task_id"],total_rows=len(rows),shown_rows=shown,
                         omitted_rows=len(rows)-shown,truncated=len(rows)>shown,
                         full_data_files=["results.json",item["task_id"]+"_rows.csv"]if rows else["results.json"])
            row_previews.append(preview)
            if rows:
                notice=f"逐行结果共 {len(rows)} 行，展示前 {shown} 行。"
                if preview["truncated"]:
                    notice+=f" PDF 预览已截断，省略 {preview['omitted_rows']} 行。"
                notice+=f"完整逐行数据：results.json 和 {item['task_id']}_rows.csv。"
                story.append(Paragraph(escape(notice),body))
                columns=r.get("summary",{}).get("columns")
                if columns:
                    story.append(Paragraph("values 的列定义（按零起始序号排列）："+escape(json.dumps(clean(columns),ensure_ascii=False)),body))
            for row in rows[:PDF_ROW_LIMIT]:
                story.append(Paragraph(escape(json.dumps(clean(row),ensure_ascii=False)),body))
            if r.get("summary"):
                summary={k:v for k,v in r["summary"].items()if k not in {"system_settings","task"}}
                for line in json.dumps(pdf_preview(clean(summary)),ensure_ascii=False,indent=2).splitlines():story.append(Paragraph(escape(line),body))
        for p in figures:
            story.extend([PageBreak(),Paragraph(escape(p.stem),body),Image(str(p),width=480,height=300,kind="proportional")])
        path=folder/"report.pdf"
        def footer(canvas,doc):
            canvas.setFont("ZemaxChinese",8);canvas.drawRightString(A4[0]-36,22,str(doc.page))
        SimpleDocTemplate(str(path),pagesize=A4,rightMargin=36,leftMargin=36,topMargin=36,bottomMargin=36).build(story,onFirstPage=footer,onLaterPages=footer)
        artifacts.append(dict(kind="pdf",path=str(path),row_previews=row_previews))
    return artifacts


def export_saved_report(folder,results,title,charts,formats):
    json_path, csv_path, md_path = folder/"results.json", folder/"metrics.csv", folder/"report.md"
    json_path.write_text(json.dumps(clean(results), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    lines = ["# " + title.replace("\n", " "), "", "[完整 JSON](results.json) · [指标 CSV](metrics.csv)", ""]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["task", "index", "input", "state", "metric", "value", "unit", "error"])
        for item in results:
            result = item["result"]
            lines += ["## 任务 " + item["task_id"], "", "```json", json.dumps(clean({
                k: result.get(k) for k in ("task", "context", "system_settings", "baseline", "summary", "restoration", "error", "artifacts", "unavailable_trace_tasks", "coupling_definition")}), ensure_ascii=False, indent=2), "```", ""]
            for row in result.get("rows", []):
                for metric in row.get("metrics") or [{}]:
                    writer.writerow([item["task_id"], row.get("index"), row.get("value", row.get("path")),
                        row.get("state"), metric.get("key"), metric.get("value"), metric.get("unit"),
                        json.dumps(row.get("error"), ensure_ascii=False)])
            lines += ["| 项目 | 输入 | 状态 | 指标 | 数值 | 单位 |", "| --- | --- | --- | --- | --- | --- |"]
            for row in result.get("rows", []):
                for metric in row.get("metrics") or [{}]:
                    values = [row.get("index"), row.get("value", row.get("path")), row.get("state"),
                              metric.get("key", row.get("error", {})), metric.get("value"), metric.get("unit")]
                    lines.append("| " + " | ".join(str(v).replace("|", " / ").replace("\\n", " ") for v in values) + " |")
            history=[dict(detector=row.get("detector"), trace_conditions=row["trace_conditions"],
                loaded_sources=row.get("loaded_sources",[]),
                history_known=row.get("history_known"), trace_options_known=row.get("trace_options_known"),
                mixed_conditions=row.get("mixed_conditions"), complete=row.get("complete"))
                for row in result.get("rows",[]) if "trace_conditions" in row]
            if history:
                lines += ["", "### 累计探测器来源", "", "```json",
                    json.dumps(clean(history),ensure_ascii=False,indent=2), "```"]
            lines += ["", "逐项实际分析条件见完整 JSON；失败项不参与性能改善判断。", ""]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    assets=report_assets(folder,results,title,charts,"pdf" in formats)
    if assets:
        with md_path.open("a",encoding="utf-8") as f:
            f.write("\n## 数据与图表\n\n")
            for a in assets:
                name=Path(a["path"]).name
                f.write(f"{'!'if a['kind']in {'plot','native_image'}else ''}[{name}]({name})\n\n")
    return {"artifacts": [{"kind": kind, "path": str(path)} for kind, path in
                          (("markdown", md_path), ("json", json_path), ("csv", csv_path))]+assets}
