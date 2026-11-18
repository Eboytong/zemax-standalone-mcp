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
    category: Literal["all", "tool", "analysis", "action"] = "all"


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
    "run_spot_analysis": ("标准点列图 光斑图 光斑半径 standard spot diagram rms geo", "μm", "有焦顺序模型", "创建分析任务", "原生 RMS、GEO、参考点和文本"),
    "relative_illumination": ("相对照度 渐晕 relative illumination", "归一化照度", "有焦顺序模型", "创建分析任务", "随视场变化的相对照度数据"),
    "field_curvature_distortion": ("场曲 畸变 field curvature distortion", "原生轴及单位", "有焦顺序模型", "创建分析任务", "场曲和畸变曲线"),
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
    "export_analysis_image": ("绘图 导出 图片 PNG 图像 插图 配图 figure chart plot", "像素", "已有任务结果；重绘需 reports 依赖", "创建文件", "已保存原生图的副本或基于结果数据绘制的 PNG"),
    "run_layout_export": ("光路布局 镜头结构图 光路图 二维 三维 折叠 展开 lens layout optical layout cross section", "模型单位", "模型及原生导出接口", "创建布局任务及文件", "原生布局 PNG"),
    "save_lens_as": ("保存 镜头 副本 模型 文件", "无", "已打开模型；绝对输出路径", "写模型文件", "保存路径"),
    "glass_trials": ("玻璃试验 材料替换 选型 候选 排名", "请求评价指标单位", "顺序模型及材料目录", "工作副本计算并恢复", "候选排名及最佳模型"),
    "cancel_task": ("取消 正在执行 原生任务 停止", "无", "有效task_id", "请求取消", "实际任务终态"),
    "get_request_status": ("查询 超时 请求编号 request_id", "无", "有效请求编号", "读取", "执行回执和任务状态"),
    "update_merit_function": ("直接 编辑 评价函数 MFE 操作数 目标 权重", "原生操作数单位", "已打开模型", "修改MFE", "操作数回读"),
}

GROUPS = {
    'project': ('工程与材料 / Projects and materials', ('tool:open_lens', 'tool:save_lens_as', 'tool:create_archive', 'tool:get_material_properties')),
    'modeling': ('顺序和非序列建模 / Modeling', ('tool:update_surfaces', 'tool:update_nsc_objects', 'tool:update_configurations')),
    'tracing': ('追迹与传播 / Ray tracing and propagation', ('tool:run_batch_ray_trace', 'tool:run_nsc_ray_trace', 'tool:run_pop')),
    'analysis': ('成像与像质 / Image quality', ('tool:run_fft_mtf', 'tool:run_spot_analysis', 'analysis:relative_illumination', 'analysis:field_curvature_distortion')),
    'optimization': ('优化与候选 / Optimization and candidates', ('tool:run_local_optimization', 'tool:run_global_optimization', 'tool:manage_candidates')),
    'tolerancing': ('公差与制造 / Tolerancing and manufacturing', ('tool:run_tolerance_analysis', 'analysis:manufacturing_geometry')),
    'delivery': ('图像与交付 / Images and delivery', ('tool:run_layout_export', 'tool:export_analysis_image', 'tool:export_evaluation_report')),
    'service': ('能力发现与任务控制 / Discovery and tasks', ('tool:get_capabilities', 'tool:search_capabilities', 'tool:get_task_result')),
}

EXAMPLES = {
    'run_layout_export': {'request': {'kind': 'cross_section', 'path': r'C:\output\layout.png'}},
    'run_fft_mtf': {'maximum_frequency': 80, 'field': 0, 'wavelength': 0},
    'run_spot_analysis': {'field': 0, 'wavelength': 0, 'reference': 'Centroid'},
    'run_batch_ray_trace': {'request': {'rays': [{'wavelength': 1}, {'px': 0.5, 'wavelength': 1}]}},
    'export_analysis_image': {'request': {'task_id': '<task_id>', 'path': r'C:\output\analysis.png', 'source': 'data_plot'}},
}

ANALYSIS_DESCRIPTIONS = {
    'relative_illumination': '计算随视场角变化的归一化相对照度。',
    'field_curvature_distortion': '计算场曲和光学畸变，返回原生曲线和轴标签。',
}


def _group(item):
    for key, (_, ids) in GROUPS.items():
        if item['capability_id'] in ids:
            return key
    name = item['tool_name']
    if any(word in item['name'] for word in ('toleranc', 'yield', 'manufactur', 'desensitize')):
        return 'tolerancing'
    if item['category'] == 'analysis' or name == 'run_analysis':
        return 'analysis'
    if any(word in name for word in ('export', 'report', 'save_detector')):
        return 'delivery'
    if any(word in name for word in ('ray', 'pop', 'detector', 'beam', 'zrd')):
        return 'tracing'
    if any(word in name for word in ('optimiz', 'merit', 'variable', 'candidate', 'focus', 'scan', 'constraint')):
        return 'optimization'
    if any(word in name for word in ('system_settings', 'surface', 'configuration', 'nsc', 'editor', 'convert', 'operand', 'star', 'coating')):
        return 'modeling'
    if any(word in name for word in ('system', 'lens', 'archive', 'catalog', 'material', 'project', 'resource', 'glass', 'dependenc')):
        return 'project'
    return 'service'


def _descriptions():
    """Read static docstrings without constructing an MCP server or native session."""
    tree = ast.parse(Path(__file__).with_name("server.py").read_text(encoding="utf-8"))
    return {node.name: ast.get_docstring(node) or "" for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


@lru_cache(maxsize=1)
def build_index():
    from .models import COMMAND_MODELS
    from .disclosure import contracts, READ_ONLY
    from .schema_disclosure import reachable, select_branch
    from .readiness import contract
    descriptions = _descriptions()
    handlers = contracts()
    result = []
    for name, model in COMMAND_MODELS.items():
        schema = handlers[name].schema
        result.append(_entry(name, "tool", name, None, reachable(schema), descriptions.get(name, "")))
        request = schema.get('properties', {}).get('request', {})
        discriminator = request.get('discriminator', {})
        if discriminator.get('propertyName') == 'action':
            for action in discriminator['mapping']:
                item = _entry(name + ':' + action, 'action', name, None,
                    select_branch(schema, 'action', action), descriptions.get(name, ''))
                item['selector'] = ['action', action]
                result.append(item)
    schema = handlers["run_analysis"].schema
    request = schema["properties"]["request"]
    for kind, ref in request["discriminator"]["mapping"].items():
        definition = schema["$defs"][ref.rsplit("/", 1)[-1]]
        item = _entry(kind, "analysis", "run_analysis", kind,
                      select_branch(schema, 'kind', kind), definition.get("description", ""))
        item['selector'] = ['kind', kind]
        result.append(item)
    for item in result:
        item.update(contract(item['tool_name'], item['analysis_kind']))
        item['read_only'] = item['tool_name'] in READ_ONLY
        item['layer'] = ('optional_workflow' if item['name'] in {'glass_trials','design_desensitize','run_merit_program'}
            else 'service' if item['tool_name'] in {'manage_candidates','run_candidate_evaluation','get_task_result','get_task_status','search_capabilities','get_capabilities'}
            else 'native_action')
    return result


def _entry(name, category, tool, kind, schema, description):
    metadata = METADATA.get(name)
    if kind and not description:
        description = ANALYSIS_DESCRIPTIONS.get(kind, f'运行 OpticStudio 分析 {kind}，通过任务结果查看已保存数据。')
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


# Each concept supplies engineering vocabulary and its implemented entry points.
CONCEPTS = (
    (("加工误差", "制造误差", "装配误差", "合格率", "成品率"),
     "公差 蒙特卡洛 良率", ("tool:run_tolerance_analysis", "analysis:design_desensitize")),
    (("清晰度", "清晰程度", "有多清楚", "分辨能力", "成像质量"),
     "MTF 调制传递函数 光斑 像质", ("tool:run_fft_mtf", "tool:run_spot_analysis")),
    (("光电接收面", "感光面", "接收屏", "传感器照度"),
     "探测器 辐照度 功率", ("tool:get_detector_data",)),
    (("杂散光", "追踪散射", "散射追迹"),
     "非序列 散射 分光 追迹", ("tool:run_nsc_ray_trace",)),
    (("波前", "光程差", "opd"), "波前 OPD", ("analysis:wavefront",)),
    (("保存候选", "存为候选", "候选设计", "设计检查点"),
     "候选 检查点 保存", ("tool:manage_candidates", "action:manage_candidates:create")),
    (("反射透射", "反射和透射", "镀膜损耗"),
     "镀膜 反射率 透射率 吸收率", ("tool:get_coating_rta",)),
    (("先前算过", "以前的结果", "历史计算"),
     "历史 任务 结果", ("tool:get_historical_result", "tool:list_task_history")),
)
GENERIC_TERMS = _terms("镜头 计算 分析 读取 查询 检查 查看 设置 系统 结果 模型 工具")


def _expand(query):
    folded = query.casefold()
    expansions, preferred = [], set()
    for phrases, vocabulary, capabilities in CONCEPTS:
        if any(phrase in folded for phrase in phrases):
            expansions.extend(vocabulary.split())
            preferred.update(capabilities)
    return list(dict.fromkeys(expansions)), preferred


def _rank(query, category):
    expanded, preferred = _expand(query)
    terms = _terms(query)
    expanded_terms = _terms(" ".join(expanded)) - terms
    ranked = []
    folded = query.casefold()
    for entry in build_index():
        if category != "all" and entry["category"] != category:
            continue
        names = _terms(entry["name"].replace("_", " ") + " " + " ".join(entry["aliases"]))
        if entry['name'] == 'update_surfaces': names |= _terms('Gradient2 Gradient3 GRIN surface')
        if entry['name'] == 'run_layout_export': names |= _terms('system drawing unfold rays')
        description = _terms(entry["description"])
        hits = terms & (names | description)
        if not (hits - GENERIC_TERMS or expanded_terms & (names | description)
                or entry['capability_id'] in preferred or entry['name'].casefold() in folded):
            continue
        score = sum(1 if term in GENERIC_TERMS else 4 for term in terms & names)
        score += sum(.25 if term in GENERIC_TERMS else 1 for term in terms & description)
        extra_hits = expanded_terms & (names | description)
        score += 2 * len(expanded_terms & names) + .5 * len(expanded_terms & description)
        if entry["capability_id"] in preferred:
            score += 30
        if re.search(r"(?<![a-z0-9_])" + re.escape(entry["name"].casefold()) + r"(?![a-z0-9_])", folded):
            score += 100
        if entry["capability_id"].casefold() in folded:
            score += 1000
        if score:
            ranked.append((score, entry, sorted(hits | extra_hits)))
    ranked.sort(key=lambda item: (-item[0], item[1]["capability_id"]))
    return ranked, expanded


def search(query, limit=5, category="all"):
    parts = list(dict.fromkeys(part.strip() for part in re.split(
        r"(?:然后|之后|接着|同时|并且|再|[；;，,。]|\bthen\b|\band\s+then\b)", query,
        flags=re.IGNORECASE) if part.strip())) or [query]
    ranked, expanded = _rank(query, category)
    selections, seen, intents = [], set(), []
    folded = query.casefold()
    figure_domains = (
        (('镜头结构图', '光路布局', '光路图', '布局图', 'lens layout', 'optical layout', 'cross section'), 'tool:run_layout_export'),
        (('mtf', '调制传递函数'), 'tool:run_fft_mtf'),
        (('点列图', '光斑图', 'spot diagram', 'spot plot'), 'tool:run_spot_analysis'),
    )
    figure_ids = [cid for terms, cid in figure_domains if any(term in folded for term in terms)]
    report = any(term in folded for term in ('报告', '配图', '插图', '出图', 'report', 'figure'))
    if (figure_ids and report) or len(figure_ids) > 1:
        figure_ids.append('tool:export_analysis_image')
    elif report and any(term in folded for term in ('像质图', '图像', '配图', 'figure', 'image')):
        figure_ids = ['tool:export_analysis_image']
    else:
        figure_ids = []
    index = {item['capability_id']: item for item in build_index()}
    exact = [row for row in ranked if row[1]['capability_id'] in folded]
    for row in [*exact, *((30, index[cid], []) for cid in figure_ids if category in ('all', 'tool'))]:
        cid = row[1]['capability_id']
        if cid not in seen and len(selections) < limit:
            selections.append(row)
            seen.add(cid)
    explicit_delete = any(word in folded for word in ('删除', '删掉', '移除', 'delete', 'remove'))
    if report and not explicit_delete:
        ranked = [row for row in ranked if not row[1]['tool_name'].startswith('delete_')]
    if len(parts) > 1:
        for part in parts:
            candidates, additions = _rank(part, category)
            if report and not explicit_delete:
                candidates = [row for row in candidates if not row[1]['tool_name'].startswith('delete_')]
            expanded.extend(additions)
            intents.append(dict(query=part, capability_ids=[row[1]['capability_id'] for row in candidates[:limit]]))
            candidate = next((row for row in candidates if row[1]['capability_id'] not in seen), None)
            if candidate and len(selections) < limit:
                selections.append(candidate)
                seen.add(candidate[1]['capability_id'])
        # Include candidates found only by a sub-intent in the final union.
        union = {row[1]['capability_id']: row for row in ranked}
        for part in parts:
            for row in _rank(part, category)[0]:
                if report and not explicit_delete and row[1]['tool_name'].startswith('delete_'):
                    continue
                old = union.get(row[1]['capability_id'])
                if old is None or row[0] > old[0]: union[row[1]['capability_id']] = row
        ranked = sorted(union.values(), key=lambda row: (-row[0], row[1]['capability_id']))
    for row in ranked:
        if len(selections) >= limit: break
        if row[1]['capability_id'] not in seen:
            selections.append(row)
            seen.add(row[1]['capability_id'])
    result = dict(query=query, total_matches=len({row[1]['capability_id'] for row in ranked} | seen), items=[
        {**brief(entry), **usage(entry), "score": score, "matched_terms": hits} for score, entry, hits in selections])
    if intents: result['intents'] = intents
    expanded = list(dict.fromkeys(expanded))
    if expanded: result['expanded_terms'] = expanded
    retry_queries = parts if intents else [" ".join(expanded)] if expanded else []
    if retry_queries:
        result['retry_requests'] = [dict(query=text[:300], limit=limit, category=category)
                                    for text in retry_queries[:2]]
    return result


def describe(req):
    from .errors import ZemaxError
    entries = build_index()
    if req.topic == 'overview':
        return dict(total=len(entries), groups=[
            dict(id=key, title=title, count=sum(_group(entry) == key for entry in entries), capability_ids=list(ids))
            for key, (title, ids) in GROUPS.items()], index_request=dict(topic='index', start=1, count=20))
    if req.topic in {"detail", "dependencies"}:
        entry = next((item for item in entries if item["capability_id"] == req.capability_id), None)
        if entry is None:
            raise ZemaxError("UNKNOWN_CAPABILITY", "能力编号不存在。", capability_id=req.capability_id)
        if req.topic == "dependencies":
            return {key: entry[key] for key in ("capability_id", "prerequisites", "availability", "effect",
                                                "requirements", "produces", "preflight_profiled")}
        from .schema_disclosure import select_branch, restrict_analyses
        result = dict(entry)
        if req.action:
            result['request_schema'] = select_branch(result['request_schema'], 'action', req.action)
        if req.analysis_kinds:
            result['request_schema'] = restrict_analyses(result['request_schema'], req.analysis_kinds)
        if not req.include_metadata:
            result = {key: result[key] for key in ('capability_id','tool_name','analysis_kind','description',
                'units','prerequisites','effect','result','read_only','layer','request_schema',
                'requirements','produces','preflight_profiled')}
        return {**result, **usage(entry)}
    selected = entries[req.start - 1:req.start - 1 + req.count]
    return dict(total=len(entries), start=req.start, count=len(selected),
                items=[brief(item) for item in selected])


def brief(item):
    return {key: item[key] for key in ('capability_id', 'name', 'category', 'description', 'effect', 'read_only', 'layer', 'detail_request')}


def usage(item):
    tool = item['tool_name']
    value = dict(call='query_capability' if item['read_only'] else 'execute_capability',
                 prerequisites=item['prerequisites'], result=item['result'])
    if tool in EXAMPLES:
        value['example'] = dict(capability_id=item['capability_id'], arguments=EXAMPLES[tool])
    if tool == 'run_spot_analysis':
        value['next_capabilities'] = ['tool:run_batch_ray_trace', 'tool:export_analysis_image']
    if tool in {'run_fft_mtf', 'run_batch_ray_trace'}:
        value['next_capabilities'] = ['tool:export_analysis_image']
    return value
