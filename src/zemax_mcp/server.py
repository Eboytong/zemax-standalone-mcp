from contextlib import asynccontextmanager
from typing import Literal

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from . import __version__
from .bridge import Bridge
from .models import ArchiveLoad, ArchiveSave, Dependencies, ProjectPatch, SaveLens, OpenLens, SystemResources, CopySurfaces, SurfaceGeometry, BatchRays, ParameterScan, BatchEvaluation, Index, Operand, OperandUpdate, SurfacePatch, SystemPatch, ToolResponse, Variable
from pydantic import StrictInt
from .analysis_models import AnalysisRequest
from .configuration_models import ConfigurationRange, ConfigurationPatch, GlobalOptimization
from .models import ConfigurationEvaluation, Multistart
from .models import ConfigurationVariable,ObjectVariable
from .editor_models import EditorMetadata,EditorInsert,EditorCopy
from .design_models import DesignRequest, DesignToolOptions
from .wizard_models import WizardRequest, WizardOptions
from .catalog_models import CatalogSearch, CatalogLens
from .models import CatalogEvaluation
from .history_models import TaskHistory, HistoricalResult, RequestStatus
from .coating_models import CoatingLayerRange,CoatingLayerUpdate,CoatingRta
from .material_models import MaterialProperties
from .conversion_models import NscConversion
from .nsc_models import ObjectGeometry
from .star_models import StarRead, StarOperation
from .hpc_models import HpcSelection
from .speos_models import SpeosExport
from .point_cloud import PointCloudExport
from .tolerance_models import ToleranceRange,TolerancePatch,ToleranceWizard,ToleranceAnalysis,ToleranceSummary
from .nsc_models import ObjectRange,ObjectInsert,ObjectCopy,ObjectUpdates,DetectorClear,DetectorRead,NscTrace,ZrdRead,ZrdReplay
from .pop_models import Pop,BeamRead,PopConvergence
from .export_models import CadExport,LayoutExport
from .nsc_models import DetectorSave,DetectorLoad
from .export_models import AnalysisImage
from .macro_models import StandaloneMacro
from .candidate_models import CandidateAction, CandidateEvaluation
from .merit_program import MeritProgram


def create_server():
    bridge = Bridge()

    @asynccontextmanager
    async def lifespan(server):
        try:
            yield bridge
        finally:
            await bridge.close()

    server = MCPServer(
        "Zemax Standalone", version=__version__, lifespan=lifespan,
        instructions="本机 OpticStudio 2024 R2 Standalone。先 connect，再打开或新建镜头。修改前检查单位与 solve/pickup。run_* 返回任务编号，通过状态与结果工具取回结果。",
    )

    def tool(fn):
        read_only = fn.__name__.startswith(("get_", "list_", "search_")) or fn.__name__ == "compare_results"
        return server.tool(
            structured_output=True,
            annotations=ToolAnnotations(readOnlyHint=read_only, destructiveHint=not read_only,
                                        idempotentHint=read_only, openWorldHint=False),
        )(fn)

    async def call(command, arguments=None):
        return ToolResponse.model_validate(await bridge.request(command, arguments))

    @tool
    async def connect(install_dir: str | None = None) -> ToolResponse:
        """创建或复用本服务的后台实例，检查许可；默认使用本机已安装的 2024 R2。"""
        return await call("connect", {"install_dir": install_dir})

    @tool
    async def get_status() -> ToolResponse:
        """读取连接、模型修订与当前任务状态；任务超时不能视为原生计算停止。"""
        return await call("get_status")

    @tool
    async def get_capabilities(topic: Literal["all", "settings", "tool", "merit_cells", "optimization_diagnostics", "index", "detail", "dependencies"] = "all",
                               tool_name: str | None = None, start: int = 1, count: int = 20,
                               capability_id: str | None = None) -> ToolResponse:
        """列出已实现工具、模式、面型及当前版本可用的设置枚举。"""
        return await call("get_capabilities", dict(topic=topic,tool_name=tool_name,start=start,count=count,capability_id=capability_id))

    @tool
    async def search_capabilities(query: str, limit: int = 5,
                                  category: Literal["all", "tool", "analysis"] = "all") -> ToolResponse:
        """离线检索中文工程需求，返回工具/分析kind、匹配词及详情入口；无需连接OpticStudio。"""
        return await call("search_capabilities", dict(query=query, limit=limit, category=category))

    @tool
    async def new_system(mode: Literal["Sequential","NonSequential"] = "Sequential") -> ToolResponse:
        """保存当前检查点并新建顺序系统，建立项目输出目录中的工作副本。"""
        return await call("new_system",dict(mode=mode))

    @tool
    async def manage_candidates(request: CandidateAction) -> ToolResponse:
        """创建设计基线、分支、具名检查点、选择/恢复及比较；list可在重启后读取持久索引。"""
        return await call("manage_candidates", {"request": request.model_dump()})

    @tool
    async def run_candidate_evaluation(request: CandidateEvaluation) -> ToolResponse:
        """独立重载候选，按冻结评价合同串行求值并恢复原模型；返回任务编号。"""
        return await call("run_candidate_evaluation", request.model_dump())

    @tool
    async def get_glass_slots() -> ToolResponse:
        """从当前顺序模型读取可替换材料段、目录身份及受solve/面型限制的跳过原因。"""
        return await call("get_glass_slots")

    @tool
    async def open_lens(path: str) -> ToolResponse:
        """读取 .zos/.zmx 并建立工作副本；path 使用绝对路径，输入文件保持只读。"""
        return await call("open_lens", {"path": path})

    @tool
    async def save_lens_as(path: str, overwrite: bool = False) -> ToolResponse:
        """保存设计副本到绝对路径；覆盖现有文件须显式设置 overwrite。"""
        return await call("save_lens_as", {"path": path, "overwrite": overwrite})

    @tool
    async def disconnect() -> ToolResponse:
        """保存检查点并关闭本服务创建的后台实例；有运行任务时先完成或取消。"""
        return await call("disconnect")

    @tool
    async def get_system_summary() -> ToolResponse:
        """读取单位、视场、波长、环境、结构编号与一阶光学数据。"""
        return await call("get_system_summary")

    @tool
    async def get_system_settings() -> ToolResponse:
        """读取实际系统设置；波长单位始终是当前环境空气参考下的 μm。"""
        return await call("get_system_settings")

    @tool
    async def update_system_settings(settings: SystemPatch) -> ToolResponse:
        """修改系统设置并回读；只传需修改字段。fields/wavelengths 替换整组，550 nm 使用 wavelength_um=0.55。"""
        return await call("update_system_settings", settings.model_dump(exclude_unset=True))

    @tool
    async def get_surfaces(start: Index = 0, count: StrictInt = 50, parameter_start: StrictInt = 1, parameter_count: StrictInt = 20) -> ToolResponse:
        """分页读取曲面、参数和 solve/pickup；曲面从 0（物面）开始，count=1..200。"""
        return await call("get_surfaces", {"start": start, "count": count,"parameter_start":parameter_start,"parameter_count":parameter_count})

    @tool
    async def update_surfaces(changes: list[SurfacePatch]) -> ToolResponse:
        """批量修改曲面，几何值使用当前镜头单位；solve/pickup 默认受保护，Infinity 表示无限半径。"""
        return await call("update_surfaces", {"changes": [x.model_dump(exclude_unset=True) for x in changes]})

    @tool
    async def insert_surfaces(at: StrictInt, count: StrictInt = 1) -> ToolResponse:
        """在指定曲面前插入标准面，at 从 1 开始且不超过像面编号。"""
        return await call("insert_surfaces", {"at": at, "count": count})

    @tool
    async def delete_surfaces(at: StrictInt, count: StrictInt = 1) -> ToolResponse:
        """删除物面和像面之间的指定曲面；操作前保存检查点。"""
        return await call("delete_surfaces", {"at": at, "count": count})

    @tool
    async def get_variables() -> ToolResponse:
        """列出顺序系统当前曲面优化变量及其数值。"""
        return await call("get_variables")

    @tool
    async def set_variables(variables: list[Variable|ConfigurationVariable|ObjectVariable]) -> ToolResponse:
        """按曲面和 cell 设置或固定变量；替换已有 solve/pickup 需显式允许。"""
        return await call("set_variables", {"variables": [x.model_dump() for x in variables]})

    @tool
    async def get_merit_function(start: StrictInt = 1, count: StrictInt = 100) -> ToolResponse:
        """分页读取评价函数及操作数字段；编号从 1 开始，value 为上次计算值。"""
        return await call("get_merit_function", {"start": start, "count": count})

    @tool
    async def update_merit_function(
        mode: Literal["replace", "append", "update", "delete", "rms_spot_wizard"], operands: list[Operand] | None = None,
        reference: Literal["Centroid", "ChiefRay"] = "Centroid", rings: int = 3,
        updates: list[OperandUpdate] | None = None, operand_numbers: list[StrictInt] | None = None,
    ) -> ToolResponse:
        """替换/追加评价函数、按行 update/delete，或生成 RMS spot 向导。updates 按 operand 编号修改；删除用 operand_numbers。parameters 是原生列号2..9，先按header和data_type核对；曲面范围列必须为整数，MNEG/MNCT等边界阈值写target，不写面号列。多配置replace须以显式CONF行开头，CONF仅指定parameters并省略target/weight。最终回读拒绝静默改写；失败含部分修改明细时先回读，勿盲目重复追加。"""
        return await call("update_merit_function", {"mode": mode, "operands": [x.model_dump(exclude_unset=True) for x in operands or []],
                          "reference": reference, "rings": rings,
                          "updates": [x.model_dump(exclude_unset=True) for x in updates or []], "operand_numbers": operand_numbers or []})

    @tool
    async def evaluate_merit_function() -> ToolResponse:
        """计算当前评价函数并返回操作数结果；权重目标须结合独立像质分析解释。"""
        return await call("evaluate_merit_function")

    @tool
    async def run_quick_focus(
        criterion: Literal["SpotSizeRadial", "SpotSizeXOnly", "SpotSizeYOnly", "RMSWavefront"],
        use_centroid: bool, replace_solve: bool = False,
    ) -> ToolResponse:
        """按显式 RMS 准则调整像面前一面的厚度；返回任务编号，其最佳焦点不等于最高 MTF。"""
        return await call("run_quick_focus", {"criterion": criterion, "use_centroid": use_centroid, "replace_solve": replace_solve})

    @tool
    async def run_fft_mtf(
        maximum_frequency: float = 50, sampling: str = "S_128x128", field: Index = 0,
        wavelength: Index = 0, frequency_unit: Literal["CyclesPerMillimeter", "CyclesPerMilliradian"] = "CyclesPerMillimeter",
        use_polarization: bool = False,
    ) -> ToolResponse:
        """启动有焦 FFT MTF，返回任务编号。field/wavelength=0 为全部/多色；频率单位须与系统一致，结果附轴与曲线标签。"""
        return await call("run_fft_mtf", dict(maximum_frequency=maximum_frequency, sampling=sampling, field=field, wavelength=wavelength, frequency_unit=frequency_unit, use_polarization=use_polarization))

    @tool
    async def run_spot_analysis(
        reference: Literal["ChiefRay", "Centroid", "Middle", "Vertex"], field: Index = 0,
        wavelength: Index = 0, pattern: Literal["Square", "Hexapolar"] = "Hexapolar",
        ray_density: StrictInt = 6, use_polarization: bool = False,
    ) -> ToolResponse:
        """启动原生标准点列图，返回任务编号；显式指定参考点，保留采样、权重条件、RMS/GEO 和原生文本。"""
        return await call("run_spot_analysis", dict(reference=reference, field=field, wavelength=wavelength, pattern=pattern, ray_density=ray_density, use_polarization=use_polarization))

    @tool
    async def run_local_optimization(
        algorithm: Literal['DampedLeastSquares', 'OrthogonalDescent'] = 'DampedLeastSquares',
        cycles: Literal['Automatic', 'Fixed_1_Cycle', 'Fixed_5_Cycles', 'Fixed_10_Cycles', 'Fixed_50_Cycles'] = 'Fixed_5_Cycles',
        number_of_cores: StrictInt = 1,
    ) -> ToolResponse:
        """使用当前变量和评价函数运行原生局部优化，返回可查询的任务编号。"""
        return await call('run_local_optimization', dict(algorithm=algorithm, cycles=cycles, number_of_cores=number_of_cores))

    @tool
    async def get_task_status(task_id: str) -> ToolResponse:
        """读取任务实际状态与可取消能力；取消中不代表已经停止。"""
        return await call("get_task_status", {"task_id": task_id})

    @tool
    async def get_task_result(task_id: str, start: Index = 0, count: StrictInt = 200, series: Index | None = None, grid: Index | None = None, x_start: Index = 0, y_start: Index = 0, width: StrictInt = 32, height: StrictInt = 32) -> ToolResponse:
        """读取已结束任务的数据、实际设置、模型版本及输出文件。"""
        return await call("get_task_result", dict(task_id=task_id,start=start,count=count,series=series,grid=grid,x_start=x_start,y_start=y_start,width=width,height=height))

    @tool
    async def cancel_task(task_id: str) -> ToolResponse:
        """请求原生工具取消，继续查询状态确认；已完成任务保持其完成状态。"""
        return await call("cancel_task", {"task_id": task_id})

    @tool
    async def run_batch_ray_trace(request: BatchRays) -> ToolResponse:
        """归一化或直接坐标批量追迹，可显式偏振，最多 10000 条；结果说明各模式可用字段和坐标。"""
        return await call("run_batch_ray_trace", request.model_dump())

    @tool
    async def run_parameter_scan(request: ParameterScan) -> ToolResponse:
        """单参数独立扫描，每点从基线开始；默认固定像面，完成或取消后恢复设计。"""
        return await call("run_parameter_scan", request.model_dump())

    @tool
    async def run_batch_evaluation(request: BatchEvaluation) -> ToolResponse:
        """按文件顺序运行同一评估，逐项记录失败，结束后恢复原设计。"""
        return await call("run_batch_evaluation", request.model_dump())

    @tool
    async def compare_results(left_task_id: str, right_task_id: str) -> ToolResponse:
        """比较成功的评估结果；分析条件不一致时返回差异，不计算改善结论。"""
        return await call("compare_results", dict(left_task_id=left_task_id, right_task_id=right_task_id))

    @tool
    async def export_evaluation_report(task_ids: list[str] | None = None, title: str = "Zemax 设计评估", include_charts: bool = False, formats: list[Literal["markdown","pdf"]] | None = None, background: bool = False, detector_files: list[str] | None = None) -> ToolResponse:
        """以已取得的结果输出 Markdown、JSON 和 CSV；不会重新执行 Zemax。"""
        return await call("export_evaluation_report", dict(task_ids=task_ids or [],detector_files=detector_files or [],title=title,include_charts=include_charts,formats=formats if formats is not None else ["markdown"],background=background))

    @tool
    async def get_system_resources(request: SystemResources) -> ToolResponse:
        """分页查询本机材料目录、材料、镀膜和相关文件。"""
        return await call("get_system_resources", request.model_dump())

    @tool
    async def get_star_data(request: StarRead) -> ToolResponse:
        """读取当前顺序曲面的STAR状态、拟合设置及分页FEA点。"""
        return await call('get_star_data', request.model_dump())

    @tool
    async def get_hpc_settings(request: HpcSelection) -> ToolResponse:
        """读取偏好或自定义HPC设置的实际节点、规格和配置状态。"""
        return await call('get_hpc_settings', {'request': request.model_dump()})

    @tool
    async def run_speos_export(request: SpeosExport) -> ToolResponse:
        """在独立系统副本中导出Speos LensSystem或Whitebox，返回任务与原生文件。"""
        return await call('run_speos_export', {'request': request.model_dump()})

    @tool
    async def run_star_operation(request: StarOperation) -> ToolResponse:
        """在检查点保护下导入或拟合STAR变形、温度或直接折射率数据。"""
        return await call('run_star_operation', {'request': request.model_dump()})

    @tool
    async def copy_surfaces(request: CopySurfaces) -> ToolResponse:
        """在物面与像面之间原生复制曲面，保留原物理光阑。"""
        return await call("copy_surfaces", request.model_dump())

    @tool
    async def get_surface_geometry(request: SurfaceGeometry) -> ToolResponse:
        """读取局部点 Sag 与全局变换；长度为镜头单位。"""
        return await call("get_surface_geometry", request.model_dump())

    @tool
    async def copy_system(request: SaveLens) -> ToolResponse:
        """创建并保存独立系统副本，释放副本，保留当前活动设计。"""
        return await call("copy_system", request.model_dump())

    @tool
    async def create_archive(request: ArchiveSave) -> ToolResponse:
        """启动 Zemax ZAR 归档创建任务；默认禁止覆盖。"""
        return await call("create_archive", request.model_dump())

    @tool
    async def load_archive(request: ArchiveLoad) -> ToolResponse:
        """解包 ZAR 到新目录并加载设计，返回任务编号。"""
        return await call("load_archive", request.model_dump())

    @tool
    async def get_project_settings() -> ToolResponse:
        """读取当前设计的项目目录状态和位置。"""
        return await call("get_project_settings")

    @tool
    async def update_project_settings(request: ProjectPatch) -> ToolResponse:
        """将当前设计转为项目目录或关闭项目模式，不修改全局偏好。"""
        return await call("update_project_settings", request.model_dump())

    @tool
    async def get_external_dependencies(request: Dependencies) -> ToolResponse:
        """分页读取原生文件管理器列出的设计依赖及可解析位置。"""
        return await call("get_external_dependencies", request.model_dump())

    @tool
    async def load_merit_function(request: OpenLens) -> ToolResponse:
        """保存检查点后从绝对路径加载 .MF 评价函数。"""
        return await call("load_merit_function", request.model_dump())

    @tool
    async def save_merit_function(request: SaveLens) -> ToolResponse:
        """将原生评价函数另存为 .MF；默认禁止覆盖。"""
        return await call("save_merit_function", request.model_dump())

    @tool
    async def run_analysis(request: AnalysisRequest) -> ToolResponse:
        """执行本机适配的顺序成像/像差/曲面分析，返回任务；实际设置和曲线、网格或原生文本随结果保存。"""
        return await call("run_analysis", {"request":request.model_dump(exclude_unset=request.kind in {'design_desensitize','coating_optimization','polarization_transmission_fan','polarization_transmission','fiber_coupling_settings','polarization_ray_trace','dispersion_diagram','dispersion_vs_wavelength','seidel_diagram'})})

    @tool
    async def get_configurations(request: ConfigurationRange) -> ToolResponse:
        """分页读取 MCE 操作数、配置值和求解关系。"""
        return await call("get_configurations",request.model_dump())

    @tool
    async def update_configurations(request: ConfigurationPatch) -> ToolResponse:
        """编辑配置及 MCE 操作数，已有求解关系受保护。"""
        return await call("update_configurations",request.model_dump())

    @tool
    async def set_configuration(configuration: StrictInt) -> ToolResponse:
        """切换活动配置并读取实际系统设置。"""
        return await call("set_configuration",dict(configuration=configuration))

    @tool
    async def get_constraint_coverage() -> ToolResponse:
        """读取 CONF 分段下的评价函数配置作用域。"""
        return await call("get_constraint_coverage")

    @tool
    async def run_global_optimization(request: GlobalOptimization) -> ToolResponse:
        """按显式有限时间预算运行原生全局优化。"""
        return await call("run_global_optimization",request.model_dump())

    @tool
    async def run_hammer_optimization(request: GlobalOptimization) -> ToolResponse:
        """按显式有限时间预算运行原生 Hammer 优化。"""
        return await call("run_hammer_optimization",request.model_dump())

    @tool
    async def run_configuration_evaluation(request: ConfigurationEvaluation) -> ToolResponse:
        """逐结构执行指定评估，每项从同一基线开始，结束恢复原设计与配置。"""
        return await call("run_configuration_evaluation",request.model_dump())

    @tool
    async def run_multistart_optimization(request: Multistart) -> ToolResponse:
        """从显式起点集合独立局部优化并评估；完成保留最佳，取消恢复基线。"""
        return await call("run_multistart_optimization",request.model_dump(exclude_unset=True))

    @tool
    async def get_tolerances(request: ToleranceRange) -> ToolResponse:
        """分页读取 TDE 公差、补偿器及 STAT 定义。"""
        return await call("get_tolerances",request.model_dump())

    @tool
    async def update_tolerances(request: TolerancePatch) -> ToolResponse:
        """替换、追加、插入、逐行修改或删除TDE操作数，操作前保存检查点。"""
        return await call("update_tolerances",request.model_dump(exclude_unset=True))

    @tool
    async def generate_tolerances(request: ToleranceWizard) -> ToolResponse:
        """按显式幅度运行顺序公差向导，未选择的误差类型关闭。"""
        return await call("generate_tolerances",request.model_dump())

    @tool
    async def run_tolerance_analysis(request: ToleranceAnalysis) -> ToolResponse:
        """运行灵敏度、逆灵敏度或蒙特卡罗，记录补偿和分布，结束恢复原设计。"""
        return await call("run_tolerance_analysis",request.model_dump())

    @tool
    async def summarize_tolerance_results(request: ToleranceSummary) -> ToolResponse:
        """从已有公差结果按显式准则列、单位及阈值计算分位数和通过比例。"""
        return await call("summarize_tolerance_results",request.model_dump())

    @tool
    async def get_nsc_objects(request: ObjectRange) -> ToolResponse:
        """读取对象及原生参数；混合模式须指定nsc_surface，编号与坐标属于该NSC组。"""
        return await call("get_nsc_objects",request.model_dump())

    @tool
    async def insert_nsc_objects(request: ObjectInsert) -> ToolResponse:
        """在指定编号前插入非序列空对象。"""
        return await call("insert_nsc_objects",request.model_dump())

    @tool
    async def delete_nsc_objects(request: ObjectInsert) -> ToolResponse:
        """删除指定非序列对象范围，保留检查点。"""
        return await call("delete_nsc_objects",request.model_dump())

    @tool
    async def copy_nsc_objects(request: ObjectCopy) -> ToolResponse:
        """原生复制非序列对象，复制后回读参考关系。"""
        return await call("copy_nsc_objects",request.model_dump())

    @tool
    async def update_nsc_objects(request: ObjectUpdates) -> ToolResponse:
        """编辑对象类型、位置、材料及 get_nsc_objects 返回的原生标量参数。"""
        return await call("update_nsc_objects",request.model_dump())

    @tool
    async def clear_detectors(request: DetectorClear) -> ToolResponse:
        """清空指定探测器，detector=0 清空全部。"""
        return await call("clear_detectors",request.model_dump())

    @tool
    async def get_detector_data(request: DetectorRead) -> ToolResponse:
        """读取矩形探测器指定数据类型及区域，完整矩阵保存为 JSON。"""
        return await call("get_detector_data",request.model_dump())

    @tool
    async def run_nsc_ray_trace(request: NscTrace) -> ToolResponse:
        """执行非序列追迹；默认清空，累积须显式指定，可保存 ZRD。"""
        return await call("run_nsc_ray_trace",request.model_dump())

    @tool
    async def read_zrd(request: ZrdRead) -> ToolResponse:
        """按光线/分段位置分块读取 ZRD，返回原生路径与后续读取位置。"""
        return await call("read_zrd",request.model_dump())

    @tool
    async def run_pop(request: Pop) -> ToolResponse:
        """运行物理光学传播，保存实际采样、窗口、光束/模式与结果网格。"""
        return await call("run_pop",request.model_dump())

    @tool
    async def get_beam_file(request: BeamRead) -> ToolResponse:
        """读取 version-1 二进制 ZBF 元数据和文件顺序复场样本。"""
        return await call("get_beam_file",request.model_dump())

    @tool
    async def run_pop_convergence(request: PopConvergence) -> ToolResponse:
        """按显式采样、窗口和容差比较 POP 指标，最后一个组合为参考。"""
        return await call("run_pop_convergence",request.model_dump())

    @tool
    async def run_cad_export(request: CadExport) -> ToolResponse:
        """按本机原生格式导出指定顺序曲面或非序列对象，返回任务。"""
        return await call("run_cad_export",request.model_dump())

    @tool
    async def run_layout_export(request: LayoutExport) -> ToolResponse:
        """导出本机原生顺序/非序列布局图片，保存实际设置并返回任务。"""
        return await call("run_layout_export",request.model_dump())

    @tool
    async def run_zrd_replay(request: ZrdReplay) -> ToolResponse:
        """用 Detector Viewer 回放 ZRD，结果与当前探测器累积数据分开保存。"""
        return await call("run_zrd_replay",request.model_dump())

    @tool
    async def save_detector_data(request: DetectorSave) -> ToolResponse:
        """保存当前探测器的原生数据文件，默认禁止覆盖。"""
        return await call("save_detector_data",request.model_dump())

    @tool
    async def load_detector_data(request: DetectorLoad) -> ToolResponse:
        """替换或累积加载原生探测器数据；外部数据的追迹来源标记为未知。"""
        return await call("load_detector_data",request.model_dump())

    @tool
    async def export_analysis_image(request: AnalysisImage) -> ToolResponse:
        """从已保存结果绘图或导出已有原生图片，不重新计算 Zemax。"""
        return await call("export_analysis_image",request.model_dump())

    @tool
    async def get_editor_metadata(request: EditorMetadata) -> ToolResponse:
        """读取MFE/MCE/TDE行类型、列标题、数据类型和活动状态；列分页从0开始。"""
        return await call("get_editor_metadata",request.model_dump())

    @tool
    async def insert_editor_rows(request: EditorInsert) -> ToolResponse:
        """在MFE/MCE/TDE指定1基位置插入行，返回实际类型与读取结果。"""
        return await call("insert_editor_rows",request.model_dump(exclude_unset=True))

    @tool
    async def copy_editor_rows(request: EditorCopy) -> ToolResponse:
        """在同一MFE/MCE/TDE内复制连续行；引用重编号由原生编辑器处理。"""
        return await call("copy_editor_rows",request.model_dump())

    @tool
    async def save_tolerance_file(path: str,overwrite: bool = False) -> ToolResponse:
        """保存原生.tol公差文件，路径为绝对路径。"""
        return await call("save_tolerance_file",dict(path=path,overwrite=overwrite))

    @tool
    async def load_tolerance_file(path: str) -> ToolResponse:
        """载入原生.tol公差文件，创建检查点并读取实际公差表。"""
        return await call("load_tolerance_file",dict(path=path))

    @tool
    async def run_design_tool(request: DesignRequest) -> ToolResponse:
        """执行缩放、Quick Adjust及非球面工具；建立检查点并返回任务。"""
        return await call("run_design_tool", {"request": request.model_dump()})

    @tool
    async def get_design_tool_options(request: DesignToolOptions) -> ToolResponse:
        """读取设计工具原生默认设置和枚举，关闭工具并返回结果。"""
        return await call("get_design_tool_options", request.model_dump())

    @tool
    async def run_optimization_wizard(request: WizardRequest) -> ToolResponse:
        """配置顺序/非序列优化向导，apply开启后生成评价函数，返回任务。"""
        return await call("run_optimization_wizard", {"request": request.model_dump(exclude_unset=True)})

    @tool
    async def run_standalone_macro(request: StandaloneMacro) -> ToolResponse:
        """在独立OpticStudio进程中运行绝对路径ZPL宏；返回可轮询、可取消的任务。"""
        return await call("run_standalone_macro", request.model_dump())

    @tool
    async def get_optimization_wizard_options(request: WizardOptions) -> ToolResponse:
        """读取原生向导设置、枚举及资源选项。"""
        return await call("get_optimization_wizard_options", request.model_dump())

    @tool
    async def get_nsc_object_geometry(request: ObjectGeometry) -> ToolResponse:
        """分页读取原生对象面顶点/法线；借用游标与坐标设置在退出时恢复。"""
        return await call('get_nsc_object_geometry',request.model_dump())

    @tool
    async def run_nsc_conversion(request: NscConversion) -> ToolResponse:
        """在工作模型中将顺序曲面组转换为混合模式或纯NSC，保留恢复检查点。"""
        return await call("run_nsc_conversion",request.model_dump())

    @tool
    async def get_material_properties(request: MaterialProperties) -> ToolResponse:
        """读取原生材料目录系数、热属性及内部透过率表，结束关闭目录工具。"""
        return await call("get_material_properties",request.model_dump())

    @tool
    async def get_coating_rta(request: CoatingRta) -> ToolResponse:
        """直接读取指定顺序曲面的双向镀膜S/P及等权非偏振R/T/A。"""
        return await call("get_coating_rta", request.model_dump(exclude_unset=True))

    @tool
    async def get_coating_layers(request: CoatingLayerRange) -> ToolResponse:
        """读取当前顺序曲面的镀膜层乘数、偏移、状态及拾取源。"""
        return await call("get_coating_layers",request.model_dump())

    @tool
    async def update_coating_layers(request: CoatingLayerUpdate) -> ToolResponse:
        """修改镀膜层并检查最终状态，保留检查点及部分失败详情。"""
        return await call("update_coating_layers",request.model_dump(exclude_unset=True))

    @tool
    async def get_lens_catalogs() -> ToolResponse:
        """读取本机原生镜头厂商目录和当前搜索设置，随后关闭工具。"""
        return await call("get_lens_catalogs", {})

    @tool
    async def run_lens_catalog_search(request: CatalogSearch) -> ToolResponse:
        """按厂商、毫米EFL/EPD、形状及类型搜索镜头，返回可分页任务。"""
        return await call("run_lens_catalog_search", request.model_dump())

    @tool
    async def run_catalog_lens(request: CatalogLens) -> ToolResponse:
        """按厂商及唯一名称加载或插入原生目录镜头，创建恢复检查点。"""
        return await call("run_catalog_lens", request.model_dump(exclude_unset=True))

    @tool
    async def run_catalog_evaluation(request: CatalogEvaluation) -> ToolResponse:
        """从独立基线比较目录镜头/材料候选，复用评价并在结束时恢复基线。"""
        return await call("run_catalog_evaluation", request.model_dump(exclude_unset=True))

    @tool
    async def list_task_history(request: TaskHistory) -> ToolResponse:
        """发现当前及磁盘历史任务，按会话、请求、种类与状态筛选分页。"""
        return await call("list_task_history", request.model_dump())

    @tool
    async def get_historical_result(request: HistoricalResult) -> ToolResponse:
        """读取指定会话已落盘结果；支持行、曲线及网格区域分页。"""
        return await call("get_historical_result", request.model_dump())

    @tool
    async def get_request_status(request: RequestStatus) -> ToolResponse:
        """按请求编号读取执行回执，区分请求已返回及原生任务状态。"""
        return await call("get_request_status", request.model_dump())

    @tool
    async def export_point_cloud(request: PointCloudExport) -> ToolResponse:
        """在自有系统副本上导出曲面PCD，保留原生消息、文件头及关闭记录。"""
        return await call('export_point_cloud',request.model_dump())

    @tool
    async def run_merit_program(request: MeritProgram) -> ToolResponse:
        """在独立副本预览、求值或应用原生向导、完整瞳OPD目标与几何约束。"""
        return await call('run_merit_program',request.model_dump(exclude_unset=True))

    return server


def main():
    create_server().run(transport="stdio")
