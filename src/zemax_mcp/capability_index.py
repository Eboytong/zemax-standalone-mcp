"""Offline, schema-derived capability discovery with explicit engineering metadata."""
import ast
import re
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from typing import Annotated, Literal

from .schema import Request


class CapabilitySearch(Request):
    query: Annotated[str, Field(min_length=1, max_length=300)]
    limit: Annotated[int, Field(strict=True, ge=1, le=50)] = 5
    category: Literal["all", "tool", "analysis"] = "all"


# Terms describe the implemented entry points; parameter contracts come from models.
METADATA = {
    "run_merit_program": ("评价函数 OPD 波前 目标 约束 预览 高斯积分", "OPD waves；几何为镜头单位", "有焦顺序模型；有效配置和波长", "副本预览；apply采用MFE并保留检查点", "实际MFE、节点、目标贡献及约束超限"),
    "design_desensitize": ("去敏感化 制造良率 固定公差 鲁棒设计 Monte Carlo", "请求准则单位", "有焦顺序模型；活动TDE；原生制造良率向导可用", "原生优化与验证后恢复源模型", "灵敏度、独立良率区间及优化模型"),
    "sequential_energy_budget": ("顺序能量 损耗 功率 逐面 透过率 截断 渐晕", "相对强度；可选W", "有焦顺序模型及带权偏振光线", "只读原生逐面追迹", "逐光线rows、逐面损耗及趋势series"),
    "manage_candidates": ("候选 设计 基线 分支 检查点 恢复 比较", "继承模型及评价单位", "创建/选择需要模型；list支持离线读取", "保存候选或选择恢复模型", "候选索引、设计差异及指标比较"),
    "run_candidate_evaluation": ("候选 公平比较 冻结评价 重载", "继承评价规格", "已保存候选和冻结评价合同", "串行评价并恢复当前模型", "候选指标rows及任务关联"),
    "get_glass_slots": ("玻璃 材料 槽位 可替换 镜片 胶合 目录", "当前镜头单位", "顺序模型及材料目录", "读取", "可替换材料段及跳过原因"),
    "update_surfaces": ("曲面建模 半径 厚度 材料 非球面 偏心 倾斜", "当前镜头长度单位", "已打开模型；检查solve/pickup", "修改曲面并增加修订", "实际曲面及属性回读"),
    "set_variables": ("优化变量 固定变量 求解 拾取 solve pickup", "各单元格原生单位", "已打开模型；替换solve须显式允许", "修改变量solve", "变量采用结果"),
    "get_surface_geometry": ("曲面几何 矢高 法线 最小间隔 镜片碰撞", "mm", "已打开模型", "读取", "几何及区间界限"),
    "run_batch_ray_trace": ("批量真实光线 交点 方向余弦 追迹", "当前镜头长度单位；方向余弦无量纲", "已打开模型；按请求坐标定义", "创建追迹任务", "逐光线rows和状态"),
    "polarization_ray_trace": ("偏振光线 电场 强度 Jones", "归一化强度及复电场", "顺序模型和偏振输入", "创建追迹任务", "光线强度和偏振状态"),
    "run_fft_mtf": ("调制传递函数 MTF 分辨率 像质 空间频率", "cycles/mm或cycles/mrad", "顺序系统；有焦/无焦频率单位匹配", "创建分析任务", "弧矢/子午series"),
    "wavefront": ("波前 光程差 OPD", "waves", "顺序模型及场/波长", "创建分析任务", "波前grids"),
    "zernike_standard": ("泽尼克 Zernike 像差系数 波前拟合", "waves", "顺序模型及瞳采样", "创建分析任务", "系数rows"),
    "rms_vs_focus": ("离焦 均方根 光斑 焦移 最佳焦点", "光斑µm；焦移为镜头单位", "有焦顺序模型", "创建分析任务", "RMS随焦移series"),
    "run_pop": ("物理光学 高斯光束 衍射传播 POP 复振幅", "镜头单位及功率", "顺序模型；有效光束定义或ZBF输入", "创建传播任务", "复场/强度grids及ZBF文件"),
    "get_coating_rta": ("镀膜 反射率 透射率 吸收率 S P 双向", "波长µm；角度degree；R/T/A无量纲", "曲面及可用镀膜", "读取", "原生双向S/P RTA"),
    "get_material_properties": ("玻璃 材料 折射率 色散 阿贝数 热光", "波长µm；折射率无量纲", "原生材料目录可用", "读取", "材料属性和目录身份"),
    "run_local_optimization": ("局部优化 阻尼最小二乘 DLS 正交下降", "评价函数单位", "已定义MFE及变量", "优化模型；创建任务", "目标前后值及模型"),
    "run_global_optimization": ("全局优化 多个极小值 搜索", "评价函数单位", "已定义MFE及变量", "优化模型；创建任务", "原生优化结果"),
    "run_optimization_wizard": ("评价函数 向导 高斯求积 矩形采样 RMS", "原生目标单位", "顺序模型", "修改MFE；创建任务", "向导设置及操作数"),
    "run_tolerance_analysis": ("公差 灵敏度 蒙特卡洛 Monte Carlo 良率", "TDE及评价量单位", "有效TDE、补偿及评价条件", "创建公差任务", "统计、样本与文件"),
    "run_nsc_ray_trace": ("非序列 非顺序 NSC 光源 探测器 散射 分光", "功率W及模型单位", "非顺序模型及光源/探测器", "更新探测器；创建任务", "探测器结果及ZRD"),
    "get_detector_data": ("探测器 照度 辐照度 功率 网格", "由探测器data_type确定", "非顺序模型；先执行追迹", "读取", "探测器grids/统计"),
    "read_zrd": ("光线数据库 ZRD 光线路径 段 分光", "模型单位及功率", "可用ZRD文件", "创建读取任务", "光线段rows"),
    "get_task_result": ("结果读取 分页 曲线 网格 行 rows series grids", "继承分析结果", "有效task_id及已产生结果", "读取", "分页结果和文件清单"),
    "export_analysis_image": ("绘图 导出 图片 PNG PDF 图像", "输出像素/页面单位", "可导出的分析任务及绘图依赖", "创建文件", "图像/PDF路径"),
    "run_layout_export": ("光路布局 二维 三维 折叠 展开", "模型单位", "模型及原生导出接口", "创建布局任务及文件", "原生布局图像"),
    "save_lens_as": ("保存 镜头 副本 模型 文件", "无", "已打开模型；绝对输出路径", "写模型文件", "保存路径"),
    "glass_trials": ("玻璃试验 材料替换 选型 候选 排名", "请求评价指标单位", "顺序模型及材料目录", "工作副本计算并恢复", "候选排名及最佳模型"),
    "system_drawing": ("系统图 光路图 折叠 展开 Unfold", "模型单位", "顺序模型及原生SystemDrawing", "创建分析任务", "原生图像文件"),
}


def _descriptions():
    """Read static docstrings without constructing an MCP server or native session."""
    tree = ast.parse(Path(__file__).with_name("server.py").read_text(encoding="utf-8"))
    return {node.name: ast.get_docstring(node) or "" for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


@lru_cache(maxsize=1)
def build_index():
    from .models import COMMAND_MODELS
    descriptions = _descriptions()
    result = []
    for name, model in COMMAND_MODELS.items():
        result.append(_entry(name, "tool", name, None, model.model_json_schema(), descriptions.get(name, "")))
    schema = COMMAND_MODELS["run_analysis"].model_json_schema()
    request = schema["properties"]["request"]
    for kind, ref in request["discriminator"]["mapping"].items():
        definition = schema["$defs"][ref.rsplit("/", 1)[-1]]
        result.append(_entry(kind, "analysis", "run_analysis", kind,
                             {**definition, "$defs": schema["$defs"]}, definition.get("description", "")))
    return result


def _entry(name, category, tool, kind, schema, description):
    metadata = METADATA.get(name)
    return dict(capability_id=f"{category}:{name}", name=name, category=category,
                tool_name=tool, analysis_kind=kind, description=description,
                aliases=metadata[0].split() if metadata else [],
                units=metadata[1] if metadata else "参见请求schema及结果unit字段",
                prerequisites=metadata[2] if metadata else "参见工具说明、请求schema和专题文档",
                effect=metadata[3] if metadata else ("创建分析任务" if kind else description),
                result=metadata[4] if metadata else "参见工具说明及任务结果",
                detailed=metadata is not None, adapted=True,
                availability={"static": "已适配", "native": "执行时按模型、资源及许可确认"},
                detail_request={"topic": "detail", "capability_id": f"{category}:{name}"},
                documentation="docs/README.md", request_schema=schema)


def _terms(text):
    text = text.casefold()
    words = re.findall(r"[a-z0-9_]+", text)
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        words.extend(run[i:i + 2] for i in range(max(1, len(run) - 1)))
    return set(words)


def search(query, limit=5, category="all"):
    terms = _terms(query)
    ranked = []
    for entry in build_index():
        if category != "all" and entry["category"] != category:
            continue
        names = _terms(entry["name"].replace("_", " ") + " " + " ".join(entry["aliases"]))
        description = _terms(entry["description"])
        hits = terms & (names | description)
        score = 4 * len(terms & names) + len(terms & description)
        if entry["name"].casefold() in query.casefold():
            score += 20
        if score:
            ranked.append((score, entry, sorted(hits)))
    ranked.sort(key=lambda item: (-item[0], item[1]["capability_id"]))
    return dict(query=query, total_matches=len(ranked), items=[
        {**{key: value for key, value in entry.items() if key != "request_schema"},
         "score": score, "matched_terms": hits} for score, entry, hits in ranked[:limit]])


def describe(req):
    from .errors import ZemaxError
    entries = build_index()
    if req.topic in {"detail", "dependencies"}:
        entry = next((item for item in entries if item["capability_id"] == req.capability_id), None)
        if entry is None:
            raise ZemaxError("UNKNOWN_CAPABILITY", "能力编号不存在。", capability_id=req.capability_id)
        if req.topic == "dependencies":
            return {key: entry[key] for key in ("capability_id", "prerequisites", "availability", "effect")}
        return entry
    selected = entries[req.start - 1:req.start - 1 + req.count]
    return dict(total=len(entries), start=req.start, count=len(selected),
                items=[{key: value for key, value in item.items() if key != "request_schema"} for item in selected])
