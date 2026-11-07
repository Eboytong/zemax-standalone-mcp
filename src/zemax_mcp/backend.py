import json
import logging
import math
import os
import sys
import time
import uuid
from pathlib import Path

from pydantic import ValidationError

from .config import Config
from .data import clean, dotnet_array, unwrap, utc_now
from .errors import ZemaxError
from .models import COMMAND_MODELS
from .native import NativeSession
from .solve_support import solve_validation_summary, extended_solve_summary


BASE_CELLS = {
    "radius": "RadiusCell", "thickness": "ThicknessCell", "material": "MaterialCell",
    "semi_diameter": "SemiDiameterCell", "conic": "ConicCell", "tce": "TCECell",
    "mechanical_semi_diameter": "MechanicalSemiDiameterCell", "chip_zone": "ChipZoneCell",
}
COLUMNS = {"radius": "Radius", "thickness": "Thickness", "material": "Material",
           "semi_diameter": "SemiDiameter", "conic": "Conic", "tce": "TCE",
           "mechanical_semi_diameter": "MechanicalSemiDiameter", "chip_zone": "ChipZone"}
TERMINAL = {"succeeded", "failed", "cancelled"}


from .evaluation import EvaluationMixin


from .modeling import ModelingMixin, SOLVES, SOLVE_FIELDS, SOLVE_ALIASES, SURFACE_TYPES
from .files import FilesMixin
from .editors import EditorsMixin
from .design_tools import DesignToolsMixin
from .wizards import WizardsMixin
from .catalogs import CatalogsMixin
from .coatings import CoatingsMixin
from .materials import MaterialsMixin
from .conversion import ConversionMixin
from .history import HistoryMixin, RESULT_VERSION, write_json
from .analyses import AnalysesMixin
from .configurations import ConfigurationsMixin
from .tolerancing import TolerancingMixin
from .nonsequential import NonSequentialMixin, wavelength_filter_validation
from .physical_optics import PhysicalOpticsMixin
from .exports import ExportsMixin
from .rays import RaysMixin
from .pupil import PupilMappingMixin
from .geometry_backend import GeometryMixin
from .star import StarMixin
from .hpc import HpcMixin


class Backend(HpcMixin, StarMixin, ConversionMixin, MaterialsMixin, CoatingsMixin, HistoryMixin, CatalogsMixin, WizardsMixin, DesignToolsMixin, EditorsMixin, GeometryMixin, ModelingMixin, EvaluationMixin, FilesMixin, AnalysesMixin, ConfigurationsMixin, TolerancingMixin, NonSequentialMixin, PhysicalOpticsMixin, ExportsMixin, RaysMixin, PupilMappingMixin):
    """All methods, including task polling and cancellation, run on one worker thread."""

    def __init__(self, config: Config, native=None):
        self.config = config
        self.native = native or NativeSession()
        self.session_id = None
        self.revision = 0
        self.source_path = None
        self.work_path = None
        self.directory = None
        self.version = None
        self.build_id = None
        self.system_context = {}
        self.license = None
        self.tasks = {}
        self.active = None
        self.last_checkpoint = None
        self.request_id = None
        self.worker_instance_id = uuid.uuid4().hex
        self.requires_reconnect = False
        self.detector_history=[]
        self.detector_history_known=False
        self.detector_records={}
        self.detector_clear_context=(0,1)

    @property
    def system(self):
        return self.native.system

    def context(self):
        return {"session_id": self.session_id, "model_revision": self.revision,
                "source_file": self.source_path, "working_file": str(self.work_path) if self.work_path else None,
                "opticstudio_version": self.version, "opticstudio_build": self.build_id, "license": self.license,
                "checkpoint": self.last_checkpoint, "requires_reconnect": self.requires_reconnect, **self.system_context,
                "geometry": self.geometry_summary()}

    def dispatch(self, command, arguments, request_id=None):
        self.request_id = request_id
        previous_revision = self.revision
        try:
            if command not in COMMAND_MODELS:
                raise ZemaxError("UNKNOWN_COMMAND", f"未知命令：{command}")
            request = COMMAND_MODELS[command].model_validate(arguments)
            self.tick()
            if self.requires_reconnect and command not in {
                "get_status", "get_capabilities", "get_task_status", "get_task_result", "disconnect", "list_task_history", "get_historical_result", "get_request_status"
            }:
                raise ZemaxError("RECONNECT_REQUIRED", "原生工具资源释放未确认，请断开后重新连接。")
            if self.active and command not in {
                "get_status", "get_capabilities", "get_task_status", "get_task_result", "cancel_task", "list_task_history", "get_historical_result", "get_request_status"
            }:
                raise ZemaxError("SYSTEM_BUSY", "当前系统正在计算，请等待完成或请求取消。", task_id=self.active["task_id"])
            data = getattr(self, command)(request)
            warnings = data.get("task", {}).get("cleanup_warnings", []) if isinstance(data, dict) else []
            return clean({"ok": True, "data": data, "error": None, "warnings": warnings,
                          "context": self.context(), "artifacts": data.get("artifacts", []) if isinstance(data, dict) else []})
        except ValidationError as exc:
            error = {"code": "INVALID_ARGUMENT", "message": "参数不符合工具定义。",
                     "details": self._argument_errors(command, exc)}
        except ZemaxError as exc:
            error = exc.as_dict()
        except Exception as exc:
            logging.getLogger(__name__).exception("Native command failed: %s", command)
            error = {"code": "NATIVE_ERROR", "message": str(exc), "details": {"type": type(exc).__name__}}
        if command in {"run_local_optimization","run_global_optimization","run_hammer_optimization"} and isinstance(error.get("details"),dict) and error["details"].get("diagnostics"):
            import copy
            attempts=getattr(self,"_optimizer_failures",{})
            current={"arguments":copy.deepcopy(arguments),"revision":self.revision,"diagnostics":error["details"]["diagnostics"]}
            if attempts.get(command)==current:
                error={"code":"OPTIMIZATION_RETRY_REQUIRES_CHANGE","message":"相同输入和模型仍产生相同诊断，请先修正参数、模型或诊断问题。",
                       "details":{"previous_code":error["code"],"diagnostics":current["diagnostics"],"next_request":{"command":"get_capabilities","arguments":{"topic":"optimization_diagnostics"}}}}
            attempts[command]=current
            self._optimizer_failures=attempts
        if isinstance(error.get("details"), dict):
            error["details"].update(command=command, partial_changes_possible=self.revision != previous_revision or
                (self.requires_reconnect and 'restore_error' in error['details']))
        return clean({"ok": False, "data": None, "error": error, "warnings": [],
                      "context": self.context(), "artifacts": []})

    @staticmethod
    def _argument_errors(command, exc):
        from ast import literal_eval
        rows=[]
        for issue in exc.errors(include_context=False, include_url=False):
            row={"field_path":".".join(map(str,issue["loc"])),"type":issue["type"],"message":issue["msg"]}
            if issue["type"]=="literal_error":
                try: row["allowed_values"]=list(literal_eval("["+issue["msg"].removeprefix("Input should be ").replace(" or ",", ")+"]"))
                except (ValueError,SyntaxError): pass
            rows.append(row)
        return {"fields":rows,"contract_request":{"tool":"get_capabilities","arguments":{"topic":"tool","tool_name":command}},
                "partial_changes_possible":False,"execution_stage":"parameter_validation"}

    def _require_sequential(self, focused=False):
        if str(self.system.Mode) != "Sequential":
            raise ZemaxError("UNSUPPORTED_MODE", "本工具当前适配顺序系统。")
        if focused and self.system.SystemData.Aperture.AFocalImageSpace:
            raise ZemaxError("UNSUPPORTED_MODE", "本分析当前适配有焦像空间；无焦模式尚未验证。")

    def _row(self, index):
        self._require_sequential()
        if index < 0 or index >= self.system.LDE.NumberOfSurfaces:
            raise ZemaxError("INDEX_OUT_OF_RANGE", "曲面编号超出范围。", surface=index)
        return self.system.LDE.GetSurfaceAt(index)

    def _cell(self, row, name):
        if name in BASE_CELLS:
            return getattr(row, BASE_CELLS[name])
        if name.startswith("parameter_"):
            enum = self.native.enum(self.native.api.Editors.LDE.SurfaceColumn, "Par" + name.removeprefix("parameter_"))
            return row.GetSurfaceCell(enum)
        raise ZemaxError("INVALID_CELL", "不支持的曲面单元格。", cell=name)

    def _cells(self, row, parameter_start=1, parameter_count=254):
        for name in (*BASE_CELLS, *(f"parameter_{i}" for i in range(parameter_start, min(255,parameter_start+parameter_count)))):
            cell = self._cell(row, name)
            if cell is not None and cell.IsActive:
                yield name, cell

    @staticmethod
    def _cell_value(cell):
        kind = str(cell.DataType)
        if kind == "Integer":
            return int(cell.IntegerValue)
        if kind == "Double":
            return float(cell.DoubleValue)
        return str(cell.Value)

    @staticmethod
    def _write_cell(cell, value, *, zero_radius=False):
        kind = str(cell.DataType)
        if cell.IsReadOnly or not cell.IsActive:
            raise ZemaxError("CELL_NOT_WRITABLE", "单元格未启用或只读。", header=str(cell.Header))
        if kind == "Integer":
            if int(value) != float(value):
                raise ZemaxError("INVALID_ARGUMENT", "此参数必须为整数。", header=str(cell.Header))
            cell.IntegerValue = int(value)
        elif kind == "Double":
            cell.DoubleValue = float(value)
        else:
            cell.Value = str(value)
        from .detectors import check_setting_value
        actual=Backend._cell_value(cell)
        if zero_radius and value == 0 and isinstance(actual,(int,float))and math.isinf(actual):
            return
        if value in ('Infinity','-Infinity')and isinstance(actual,(int,float))and math.isinf(actual):
            if (actual>0)!=(value=='Infinity'):raise ZemaxError('SETTING_REJECTED','无穷值符号未采用。')
        elif isinstance(value,str):
            check_setting_value(str(cell.Header),value,str(actual))
        else:check_setting_value(str(cell.Header),value,actual)

    def _guard_cell(self, cell, replace=False):
        if cell is None:
            raise ZemaxError('CELL_NOT_WRITABLE','此面型没有对应的活动单元格。')
        automatic_transition = replace and cell.IsActive and str(cell.Solve)=="Automatic" and "Fixed" in [str(x) for x in cell.GetAvailableSolveTypes()]
        if (cell.IsReadOnly and not automatic_transition) or not cell.IsActive:
            raise ZemaxError("CELL_NOT_WRITABLE", "单元格未启用或只读。", header=str(cell.Header))
        if str(cell.Solve) not in ("Fixed", "Variable") and not replace:
            raise ZemaxError("SOLVE_PROTECTED", "修改会影响现有 solve/pickup；请显式允许替换。", solve=str(cell.Solve), header=str(cell.Header))

    def _checkpoint(self, label):
        if self.work_path is None:
            raise ZemaxError("NO_WORKING_MODEL", "请先新建或打开镜头。")
        root=self.work_path.parent if getattr(self.system,"IsProjectDirectory",False) else self.directory
        path = root / f"checkpoint_r{self.revision}_{label}_{uuid.uuid4().hex[:8]}.zos"
        self.system.SaveAs(str(path))
        self.system.SaveAs(str(self.work_path))
        self.last_checkpoint = str(path)
        return str(path)

    def _mutate(self, label):
        self._checkpoint(label)
        # Increment before the first native write: partial failures also invalidate old results.
        self.revision += 1
        if getattr(self, '_geometry_fact', None):
            self._geometry_fact = {**self._geometry_fact, 'state': 'expired', 'expired_by': label}
        if label in {'insert','delete','copy_surfaces','before_archive_load'}:
            self._engineering_mapping_valid=False

    def _working_copy(self):
        path = self.directory / f"working_{uuid.uuid4().hex[:8]}.zos"
        if getattr(self.system,'IsProjectDirectory',False):
            original=Path(str(self.system.SystemFile))
            path=self.directory/('project_'+uuid.uuid4().hex[:8])/original.name
            self._copy_project_resources(original.parent,path.parent)
        self.system.SaveAs(str(path))
        self.work_path = path

    def connect(self, req):
        try:
            app = self.native.connect(Path(req.install_dir) if req.install_dir else self.config.install_dir)
        except Exception:
            if self.native.application is not None and not getattr(self.native, "connection_ready", True):
                self.requires_reconnect = True
            raise
        if self.session_id is None:
            self.session_id = uuid.uuid4().hex
            self.directory = self.config.output_dir / self.session_id
            self.directory.mkdir(parents=True, exist_ok=True)
            self.version = f"{app.ZOSMajorVersion}.{app.ZOSMinorVersion}.{app.ZOSSPVersion}"
            self.build_id = str(app.OpticStudioVersion)
            self.license = str(app.LicenseStatus)
            self.get_system_settings(None)
        return self.get_status(None)

    def get_status(self, req):
        connected = self.native.application is not None and getattr(self.native, "connection_ready", True)
        native_status = str(self.system.GetCurrentStatus()) if connected and not self.active and not self.requires_reconnect else None
        views = list(self.tasks.values())
        index = {task["task_id"]: {"state": task.get("state"), "kind": task.get("kind"),
                                   "finished_at": task.get("finished_at")}
                 for task in views if task.get("task_id")}
        return {"connected": connected, "native_system_status": native_status,
                "native_startup": getattr(self.native, "startup_diagnostics", None),
                "active_task": self._task_view(self.active) if self.active else None,
                # Polling only the newest ten tasks let older finished tasks stay
                # "running" in the host forever and prevented task reconciliation.
                "running_tasks": [self._task_view(task) for task in views
                                  if task.get("state") not in TERMINAL][::-1],
                "task_index": index,
                "recent_tasks": [self._task_view(t) for t in views[-10:][::-1]],
                **self.context()}

    def get_capabilities(self, req):
        topic = getattr(req, "topic", "all")
        if topic == "tool":
            tool = getattr(req,"tool_name",None)
            if tool not in COMMAND_MODELS:
                raise ZemaxError("UNKNOWN_COMMAND","请选择已登记工具。",tool_name=tool,allowed_values=list(COMMAND_MODELS))
            value=dict(tool_name=tool,request_schema=COMMAND_MODELS[tool].model_json_schema(),
                       example_note="参数字段按 request_schema 填写；操作数参数使用原生列号键值对象。")
            if tool=='run_cad_export':
                value['cad_export']=dict(interface='ZOSAPI.Tools.General.IExportCAD',
                    configuration='current by default (native encoding 0); positive configuration selects single; configuration_mode also supports all_by_file/all_by_layer/all_at_once without changing model selection',
                    optional_settings='omitted or null retains the native tool value',
                    units=dict(dummy_thickness='current lens unit',layers='native integer layer indices'),
                    conditions=dict(angular_tolerance='STL',dummy_thickness='export_dummy_surfaces and surfaces_as_solids',
                        SolidRing='sequential, at least 8 rays; native marginal-ray and caustic conditions apply',
                        nsc_ray_count='number_of_rays inactive; per-source NumberOfLayoutRays controls NSC rays',
                        file_version='ACIS formats only; SAT/SAB actual file header checked, local explicit V25-V30 not adopted'),
                    adoption='final scalar readback and native enum value comparison',
                    completion='native success, confirmed Close, output file present; all_by_file returns unique directory, paths and per-configuration artifacts',
                    native_acceptance='STEP/STL/SAT Current extended settings and file creation passed; sequential cylinder and transformed NSC box geometry accepted; NSC scatter/split/polarization adoption and subsequent trace passed; ACIS explicit version mismatch remains',validation='docs/special-exports.md')
            if tool=='export_point_cloud':
                value['point_cloud']=dict(interface='ILensDataEditor.CanExportPointCloud/RunTool_ExportPointCloudFile',
                    formats=['ASCII','Binary','CompressedBinary'],scope='sequential supported native surface; owned synchronous copy',
                    units='selected surface local coordinates in current lens units; native normals',
                    sampling='organized WIDTH=x_sampling, HEIGHT=y_sampling; X-fastest cell-center grid; invalid aperture sag/normals remain NaN',
                    adoption='native output dimensions, DATA and normal fields; method has no setting getters',
                    lifecycle='copy closed on success/failure; synchronous method has no native cancellation handle',
                    validation='plane and sphere, translated/tilted parent, mm/cm and all three encodings accepted; docs/special-exports.md')
            if tool=='get_surface_geometry':
                value['geometry_metrics']=dict(analysis_kind='geometry_check',unit='mm',
                    metrics=['minimum_separation_lower_mm','minimum_separation_upper_mm','glass_minimum_thickness_lower_mm','glass_minimum_thickness_upper_mm','air_minimum_gap_lower_mm','air_minimum_gap_upper_mm'],
                    availability='complete system task observations only; lower and upper are certified interval bounds, missing media have no metric')
            return value
        if topic in {"merit_cells","optimization_diagnostics"} and (self.active or self.requires_reconnect):
            raise ZemaxError("SYSTEM_BUSY" if self.active else "RECONNECT_REQUIRED","当前原生状态不允许评价函数读取或求值。")
        if topic == "merit_cells":
            from .models import MeritRange
            return self.get_merit_function(MeritRange(start=req.start,count=req.count))
        if topic == "optimization_diagnostics":
            return self.optimization_diagnostics()
        connected = self.native.application is not None and getattr(self.native, "connection_ready", True)
        result = {"connected": connected, "implemented_tools": list(COMMAND_MODELS),
                  "editor_extensions": {"editors":["MFE","MCE","TDE"],"tde_modes":["replace","append","insert","update","delete"],"metadata":"get_editor_metadata","rows":["insert_editor_rows","copy_editor_rows"],"tolerance_files":["load_tolerance_file","save_tolerance_file"],"native_adoption":"pending_connection","validation":"docs/editor-extensions.md"},
                  "task_history": {"discovery":"list_task_history","request_lookup":"get_request_status","results":"get_historical_result","result_schema_version":1,"legacy_result_versions":[0],"history_root":str(self.config.output_dir),"validation":"docs/task-history.md"},
                  "lens_catalogs": {"search":"run_lens_catalog_search","selection":"run_catalog_lens","evaluation":"run_catalog_evaluation","dimension_unit":"millimeters","native_adoption":"pending_connection","validation":"docs/lens-catalogs.md"},
                  "design_tools": {"tools": ["scale_factor","scale_units","quick_adjust","find_best_asphere","convert_asphere","ray_aiming_wizard"],"wizards":["sequential","nsc","bitmap","roadway"],"native_adoption":"pending_connection","validation":"docs/design-tools.md"},
                  "modes": {"Sequential": "implemented", "NonSequential": "implemented"},
                  "implemented_surface_types": SURFACE_TYPES,
                  "implemented_solves": SOLVES,
                  "extended_solve_validation": extended_solve_summary(),
                  "analysis_scope": "typed sequential curve/grid/text analyses, POP and NSC tracing",
                  "validation": "See docs/capabilities.md for implementation and validation scope.",
                  "pending_verification": ["additional_surface_type_numeric_references", "advanced_NSC_physics_numeric_references", "nonzero_aberration_and_complex_pupil_analysis_references"],
                  "runtime_availability": "未连接时不判定许可或本机任务可运行性。",
                  "verification": {"gui_fft_mtf":"passed_Cooke_image_all_fields_waves_64x64_Modulation_50cycles_per_mm_unpolarized_606_displayed_values","gui_quick_focus":"passed_radial_chief_ray_Cooke","native_diagnostic_root":"unknown","evidence":"docs/capabilities.md"}}
        from .property_pages import SYSTEM_PAGES,SURFACE_PAGES
        from .extension_resources import EXTENSION_FOLDERS
        result['extension_resources'] = dict(tool='get_system_resources', kind='extension_files',
            roles=[*EXTENSION_FOLDERS, 'zpl'], source='active native application resource directories',
            selection='native consumer validates actual resource selection and settings', validation='docs/extensions.md')
        result['hpc'] = dict(settings_tool='get_hpc_settings', selection_modes=['preferences','custom'],
            task_tools=['run_nsc_ray_trace','run_tolerance_analysis','run_global_optimization','run_hammer_optimization'],
            settings=['IsHPCConfigured','NodeCount','MaxNodeCount','InstanceType','ThreadsPerTask','ShutdownTimeTicks'],
            readiness='native configuration flag plus actual job initialization/license/node checks',
            native_acceptance='pending native initialization and configured execution environment',validation='docs/hpc.md')
        from .star_controls import CONTROL_KINDS
        result['star_operations'] = dict(read='get_star_data', run='run_star_operation',
            data_kinds=['deformation','temperature','direct_index'], operations=['import','fit',*sorted(CONTROL_KINDS)],
            mode='Sequential current configuration', license='IsSTARModuleEnabled checked per operation',
            length_units='FEA file coordinates and displacement must match current lens units',
            cancellation='cooperative between native calls with checkpoint restoration on failure/cancel',
            native_acceptance='pending initialization and STAR license check', validation='docs/star.md')
        result['property_pages']={'system':{k:list(m) for k,(_,m) in SYSTEM_PAGES.items()},'surface':{k:list(m) for k,(_,m) in SURFACE_PAGES.items()},'units':'lengths in current lens units; angles follow native page units','evidence':'docs/property-pages.md'}
        result['property_page_local_limitations']={
            'User':'settings creation raises UILDEScatterData serialization exception; raw exception retained',
            'BSDF':'local file selector can return ABGF names and ignore BSDF assignment; mismatched resource list is rejected',
            'ISScatterCatalog':'requires an installed valid ISX catalog data file',
            'FloatingAperture_to_None':'native success can retain FloatingAperture; actual type readback is required',
            'evidence':'verification/property-pages017-summary.json'}
        result["solve_validation"]=solve_validation_summary()
        result["zrd_wavelength_filter_validation"]=wavelength_filter_validation()
        from .detectors import detector_capabilities
        result["detector_adapters"]=detector_capabilities()
        result["feature_registry"]="docs/capabilities.md"
        result['nsc_object_geometry']=dict(tool='get_nsc_object_geometry',source='INCERow.GetFacetedObjectData / IFaceData',condition='ObjectIsADetector must be explicitly enabled',pages='zero-based faces; per page <=1000 faces and <=100000 vertices',frames=['local','global'],normals='global rotation of local vectors; raw native global normals retained separately',restore='CurrentFace and ConvertToGlobal restored; failure requires reconnect',validation='native box/STL coordinates, normals, radiometry and reload passed',evidence='docs/nsc-object-data.md')
        result['nsc_detector_regions']=dict(tool='get_detector_data',read_mode='region',supported=['DetectorRectangle','DetectorVolume'],max_samples=100000,source='NCE.GetDetectorData scalar, one-based x-fast pixel formula',full_matrix_allocation=False,validation='native rectangle/volume quantities, independent point ray and >1 million voxel bounded read passed',evidence='docs/nsc-object-data.md')
        result['ima_bim_viewer']=dict(kind='ima_bim_viewer',methods=['native_source_bitmap','file'],resource='Images directory; IMA/BIM filename and one-based map_index',results='full-precision file intensity and peak-normalized grids; optional native 8-bit RGB display; rows/grid paging',source='documented IMA/BIM formats; formal ImageSimulation SourceBitmap; 2/4 plane conversion tested',validation='590 exact pixel checks; zero/malformed/cancel/reuse/reload/resource close passed',evidence='docs/ima-bim-viewer.md')
        result['ray_database_viewer']=dict(kind='ray_database_viewer',source='formal OpenRayDatabaseReader; RayDatabaseViewer AS_Default has no typed selectors',results='native ray/segment rows, filtering, bounded continuation and task paging',validation='deterministic three-ray NSC trace, segment references, close, cancel/reuse/reload passed; malformed-content file is returned as empty-success by runtime',evidence='docs/ray-database-viewer.md')
        result['power_maps']=dict(kinds=['power_field_map','power_pupil_map'],source='explicit native POWF/POWP arguments; thematic AS_Default has no typed selectors',units='Power in diopters; EFL in current lens units',surface='required last powered surface',field_sampling='uniform physical field; use_tangent_of_field_angle=true: uniform dimensionless tan(angle), with physical angles retained; Angle fields only, widths <180 degrees',validation='implemented: principal-curvature, oblique spherical/biaxial Coddington and off-center pupil references passed; tangent coordinates, mm/cm units, pagination/export and lifecycle accepted; peripheral native ring validity and zero-EFL interpretation remain open',ray_validity='valid_mask covers central reference ray and finite query only; native surrounding ring status unavailable',value_states='raw_value_state distinguishes native_zero, finite_nonzero and not_queried independently of offset; native_zero_count and invalid_reference_ray_count accompany the grid',zero_semantics='native zero retained without inferring infinity or native failure; zero_interpretation remains unresolved',evidence='docs/power-maps.md')
        result['nsc_mtf']=dict(kind='nsc_geometric_mtf',detector='DetectorRectangle; PSF wave 0',
            frequency='cycles/mm, limited by smaller pixel Nyquist',source='current accumulation or explicit ZRD/filter',
            direction_axes={'Tangential':'detector local Y','Sagittal':'detector local X'},
            frequency_sampling=dict(default='native_display_curve',explicit_frequencies='native_frequency_endpoints;1..301 increasing nodes; one native analysis per node'),
            validation='accepted through native endpoint queries; point/asymmetric accumulated/ZRD DFT max error2.701e-8 under original1e-7+1e-7relative',
            display_curve_precision='native serialized interior nodes retain historical6.234e-5 error; original output and evidence retained',
            evidence='verification/development/NS-03/acceptance565-endpoints.json')
        result['mce_double_readback']=dict(source='native MCE DoubleValue',significant_digits=9,
            write_check='requested value rounded to getter precision; actual native getter value returned',
            internal_precision='setter can retain more precision than getter',
            evidence='verification/development/ED-03/progress542-mce-precision.json')
        result['quick_yield']=dict(kind='quick_yield',metric='native fitted RMS wavefront in waves; cumulative yield in percent',
            settings='final scalar/enum combination, user-defined field mode and wavelength read back',
            validation='accepted; controlled zero/finite perturbations and lifecycle; Cooke reference requires selected-wavelength evaluation of primary-dependent solves',
            reference_conditions='Cooke dynamic/fixed-radius controls agree within6.7e-7waves; controlled refractor agrees with piston/linear-pupil-tilt removed OPD RMS',
            precision_reference='controlled equal-edge-sag r6-r12: VeryHigh passes original RMS gate; Standard r8-r12 exceeds it; TO-01/progress550-high-order.json',
            evidence='verification/development/TO-01/acceptance574-reference.json')
        result['system_data_report']=dict(kind='system_data',settings='AS_Default; no business settings',results='native system/detail report and one-based rows; displayed precision retained')
        result['system_check']=dict(kind='system_check',settings='native AS_Default; no business settings',results='native UTF-16 diagnostic report; one-based rows pagination',scope='configuration scope and findings retained in original report; task success means report generation')
        result['file_comparator']=dict(kind='file_comparator',inputs='existing absolute .zos/.zmx paths; optional one-based configurations',settings='all 15 include sections plus ShowDifferencesOnly; final native readback',results='native UTF-16 report and paged one-based text lines, native markup retained',configuration_validation='explicit selections checked in owned temporary system; native silently accepts out-of-range values',validation='controlled radius/comment changes, same file, distinct configurations, section flags, paging and close passed',evidence='docs/file-comparator.md')
        result['surface_slope_analyses']=dict(kinds=['surface_slope','surface_slope_cross','surface_phase_slope','surface_phase_slope_cross'],
            coordinates='surface local lens units; maps values[y][x]; cross XData=X, YData=[Y,slope]',
            geometric_value_unit='dimensionless sag derivative',phase_value_unit='cycles per lens unit',
            validation='sphere/conic sag derivatives and positive/negative Binary2 analytic phase derivatives/(2*pi), removals, paging, save/reload and lifecycle passed',
            evidence='docs/surface-slopes.md')
        result['rms_field_map']=dict(kind='rms_field_map',sampling='native RayDensity; rectangular array or GaussQuad',
            coordinates='native offsets plus selected physical reference field; X/Y sizes are half widths',
            spot_unit='micrometers; converted from native lens units',wavefront_unit='waves',strehl_unit='dimensionless',
            auxiliary_line='show_diffraction_limit=true rejected; native interface has no setting',
            grid_dimensions='5..101 points per axis, even sizes supported',
            validation='offset7x5 grid;128x128 spot/ChiefRayOPD quadrature, native options, paging/save-reload/cancellation and reuse passed;64sampling convergence evidence retained',evidence='docs/rms-field-map.md')
        result['nsc_ray_analyses']=dict(kinds=['path_analysis','critical_ray_trace','nsc_single_ray_trace'],scope='pure NSC current configuration',units='path flux watts; CRT positions lens units, angles degrees; single-ray segments global',results='native paths/rows and uncategorized, CRT Pass and endpoints, single-ray segments/ZRD; paged rows',validation='CRT and single-ray references/reload/cancellation passed; path threshold-excluded uncategorized flux remains open',evidence='docs/nsc-paths.md')
        result['nsc_conversion']=dict(tool='run_nsc_conversion',source='IConvertToNSCGroup',modes=['group','pure'],checkpoint='before conversion; failure/cancel retain checkpoint for explicit recovery',validation='implemented; native adoption and ray equivalence pending',evidence='docs/nsc-conversion.md')
        result['material_analyses']=dict(kinds=['internal_transmission_vs_wavelength'],resource_identity='explicit loaded catalog; catalog names accept an optional .AGF suffix; ambiguous aliases and duplicate material names rejected',
            properties_tool='get_material_properties',units='wavelength micrometers; transmission thickness millimeters; raw native catalog formula/thermal/mechanical properties',
            table_pages='table_start/table_count; native coefficient and table indices retained',validation='SCHOTT N-BK7 native properties/selection and Beer-Lambert reference passed; other catalog conditions require item-specific acceptance',evidence='docs/materials.md')
        result['material_analyses']['star_samples'] = dict(maximum=100, source='ISTARMaterials',
            outputs=['refractive_index','dn_dt'], availability='native material getter decides actual availability',
            conditions=['wavelength_um','environment_pressure_atm','environment_temperature_c',
                        'material_pressure_atm','material_temperature_c','delta_temperature_c'])
        result['polarization_analyses']=dict(kinds=['polarization_pupil_map'],scope='sequential current configuration',
            settings='documented IAS_.SaveTo/ModifySettings/LoadFrom; native text header and pupil-lattice adoption checks',
            sampling='odd pupil grid diameter 3..101; native adoption verified per run',
            results='paged pupil rows Ex/Ey amplitudes, relative intensity, relative phase and orientation; intensity scatter plot',
            units='normalized pupil; native field amplitude/intensity; phase and orientation degrees',
            validation='docs/polarization.md')
        result['coating_analyses']=dict(metrics=['reflection','transmission','absorption','diattenuation','phase','retardance'],
            scans=['angle','wavelength'],listing='coating_listing (sequential)',scope='sequential current configuration, mixed NSC component, pure NSC',
            nsc_selection='paired one-based nsc_object and zero-based native optical face-group nsc_face; discover via get_nsc_objects; pure NSC surface=0, mixed component uses actual LDE surface; owned analysis copy',
            wavelength_selection='public one-based, native coating-angle selector zero-based; wavelength-copy primary preserved for relative film thickness',
            reverse_direction='active for pure NSC and NonSequential component surfaces; rejected on ordinary sequential surfaces',
            units='angle degrees; wavelength micrometers; result labels/header preserve S/P phase conventions',
            layer_tools=['get_coating_layers','update_coating_layers'],layer_values='thickness multiplier, index/extinction offsets; Fixed/Variable/Pickup',
            validation='native scans/layers and independent bare-interface plus absolute/relative single-film references passed; ideal MIRROR reflection-phase reference passed; remaining scope in docs/coatings.md',evidence='docs/coatings.md')
        result['imaging_analyses']=dict(kinds=['image_simulation','geometric_image','fft_line_edge_spread','geometric_line_edge_spread','extended_source_encircled_energy'],
            scope='focused sequential current configuration', resources=['image_simulation_files','geometric_image_files'],
            results='native scalar/RGB grids, series, scatter; ImageSimulation owned OutputFile BMP fallback with three 8-bit display RGB grids and native PNG export; grid regions and series pages',
            units='native labels/header; scene height/width uses field coordinates; geometric line radius in micrometers',
            validation='geometric_image: ideal coordinates/power and parity accepted; image_simulation: native file views/RGB, ideal pixels and source transforms, spectral/polarization modes, reload and running cancellation accepted; other kinds retain per-item evidence',
            evidence='docs/imaging.md')
        result['parameter_ranges']=dict(LDE=dict(first=1,last=254,default_read_count=20),NCE=dict(first=1,last=250,default_read_count=20),
            availability='only native active writable cells; enumeration bounds are not a model support claim')
        result['wavefront_pupil_mapping']=dict(option='include_pupil_mapping',
            scope='axisymmetric focused, untilted/undecentered circular unobscured; angular Y fields, radial normalization, selected primary wavelength',
            method='real chief/marginal-ray F-numbers and analytic apparent-display inverse; per-point raw OPD check',
            invalid='null coordinates with reason for unsupported scope, aperture/ray failures or OPD mismatch',
            limitation='non-primary wavelength mapping remains unverified; not a physical pupil-surface reconstruction',
            evidence='docs/model-adaptation.md')
        result['source_backed_nsc_dll_validation']=dict(
            object_geometry=['HalfCylinder.DLL','EllipticalVolume.DLL'],object_transmission=['CoatingSample.DLL'],
            source_distributions=['Cone.dll','fiber1.DLL','Lambertian_Overfill.dll'],
            bulk_first_event_distributions=['bulk_samp_1.DLL','Henyey-Greenstein-bulk.DLL','poly_bulk_scat.DLL','Rayleigh.DLL'],
            pending=['DiffractionGrating.DLL optical trace'],
            scope='explicit installed-source parameter fixtures; other parameters require independent references',
            evidence='docs/model-adaptation.md')
        result['mixed_mode_objects']=dict(interfaces=['get_nsc_objects','insert_nsc_objects','update_nsc_objects','delete_nsc_objects','copy_nsc_objects'],
            selector='nsc_surface: sequential NonSequential-component surface number; required in mixed mode',
            identity='(nsc_surface, object); ref_object and inside_of are group-local',
            coordinates='NSC group entrance coordinates; combine with get_surface_geometry(nsc_surface) for sequential global coordinates',
            trace_scope='NSC tracing and detector tools remain pure NonSequential only',
            validation='docs/nonsequential-validation.md')
        if connected and not self.active and str(self.system.Mode)=='Sequential':
            result['active_nsc_surface']=int(self.system.NCE.ActiveSurface)
        result["validated_surface_model_scope"]=["Standard","EvenAspheric","OddAsphere","Toroidal","Biconic","Paraxial","CoordinateBreak","GridSag","GridPhase",
            "Polynomial","Periodic","ExtendedAsphere","ExtendedOddAsphere","ExtendedPolynomial",
            "Conjugate","ABCD","RetroReflect","JonesMatrix"]
        result["surface_numeric_reference_scopes"]={
            "OddAsphere":"signed radial coefficients; cusp Sag only at vertex; smooth normals/refraction away from cusp",
            "Biconic":"unequal/swapped principal radii and conics; infinite X radius; Sag/normal/refraction",
            "Conjugate":"real/virtual/off-axis construction points; vertex branch distance equation and reflection",
            "ABCD":"separate X/Y first-order matrices on (height, l/n or m/n); geometric rays only, no OPD reference",
            "RetroReflect":"air/glass plane and MIRROR reverse propagation; raw sequential cosines distinguished from physical propagation",
            "JonesMatrix":"axial incidence, normalized X/Y/45deg/circular input; identity/linear/quarter-wave/real rotation; common phase removed with identity reference",
            "extended_parameters":"term participation, signed coefficients and normalization; supported Fixed/Variable/same-column pickup, protection and zos/zmx reload; see evidence",
            "evidence":"docs/model-adaptation.md#顺序面型与求解范围"}
        result["surface_type_scope_note"]="原生可选枚举与上述受控模型数值范围分别解释；其他面型不自动视为已适配。"
        result["beam_file_formats"]={"zbf_binary_v1":"native_asymmetric_polarized_field_reference","zbf_text_v1":"native_asymmetric_polarized_field_reference"}
        result["analysis_image_sources"]={"data_plot":"saved_data_only","native":"existing_native_image_artifact_only; no general IAR bitmap export"}
        result["pop_dll_adapters"]={
            "parameter_metadata":"ZOS-API first; known installed DLL UserParamNames queried in a bounded isolated no-window process on metadata failure",
            "supported_files":["beamsamp1.DLL","Laguerre beam.dll","Ince-Gaussian-64.dll"],
            "beam_and_receiver":"native calls and identical-mode coupling verified for the three listed files",
            "independent_field_reference":{"beamsamp1.DLL":"installed Gaussian source second moments","Laguerre beam.dll":"installed n=0,l=1 source second moments","Ince-Gaussian-64.dll":"p=m=2, even/odd, f0=0.05/0.1mm, w0=0.1mm: independent whole-waist irradiance and signed relative complex field; other orders/propagated phase pending"}}
        result["pop_coupling_definition"]="polarized receiver efficiency is a power-weighted mean of separately normalized component overlaps; not a single normalized vector inner product"
        result["tolerance_trial_status"]={"verified_format":"OpticStudio 2024 R2 Chinese Monte Carlo trial table",
            "mapping":"complete one-based trial IDs, zero-based row indices, displayed criterion precision and traceable count must agree",
            "failed_trials":"explicit untraceable trials excluded from moments and counted as failed in requested-sample yield; raw finite sentinel retained",
            "unrecognized_format":"SAMPLE_STATUS_UNAVAILABLE when failures cannot be mapped"}
        if connected and not self.active:
            from .analyses import ANALYSES
            available=set(self.native.enum_names(self.native.api.Analysis.AnalysisIDM))
            result["analyses"]={name:{"implemented":True,"api_available":native_id in available,"license_checked_per_run":True,"verification":"调用和数值验证范围见 docs/capabilities.md"}for name,native_id in ANALYSES.items()}
            for name in ('vignetting','footprint'):
                result['analyses'][name].update(methods=['auto','ray_trace'],native_settings_readback=False,source='native_batch_ray_trace')
            for name,method in [('yybar_diagram','native_PARY_and_paraxial_batch_validity'),('incident_angle_vs_image_height','native_real_batch_trace_with_image_material_control')]:
                result['analyses'][name].update(computation_method=method,
                    settings_source='typed native ray arguments and renderer settings',
                    verification='accepted; verification/development/CV-02/acceptance400-ray-diagrams.json')
            result['analyses']['sag_table'].update(computation_method='native_BFSD_or_SSAG_GetSag_SSLP',
                settings_source='typed native query arguments',supported_criterion='MinimumVolume',
                curve_criteria=['MinimumVolume','MinimumRMS','MinimumRMSWithOffset'],
                reverse_scope='MinimumVolume full-aperture SSAG sphere only',
                alternate_criterion_scope='full-aperture SSAG sphere curve; MinimumRMS vertex offset fixed zero, other offsets unavailable; removal statistics apply only to MinimumVolume',
                rms_bfs_auxiliary='DSAG Data9 radius and Data10 raw native Z offset; includes SSAG radius consistency; conversion to manufacturing vertex_offset unconfirmed',
                summary_sampling='native BFSD; independent of requested rows; observed1000 intervals including endpoints with radial RMS weights',
                applicability='rotational Y-section; sampled native sag meridians reject witnessed asymmetry',
                aperture_scope='full radial blank; aperture-present SSLP uses an owned unclipped copy; active-model slope retained',
                verification='implemented; verification/development/MF-01/progress589-offset-reference.json')
            result['analyses']['grin_profile'].update(
                source_readback='task.settings.source_surface: surface type,material,dimensions,current configuration; Gradium includes profile file and parameters1–8',
                gradium_reference_index='RefN is evaluated at the material-family reference wavelength, separate from requested system wavelength',
                gradium_verification='in_progress; original numeric gate retained; shared-dispersion and capping diagnostics recorded separately')
            result['analyses']['full_field_spot'].update(
                coordinate_units='spatial radii: micrometers; spatial reference: lens units; direction-cosine mode: dimensionless',
                shared_reference='all fields share reference; ChiefRay uses field1',
                result_limitation='Cooke native text and structured outlets unavailable; no validated shared-reference substitute',
                verification='implemented; verification/development/CV-01/progress533-full-field.json')
            result['analyses']['fft_line_edge_spread'].update(
                verification='accepted; verification/development/CV-01/acceptance547-spread.json',
                independent_coherent_reference='direct OPD/intensity rays on documented FFT-stretched pupil nodes at64/128 sampling; physical Fraunhofer sum',
                scalar_interpolation='complex identities checked at original FFT knots; native display interpolates exported scalar quantities independently')
            result['analyses']['test_plate_list'].update(methods=['auto','native','file'],
                units={'radius':'millimeters','diameter':'millimeters'},resource_kind='test_plate_files',
                native_settings_readback=False,native_active_catalog_readback='formatted report header',
                requested_native_catalog_selection='unconfirmed; mismatched catalog explicitly refused',
                file_method='documented TPD resource format; selected filename and source recorded',
                verification='implemented; verification/development/MF-01/progress435-plates.json')
            for name in ('paraxial_gaussian_beam','skew_gaussian_beam'):
                result['analyses'][name].update(computation_method='native_gaussian_merit_operands',
                    settings_source='typed native query arguments',verification='accepted; verification/development/WP-01/acceptance362-gaussian.json')
        if connected and not self.active:
            data = self.system.SystemData
            result['property_enums']={}
            for group,(attribute,mapping) in SYSTEM_PAGES.items():
                obj=getattr(data,attribute)
                result['property_enums'][group]={key:self.native.property_enum_names(obj,name) for key,(name,_) in mapping.items() if obj.GetType().GetProperty(name).PropertyType.IsEnum}
            if str(self.system.Mode)=='Sequential':
                row=self._row(1)
                for group,(attribute,mapping) in SURFACE_PAGES.items():
                    obj=getattr(row,attribute)
                    result['property_enums'][group]={key:self.native.property_enum_names(obj,name) for key,(name,_) in mapping.items() if obj.GetType().GetProperty(name).PropertyType.IsEnum}
            result["available_settings"] = {
                "aperture_type": self.native.property_enum_names(data.Aperture, "ApertureType"),
                "field_type": self.native.enum_names(self.native.api.SystemData.FieldType),
                "lens_units": self.native.property_enum_names(data.Units, "LensUnits"),
                "mtf_units": self.native.property_enum_names(data.Units, "MTFUnits"),
                "source_units":self.native.property_enum_names(data.Units,"SourceUnits"),
                "source_unit_prefix":self.native.property_enum_names(data.Units,"SourceUnitPrefix"),
                "analysis_units":self.native.property_enum_names(data.Units,"AnalysisUnits"),
                "analysis_unit_prefix":self.native.property_enum_names(data.Units,"AnalysisUnitPrefix"),
                "polarization_method": self.native.property_enum_names(data.Polarization,"Method"),
                "ray_aiming_mode": self.native.property_enum_names(data.RayAiming,"RayAiming"),
                "ray_aiming_method": self.native.property_enum_names(data.RayAiming,"Method"),
                "field_normalization": self.native.property_enum_names(data.Fields,"Normalization"),
            }
            editor=self.system.NCE
            for kind,methods in {
                "DetectorRectangle":["GetAllDetectorDataSafe","GetAllCoherentDataSafe"],
                "DetectorPolar":["GetAllPolarDetectorDataSafe","GetPolarDetectorData"],
                "DetectorColor":["GetAllColorDetectorDataSafe","GetColorDetectorData"],
                "DetectorVolume":["GetDetectorData"],"DetectorSurface":["GetDetectorData","GetDetectorSize"],
            }.items():
                result["detector_adapters"][kind]["api_available"]=all(hasattr(editor,m) for m in methods)
            result["available_nsc_object_types"]=self.native.enum_names(self.native.api.Editors.NCE.ObjectType)
            result["available_cad_formats"]=self.native.enum_names(self.native.api.Tools.General.CADFileType)
            from .exports import CAD_EXTENSIONS
            unsupported={"ASAT","ASAB","MODEL","CATPART","CATPRODUCT","XCGM"}
            result["cad_formats"]={name:{"extensions":sorted(extensions),"local_2024_r2_test":"native_rejected"if name in unsupported else"native_succeeded","reason":"Unsupported export format"if name in unsupported else None,"license_checked_per_run":True}for name,extensions in CAD_EXTENSIONS.items()}
            layout_owner=getattr(self.system.Tools,"Layouts",None)
            result["layout_exports"]={kind:dict(api_available=hasattr(layout_owner,method),mode=mode,license_checked_per_run=True)for kind,method,mode in [("cross_section","OpenCrossSectionExport","Sequential"),("viewer_3d","Open3DViewerExport","Sequential"),("shaded_model","OpenShadedModelExport","Sequential"),("nsc_3d","OpenNSC3DLayoutExport","NonSequential"),("nsc_shaded","OpenNSCShadedModelExport","NonSequential")]}
        if topic == "settings":
            return {"connected":connected,"available_settings":result.get("available_settings",{}),
                    "availability":"native_readback" if connected and not self.active else "connect_and_wait_for_idle"}
        return result

    def new_system(self, req):
        if self.work_path:
            self._checkpoint("before_new")
        self.revision += 1
        self._engineering_mapping_valid=False
        # The old file must not become the save target of a partially created model.
        self.work_path = None
        self.source_path = None
        self.system_context = {}
        self._reset_detector_history(False)
        self.system.New(False)
        if req.mode=="Sequential":self.system.MakeSequential()
        elif not self.system.MakeNonSequential():raise ZemaxError("MODE_CHANGE_FAILED","原生非序列创建失败。")
        self._reset_detector_history(True)
        self._working_copy()
        return self.get_system_summary(None)

    def open_lens(self, req):
        if not Path(req.path).is_absolute():
            raise ZemaxError("INVALID_ARGUMENT", "镜头路径须为绝对路径。")
        path = Path(req.path).resolve()
        if not path.is_file() or path.suffix.lower() not in {".zos", ".zmx"}:
            raise ZemaxError("INVALID_INPUT_FILE", "需要现有的 .zos 或 .zmx 镜头文件。", path=str(path))
        if self.work_path:
            self._checkpoint("before_open")
        self.revision += 1
        self._engineering_mapping_valid=False
        if not self.system.LoadFile(str(path), False):
            raise ZemaxError("LOAD_FAILED", "原生接口未能加载镜头文件。", path=str(path))
        self.source_path = str(path)
        self._reset_detector_history(False)
        self.work_path = None
        self.system_context = {}
        self._working_copy()
        return self.get_system_summary(None)

    def save_lens_as(self, req):
        if not self.work_path:
            raise ZemaxError("NO_WORKING_MODEL", "请先新建或打开镜头。")
        if not Path(req.path).is_absolute():
            raise ZemaxError("INVALID_ARGUMENT", "输出路径须为绝对路径。")
        path = Path(req.path).resolve()
        if path.suffix.lower() not in {".zos", ".zmx"}:
            raise ZemaxError("INVALID_OUTPUT_FILE", "输出扩展名须为 .zos 或 .zmx。")
        if path.exists() and not req.overwrite:
            raise ZemaxError("OUTPUT_EXISTS", "目标已存在；覆盖需要 overwrite=true。", path=str(path))
        if getattr(self.system,'IsProjectDirectory',False):
            self._copy_project_resources(self.work_path.parent,path.parent)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.system.SaveAs(str(path))
        self.system.SaveAs(str(self.work_path))
        return {"path": str(path), "artifacts": [{"kind": "lens", "path": str(path)}]}

    def disconnect(self, req):
        if self.work_path and not self.requires_reconnect:
            self._checkpoint("disconnect")
        try:
            self.native.disconnect()
        except Exception:
            self.requires_reconnect = True
            raise
        result = {"connected": False, "last_session": self.context()}
        self.session_id = None
        self.work_path = None
        self.source_path = None
        self.directory = None
        self.version = None
        self.build_id = None
        self.system_context = {}
        self.license = None
        self.last_checkpoint = None
        self.requires_reconnect = False
        return result

    def get_system_settings(self, req):
        data = self.system.SystemData
        fields = data.Fields
        waves = data.Wavelengths
        self.system_context = {"mode": str(self.system.Mode), "configuration": int(self.system.MCE.CurrentConfiguration),
                               "lens_units": str(data.Units.LensUnits), "mtf_units": str(data.Units.MTFUnits)}
        return {
            "mode": str(self.system.Mode), "configuration": int(self.system.MCE.CurrentConfiguration),
            "lens_units": str(data.Units.LensUnits), "mtf_units": str(data.Units.MTFUnits),
            "source_units":str(data.Units.SourceUnits),"source_unit_prefix":str(data.Units.SourceUnitPrefix),
            "analysis_units":str(data.Units.AnalysisUnits),"analysis_unit_prefix":str(data.Units.AnalysisUnitPrefix),
            "afocal_image_space": bool(data.Aperture.AFocalImageSpace),
            "aperture": {"type": str(data.Aperture.ApertureType), "value": float(data.Aperture.ApertureValue)},
            "field_type": str(fields.GetFieldType()), "field_normalization": str(fields.Normalization),
            "fields": [{"number": i, "x": float(fields.GetField(i).X), "y": float(fields.GetField(i).Y),
                        "weight": float(fields.GetField(i).Weight), **{k.lower(): float(getattr(fields.GetField(i),k)) for k in ("VDX","VDY","VCX","VCY","VAN")}} for i in range(1, fields.NumberOfFields + 1)],
            "wavelength_unit": "micrometers (environmental air reference)",
            "wavelengths": [{"number": i, "wavelength_um": float(waves.GetWavelength(i).Wavelength),
                             "weight": float(waves.GetWavelength(i).Weight),
                             "primary": bool(waves.GetWavelength(i).IsPrimary)} for i in range(1, waves.NumberOfWavelengths + 1)],
            "temperature_c": float(data.Environment.Temperature), "pressure_atm": float(data.Environment.Pressure),
            "adjust_index_to_environment": bool(data.Environment.AdjustIndexToEnvironment),
            **self._extended_settings(),
            "title": str(data.TitleNotes.Title), "notes": str(data.TitleNotes.Notes),
        }

    def get_system_summary(self, req):
        result = self.get_system_settings(None)
        result["surface_count"] = int(self.system.LDE.NumberOfSurfaces)
        result["native_system_status"] = str(self.system.GetCurrentStatus())
        if str(self.system.Mode) == "Sequential":
            values = self.system.LDE.GetFirstOrderData()
            result["first_order"] = dict(zip(
                ("effective_focal_length", "paraxial_working_f_number", "real_working_f_number",
                 "paraxial_image_height", "paraxial_magnification"), map(float, values)))
        return result

    def update_system_settings(self, req):
        if str(self.system.Mode)!="Sequential" and any(getattr(req,k) is not None for k in ("fields","field_updates","field_type","field_normalization","vignetting_action","ray_aiming","aperture_type","aperture_value","global_reference_surface")):
            raise ZemaxError("UNSUPPORTED_MODE","非序列系统通过光源和对象定义光线与孔径；此请求含顺序系统设置。")
        data = self.system.SystemData
        # Validate enum names and dependent bounds before any native write.
        for key, obj, attr in (("lens_units", data.Units, "LensUnits"), ("mtf_units", data.Units, "MTFUnits"),
                               ("aperture_type", data.Aperture, "ApertureType")):
            value = getattr(req, key)
            if value is not None:
                self.native.enum(obj.GetType().GetProperty(attr).PropertyType, value)
        if req.field_type:
            self.native.enum(self.native.api.SystemData.FieldType, req.field_type)
        wave_count = len(req.wavelengths) if req.wavelengths else data.Wavelengths.NumberOfWavelengths
        if req.primary_wavelength and req.primary_wavelength > wave_count:
            raise ZemaxError("INDEX_OUT_OF_RANGE", "主波长编号超出范围。")
        self._validate_settings_extension(req)
        self._mutate("settings")
        self._apply_settings_extension(req)
        for key, obj, attr in (("lens_units", data.Units, "LensUnits"), ("mtf_units", data.Units, "MTFUnits"),
                               ("aperture_type", data.Aperture, "ApertureType")):
            value = getattr(req, key)
            if value is not None:
                self.native.set_enum(obj, attr, value)
        if req.aperture_value is not None:
            data.Aperture.ApertureValue = req.aperture_value
        if req.field_type:
            data.Fields.SetFieldType(self.native.enum(self.native.api.SystemData.FieldType, req.field_type))
        if req.fields is not None:
            while data.Fields.NumberOfFields > 1:
                data.Fields.DeleteFieldAt(data.Fields.NumberOfFields)
            for i, point in enumerate(req.fields):
                f = data.Fields.GetField(1) if i == 0 else data.Fields.AddField(point.x, point.y, point.weight)
                f.X, f.Y, f.Weight = point.x, point.y, point.weight
                for k in ("vdx","vdy","vcx","vcy","van"): setattr(f,k.upper(),getattr(point,k))
        if req.wavelengths is not None:
            while data.Wavelengths.NumberOfWavelengths > 1:
                data.Wavelengths.RemoveWavelength(data.Wavelengths.NumberOfWavelengths)
            for i, wave in enumerate(req.wavelengths):
                previous_count = int(data.Wavelengths.NumberOfWavelengths)
                w = data.Wavelengths.GetWavelength(1) if i == 0 else data.Wavelengths.AddWavelength(wave.wavelength_um, wave.weight)
                if w is None or i > 0 and int(data.Wavelengths.NumberOfWavelengths) != previous_count + 1:
                    raise ZemaxError("SETTING_REJECTED", "原生波长表未添加请求项。",
                                     setting="wavelengths", wavelength_number=i+1,
                                     requested_count=len(req.wavelengths), actual_count=int(data.Wavelengths.NumberOfWavelengths))
                w.Wavelength, w.Weight = wave.wavelength_um, wave.weight
                if not math.isclose(float(w.Wavelength), wave.wavelength_um, rel_tol=1e-7, abs_tol=1e-12) or not math.isclose(float(w.Weight), wave.weight, rel_tol=1e-7, abs_tol=1e-12):
                    raise ZemaxError("SETTING_REJECTED", "原生波长表未采用请求值。",
                                     setting="wavelengths", wavelength_number=i+1,
                                     requested=dict(wavelength_um=wave.wavelength_um, weight=wave.weight),
                                     actual=dict(wavelength_um=float(w.Wavelength), weight=float(w.Weight)))
        if req.primary_wavelength:
            data.Wavelengths.GetWavelength(req.primary_wavelength).MakePrimary()
        for key, attr in (("adjust_index_to_environment", "AdjustIndexToEnvironment"),
                          ("temperature_c", "Temperature"), ("pressure_atm", "Pressure")):
            value = getattr(req, key)
            if value is not None:
                setattr(data.Environment, attr, value)
                actual = getattr(data.Environment, attr)
                if actual != value:
                    raise ZemaxError("SETTING_REJECTED", "原生环境设置未采用请求值。",
                                     setting=key, requested=value, actual=actual)
        if req.title is not None:
            data.TitleNotes.Title = req.title
        if req.notes is not None:
            data.TitleNotes.Notes = req.notes
        return self.get_system_settings(None)

    def _surface_data(self, index, parameter_start=1, parameter_count=20):
        row = self._row(index)
        result = {"surface": index, "surface_type": str(row.Type), "comment": str(row.Comment),
                  "is_object": bool(row.IsObject), "is_image": bool(row.IsImage), "is_stop": bool(row.IsStop),
                  "cells": {}, "properties": self._surface_properties(row)}
        for name, cell in self._cells(row,parameter_start,parameter_count):
            solve = {"type": str(cell.Solve)}
            if str(cell.Solve) == "SurfacePickup":
                p = cell.GetSolveData()._S_SurfacePickup
                solve.update(source_surface=int(p.Surface),
                             scale=float(p.ScaleFactor) if p.SupportsScale else None,
                             offset=float(p.Offset) if p.SupportsOffset else None,
                             supports_scale=bool(p.SupportsScale), supports_offset=bool(p.SupportsOffset),
                             source_column=str(p.Column))
            elif str(cell.Solve) == "FNumber":
                solve["f_number"] = float(cell.GetSolveData()._S_FNumber.FNumber)
            canonical=SOLVE_ALIASES.get(str(cell.Solve),str(cell.Solve))
            if canonical in SOLVE_FIELDS:
                obj=getattr(cell.GetSolveData(),"_S_"+canonical)
                solve.update({k:getattr(obj,v) for k,v in SOLVE_FIELDS[canonical].items()})
            result["cells"][name] = {"value": self._cell_value(cell), "solve": solve,
                                     "writable": not bool(cell.IsReadOnly), "header": str(cell.Header),
                                     "available_solves": [str(x) for x in cell.GetAvailableSolveTypes()]}
            if str(row.Type) == "Hologram2" and name == "parameter_13":
                result["cells"][name]["solve_persistence"] = self._hologram2_persistence(self._cell_value(cell))
        return result

    def get_surfaces(self, req):
        self._require_sequential()
        total = int(self.system.LDE.NumberOfSurfaces)
        if req.start >= total:
            raise ZemaxError("INDEX_OUT_OF_RANGE", "起始曲面超出范围。")
        end = min(total, req.start + req.count)
        return {"total": total, "surfaces": [self._surface_data(i,req.parameter_start,req.parameter_count) for i in range(req.start, end)],
                "parameter_start":req.parameter_start,"parameter_count":min(req.parameter_count,255-req.parameter_start),
                "next_start": end if end < total else None, "units": str(self.system.SystemData.Units.LensUnits)}

    def _validate_solve(self, row, name, spec):
        cell = self._cell(row, name)
        mode = SOLVES[spec.mode]
        if not cell.IsSolveTypeSupported(self.native.enum(self.native.api.Editors.SolveType, mode)):
            raise ZemaxError("UNSUPPORTED_SOLVE", "此单元格不支持所选 solve。", cell=name, solve=mode)
        if getattr(spec,"source_surface",None) is not None:
            self._row(spec.source_surface)
            if spec.mode=="surface_pickup" and spec.source_surface == row.SurfaceNumber:
                raise ZemaxError("INVALID_SOLVE", "禁止自引用 pickup。")
        if spec.mode == "pickup_chief_ray" and (spec.field > self.system.SystemData.Fields.NumberOfFields or spec.wavelength > self.system.SystemData.Wavelengths.NumberOfWavelengths):
            raise ZemaxError("INDEX_OUT_OF_RANGE", "solve 视场或波长越界。")
        if getattr(spec,"source_column",None):
            self.native.enum(self.native.api.Editors.LDE.SurfaceColumn, spec.source_column)
        if spec.mode == "surface_pickup":
            pickup = cell.CreateSolveType(self.native.api.Editors.SolveType.SurfacePickup)._S_SurfacePickup
            column = spec.source_column or COLUMNS.get(name, name.replace("parameter_", "Par"))
            pickup.Column = self.native.enum(self.native.api.Editors.LDE.SurfaceColumn, column)
            if (not pickup.SupportsScale and spec.scale != 1) or (not pickup.SupportsOffset and spec.offset != 0):
                raise ZemaxError("UNSUPPORTED_SOLVE_PARAMETER", "此拾取不支持请求的比例或偏移。",
                                 cell=name, supports_scale=bool(pickup.SupportsScale),
                                 supports_offset=bool(pickup.SupportsOffset))

        if spec.mode in {"concentric_surface","concentric_radius","center_of_curvature","compensator"} and spec.source_surface >= row.SurfaceNumber:
            raise ZemaxError("INVALID_SOLVE","此求解要求参考面位于目标面之前。",source_surface=spec.source_surface,surface=int(row.SurfaceNumber))
        if spec.mode=="maximum" and self.system.MCE.NumberOfConfigurations < 2:
            raise ZemaxError("INVALID_SOLVE","Maximum 要求至少两个配置；单配置原生回退为 Automatic。")
        if spec.mode=="element_power" and row.SurfaceNumber < 2:
            raise ZemaxError("INVALID_SOLVE","ElementPower 要求目标面编号至少为2。")
        if spec.mode=="material_substitute" and spec.catalog:
            catalogs=[str(x) for x in self.system.SystemData.MaterialCatalogs.GetCatalogsInUse()]
            if spec.catalog not in catalogs:
                raise ZemaxError("INVALID_RESOURCE","替代玻璃目录须为当前已启用目录。",catalog=spec.catalog,available=catalogs)
        if spec.mode=="zpl_macro":
            macros=list(cell.CreateSolveType(self.native.api.Editors.SolveType.ZPLMacro)._S_ZPLMacro.GetAvailableMacros())
            if spec.macro not in macros:
                raise ZemaxError("INVALID_RESOURCE","宏名称不在原生可用列表中。",macro=spec.macro,available=macros)

    def _set_solve(self, row, name, spec):
        cell = self._cell(row, name)
        self._validate_hologram2_mode(row, name, SOLVES[spec.mode])
        if spec.mode in ("fixed","variable"):
            self._set_variable_mode(cell,spec.mode=="variable")
        elif spec.mode == "surface_pickup":
            solve = cell.CreateSolveType(self.native.api.Editors.SolveType.SurfacePickup)
            pickup = solve._S_SurfacePickup
            pickup.Surface = spec.source_surface
            column = spec.source_column or COLUMNS.get(name, name.replace("parameter_", "Par"))
            pickup.Column = self.native.enum(self.native.api.Editors.LDE.SurfaceColumn, column)
            if pickup.SupportsScale:
                pickup.ScaleFactor = spec.scale
            if pickup.SupportsOffset:
                pickup.Offset = spec.offset
            self._checked_set_solve(cell,solve)
        elif spec.mode == "f_number":
            solve = cell.CreateSolveType(self.native.api.Editors.SolveType.FNumber)
            solve._S_FNumber.FNumber = spec.f_number
            self._checked_set_solve(cell,solve)

        elif SOLVES[spec.mode] in SOLVE_FIELDS:
            mode=SOLVES[spec.mode]
            solve=cell.CreateSolveType(self.native.enum(self.native.api.Editors.SolveType,mode))
            obj=getattr(solve,"_S_"+mode)
            for key,attr in SOLVE_FIELDS[mode].items(): setattr(obj,attr,getattr(spec,key))
            self._checked_set_solve(cell,solve)

        actual=str(cell.Solve)
        if SOLVE_ALIASES.get(actual,actual) != SOLVES[spec.mode]:
            raise ZemaxError("SOLVE_UPDATE_FAILED", "原生单元格未采用请求的求解模式。", requested=SOLVES[spec.mode], actual=actual, cell=name)

        if spec.mode not in ("fixed","variable","surface_pickup","f_number"):
            from .detectors import check_setting_value
            obj=getattr(cell.GetSolveData(),"_S_"+SOLVES[spec.mode])
            for key,attr in SOLVE_FIELDS[SOLVES[spec.mode]].items():
                check_setting_value(key,getattr(spec,key),getattr(obj,attr))

    @staticmethod
    def _set_variable_mode(cell,variable):
        requested="Variable" if variable else "Fixed"
        status=cell.MakeSolveVariable() if variable else cell.MakeSolveFixed()
        actual=str(cell.Solve)
        if not status or actual!=requested:
            raise ZemaxError("SOLVE_UPDATE_FAILED","原生变量/固定模式未采用请求值。",
                             requested=requested,actual=actual,native_return=bool(status))

    @staticmethod
    def _checked_set_solve(cell,solve):
        if not solve.IsValid:
            raise ZemaxError("INVALID_SOLVE", "原生 solve 无效。")
        status=cell.SetSolveData(solve)
        if str(status) != "Success":
            raise ZemaxError("SOLVE_UPDATE_FAILED", "原生 solve 设置失败。",status=str(status))

    def _failure_surface_state(self,index):
        try:return self._surface_data(index)
        except Exception as exc:return dict(surface=index,state_unavailable=str(exc))

    def update_surfaces(self, req):
        self._validate_hologram2_batch(req.changes)
        plans = []
        for change in req.changes:
            row = self._row(change.surface)
            target_type = change.surface_type or str(row.Type)
            if target_type in {"ExtendedAsphere", "ExtendedOddAsphere", "ExtendedPolynomial"} and 13 in change.parameters:
                # Term-count writes can disable cells later in the same request.
                # Reject that known conflict before a checkpoint or native write.
                maximum = int(change.parameters[13])
                requested_parameters = set(change.parameters)
                requested_parameters.update(int(name[10:]) for name in change.solves if name.startswith("parameter_"))
                disabled = sorted(i for i in requested_parameters if i >= 15 and i > 14 + maximum)
                if disabled:
                    raise ZemaxError("CELL_NOT_WRITABLE", "请求的最大项数未启用所修改的系数。",
                                     surface=change.surface, surface_type=target_type,
                                     maximum_term=maximum, inactive_parameters=disabled)
            values = {name: getattr(change, name) for name in BASE_CELLS if getattr(change, name) is not None}
            values.update({f"parameter_{i}": v for i, v in change.parameters.items()})
            if change.surface_type:
                self.native.enum(self.native.api.Editors.LDE.SurfaceType, change.surface_type)
                if change.surface_type not in [str(x) for x in row.AvailableSurfaceTypes()]:
                    raise ZemaxError("UNSUPPORTED_SURFACE_TYPE","本机曲面不支持此类型。")
                # Type changes can discard type-specific parameters and solves.
                if not change.replace_solves and str(row.Type) != change.surface_type:
                    raise ZemaxError("SOLVE_PROTECTED", "改变面型需要 replace_solves=true，以确认面型参数和关系的变化。")
            if change.surface_file is not None:
                target=change.surface_type or str(row.Type)
                settings=row.GetSurfaceTypeSettings(self.native.enum(self.native.api.Editors.LDE.SurfaceType,target))
                if not settings.RequiresFile or change.surface_file not in [str(x)for x in settings.GetFileNames()]:
                    raise ZemaxError("INVALID_RESOURCE","面型文件不在本机可用列表中。")
            if change.import_file is not None:
                from .files import input_path
                input_path(change.import_file,{".dat"})
                if (change.surface_type or str(row.Type)) not in {"GridSag","GridPhase"}:
                    raise ZemaxError("UNSUPPORTED_SURFACE_TYPE","当前外部数据导入适配 GridSag/GridPhase。")
                if not change.replace_solves:raise ZemaxError("SOLVE_PROTECTED","导入面型数据需要 replace_solves=true。")
            for name in values:
                if name.startswith("parameter_") and change.surface_type and str(row.Type) != change.surface_type:
                    continue
                self._guard_cell(self._cell(row, name), change.replace_solves)
            for name, spec in change.solves.items():
                if change.surface_type and str(row.Type) != change.surface_type:
                    continue
                self._guard_cell(self._cell(row, name), change.replace_solves)
                self._validate_solve(row, name, spec)
            self._validate_surface_extension(row, change)
            plans.append((change, values))
        self._validate_aperture_batch(req.changes)
        self._mutate("surfaces")
        completed = []
        try:
            # Remove replaced edges first, so a valid final DAG never creates a
            # temporary cycle when updates reverse an existing dependency.
            for change, _ in plans:
                if change.aperture is not None:
                    aperture = self._row(change.surface).ApertureData
                    if aperture.IsPickedUp:
                        aperture.SetPickupNone()
            for change, values in plans:
                row = self._row(change.surface)
                if change.surface_type or change.surface_file is not None:
                    settings=row.GetSurfaceTypeSettings(self.native.enum(self.native.api.Editors.LDE.SurfaceType,change.surface_type or str(row.Type)))
                    if change.surface_file is not None:settings.Filename=change.surface_file
                    if not row.ChangeType(settings):
                        raise ZemaxError("SURFACE_TYPE_FAILED", "面型切换失败。")
                    self._validate_surface_extension(row,change)
                if change.import_file is not None and not row.ImportData.ImportDataFile(change.import_file):
                    raise ZemaxError("IMPORT_FAILED","原生曲面数据导入失败。")
                for name, value in values.items():
                    cell = self._cell(row, name)
                    self._guard_cell(cell, change.replace_solves)
                    if change.replace_solves and str(cell.Solve) not in ("Fixed", "Variable"):
                        self._set_variable_mode(cell, False)
                    self._write_cell(cell, value, zero_radius=name=='radius')
                if change.comment is not None:
                    row.Comment = change.comment
                for name, spec in change.solves.items():
                    self._guard_cell(self._cell(row,name),change.replace_solves)
                    self._validate_solve(row,name,spec)
                    self._set_solve(row, name, spec)
                self._apply_surface_extension(row, change)
                completed.append(change.surface)
        except Exception as exc:
            raise ZemaxError("PARTIAL_UPDATE", str(exc), completed_surfaces=completed,
                             checkpoint=self.last_checkpoint, current_revision=self.revision,
                             failed_surface=change.surface,failed_surface_state=self._failure_surface_state(change.surface),
                             cause=exc.as_dict() if isinstance(exc,ZemaxError) else {"code":"NATIVE_ERROR","message":str(exc)}) from exc
        result={"surfaces": [self._surface_data(i) for i in completed]}
        for change in req.changes:
            extra=set(change.parameters)|{int(n.removeprefix('parameter_'))for n in change.solves if n.startswith('parameter_')}
            if any(i>20 for i in extra):
                row=self._row(change.surface)
                result.setdefault('updated_parameters',[]).append(dict(surface=change.surface,
                    cells={str(i):dict(value=self._cell_value(self._cell(row,'parameter_'+str(i))),solve=str(self._cell(row,'parameter_'+str(i)).Solve))for i in sorted(extra)}))
        return result

    def insert_surfaces(self, req):
        self._require_sequential()
        if req.at >= self.system.LDE.NumberOfSurfaces:
            raise ZemaxError("INDEX_OUT_OF_RANGE", "插入位置须在像面之前。")
        self._mutate("insert")
        for _ in range(req.count):
            self.system.LDE.InsertNewSurfaceAt(req.at)
        return {"inserted_at": req.at, "count": req.count, "total": int(self.system.LDE.NumberOfSurfaces)}

    def delete_surfaces(self, req):
        self._require_sequential()
        if req.at + req.count > self.system.LDE.NumberOfSurfaces - 1:
            raise ZemaxError("INDEX_OUT_OF_RANGE", "不能删除物面或像面，删除范围须在两者之间。")
        self._mutate("delete")
        for _ in range(req.count):
            self.system.LDE.RemoveSurfaceAt(req.at)
        return {"removed_at": req.at, "count": req.count, "total": int(self.system.LDE.NumberOfSurfaces)}

    def get_variables(self, req):
        if str(self.system.Mode)=="NonSequential":return self._nsc_variables()
        self._require_sequential()
        variables = []
        for i in range(self.system.LDE.NumberOfSurfaces):
            for name, cell in self._cells(self._row(i)):
                if str(cell.Solve) == "Variable":
                    variables.append({"surface": i, "cell": name, "value": self._cell_value(cell)})
        m=getattr(self.system,"MCE",None)
        if m is not None:
            for i in range(1,m.NumberOfOperands+1):
                for c in range(1,m.NumberOfConfigurations+1):
                    cell=m.GetOperandAt(i).GetOperandCell(c)
                    if str(cell.Solve)=="Variable":variables.append(dict(scope="configuration",operand=i,configuration=c,value=self._cell_value(cell)))
        return {"variables": variables}

    def set_variables(self, req):
        from .models import SolveSpec
        plans=[]
        for item in req.variables:
            if hasattr(item,"object"):
                cell=self._nsc_cell(item.object,item.cell)
                if not cell.IsSolveTypeSupported(self.native.enum(self.native.api.Editors.SolveType,"Variable"if item.variable else"Fixed")):raise ZemaxError("UNSUPPORTED_SOLVE","此对象单元格不支持变量。")
            elif hasattr(item,"operand"):
                self._require_sequential();self._configuration_number(item.configuration)
                if item.operand>self.system.MCE.NumberOfOperands:raise ZemaxError("INDEX_OUT_OF_RANGE","MCE 操作数越界。")
                cell=self.system.MCE.GetOperandAt(item.operand).GetOperandCell(item.configuration)
                if not cell.IsSolveTypeSupported(self.native.enum(self.native.api.Editors.SolveType,"Variable"if item.variable else"Fixed")):raise ZemaxError("UNSUPPORTED_SOLVE","此配置单元格不支持变量。")
            else:
                row = self._row(item.surface)
                cell = self._cell(row, item.cell)
                self._validate_hologram2_mode(row, item.cell, "Variable" if item.variable else "Fixed")
                self._validate_solve(row, item.cell, SolveSpec(mode="variable" if item.variable else "fixed"))
            self._guard_cell(cell, item.replace_solve)
            plans.append((cell,item.variable))
        self._mutate("variables")
        for index,(cell,variable) in enumerate(plans):
            try:
                self._set_variable_mode(cell,variable)
            except ZemaxError as exc:
                exc.details.update(failed_index=index,completed_count=index)
                raise
        return self.get_variables(None)

    def get_merit_function(self, req):
        self._require_work()
        mfe = self.system.MFE
        # Keep the response bounded even for a wizard-generated merit function.
        start, count = (req.start, req.count) if req is not None else (1, 100)
        if start > mfe.NumberOfOperands:
            raise ZemaxError("INDEX_OUT_OF_RANGE", "操作数起始编号超出范围。")
        end = min(mfe.NumberOfOperands + 1, start + count)
        operands = []
        for i in range(start, end):
            row = mfe.GetOperandAt(i)
            parameters, cells = {}, {}
            for j in range(2, 10):
                cell = row.GetCellAt(j)
                cells[str(j)] = {"column":j,"header":str(cell.Header),"data_type":str(cell.DataType),
                                 "active":bool(cell.IsActive),"writable":bool(cell.IsActive and not cell.IsReadOnly),
                                 "unit":None,"unit_source":None}
                if cell.IsActive:
                    parameters[str(j)] = {**cells[str(j)],"value": self._cell_value(cell)}
            operands.append({"operand": i, "type": str(row.Type), "target": float(row.Target),
                             "weight": float(row.Weight), "value": float(row.Value),
                             "contribution": float(row.Contribution), "parameters": parameters,"cells":cells})
        return {"total": int(mfe.NumberOfOperands), "operands": operands,
                "next_start": end if end <= mfe.NumberOfOperands else None, "values_are_cached": True}

    def update_merit_function(self, req):
        self._require_sequential()
        mfe = self.system.MFE
        initial_count = int(mfe.NumberOfOperands)
        completed, removed, added, current = [], [], [], {}
        phase, mutated = "preflight", False
        expected_rows=[]
        operand_enum = self.native.api.Editors.MFE.MeritOperandType

        def select(index, number, kind):
            current.clear()
            current.update(request_index=index, operand=number, operand_type=kind, applied_fields=[])

        def parameter_plan(row, parameters):
            # Native GetCellAt columns are not ordinal float parameters.
            # Check every parameter before assigning target, weight or any cell value.
            plan = []
            for column, value in parameters.items():
                current["attempted_field"] = f"parameters.{column}"
                cell = row.GetCellAt(column)
                details = dict(column=column, requested=value, field=f"parameters.{column}")
                if cell is None:
                    raise ZemaxError("CELL_NOT_WRITABLE", "操作数没有对应单元格。", **details)
                details.update(header=str(cell.Header), data_type=str(cell.DataType))
                if cell.IsReadOnly or not cell.IsActive:
                    raise ZemaxError("CELL_NOT_WRITABLE", "操作数单元格未启用或只读。", **details)
                if str(cell.DataType) == "Integer" and int(value) != float(value):
                    raise ZemaxError("INVALID_ARGUMENT", "此参数必须为整数；请核对列标题，边界值通常应填写 target。", **details)
                plan.append((column, cell, value))
            return plan

        def apply(row, item, index, number):
            nonlocal phase
            select(index, number, item.type or str(row.Type))
            if item.type is not None and str(row.Type) != item.type:
                phase, current["attempted_field"] = "change_type", "type"
                result = row.ChangeType(self.native.enum(operand_enum, item.type))
                if result is False or str(row.Type) != item.type:
                    raise ZemaxError("SETTING_REJECTED", "操作数类型未采用。", requested=item.type, actual=str(row.Type))
                current["applied_fields"].append("type")
            phase = "validate_parameters"
            plan = parameter_plan(row, item.parameters)
            phase = "write_operand"
            for field in ("target", "weight"):
                value = getattr(item, field)
                if value is not None and str(row.Type)!="CONF":
                    current["attempted_field"] = field
                    setattr(row, field.title(), value)
                    current["applied_fields"].append(field)
            for column, cell, value in plan:
                current["attempted_field"] = f"parameters.{column}"
                self._write_cell(cell, value)
                current["applied_fields"].append(f"parameters.{column}")
            current.pop("attempted_field", None)
            expected_rows.append((number,str(current['operand_type']),item,list(current['applied_fields'])))
            completed.append(dict(current, applied_fields=list(current["applied_fields"])))

        def remove(number):
            current.clear()
            current.update(operand=number, attempted_field="remove_operand", applied_fields=[])
            before = int(mfe.NumberOfOperands)
            result = mfe.RemoveOperandAt(number)
            after = int(mfe.NumberOfOperands)
            retained_blank = before == after == 1 and str(mfe.GetOperandAt(1).Type) == "BLNK"
            if not retained_blank and (result is False or after != before - 1):
                raise ZemaxError("SETTING_REJECTED", "操作数删除未确认。", operand=number, before_count=before, after_count=after)
            removed.append(number)
            return retained_blank

        try:
            if req.mode=="replace"and req.operands and req.operands[0].type!="CONF"and int(self.system.MCE.NumberOfConfigurations)>1:
                raise ZemaxError('INVALID_ARGUMENT','多配置评价函数替换须以显式CONF行开头，避免原生自动插入改变行号。')
            for index, item in enumerate(req.operands):
                select(index, None, item.type)
                self.native.enum(operand_enum, item.type)
                if item.type=='CONF'and {'target','weight'}&item.model_fields_set:raise ZemaxError('INACTIVE_SETTING','CONF行不接受target或weight；仅指定配置参数。')
            for index, item in enumerate(req.updates):
                select(index, item.operand, item.type)
                if item.operand > initial_count:
                    raise ZemaxError("INDEX_OUT_OF_RANGE", "操作数编号超出范围。", operand=item.operand)
                row = mfe.GetOperandAt(item.operand)
                if item.type is not None:
                    self.native.enum(operand_enum, item.type)
                if (item.type or str(row.Type))=='CONF'and any(getattr(item,key)is not None for key in ('target','weight')):raise ZemaxError('INACTIVE_SETTING','CONF行不接受target或weight。')
                # Unchanged types permit a full read-only parameter preflight for the batch.
                # New/changed types must be checked after ChangeType; do not create scratch
                # user rows or use unverified APIs to pretend the request is transactional.
                if item.type is None or item.type == str(row.Type):
                    current["operand_type"] = str(row.Type)
                    parameter_plan(row, item.parameters)
            if any(i > initial_count for i in req.operand_numbers):
                raise ZemaxError("INDEX_OUT_OF_RANGE", "操作数删除编号超出范围。")
            current.clear()
            self._mutate("merit")
            mutated = True
            phase = "delete_operands"
            if req.mode == "delete":
                for number in sorted(req.operand_numbers, reverse=True):
                    remove(number)
            if req.mode == "update":
                for index, item in enumerate(req.updates):
                    apply(mfe.GetOperandAt(item.operand), item, index, item.operand)
            if req.mode in ("replace", "rms_spot_wizard"):
                while mfe.NumberOfOperands > 0:
                    if remove(int(mfe.NumberOfOperands)):
                        break  # Editors keep a final blank row.
            if req.mode == "rms_spot_wizard":
                phase = "wizard"
                current.clear()
                current.update(attempted_field="wizard", applied_fields=[])
                wizard = unwrap(mfe.SEQOptimizationWizard2)
                wizard.ResetSettings()
                self.native.set_enum(wizard, "Type", "RMS")
                self.native.set_enum(wizard, "Criterion", "Spot")
                self.native.set_enum(wizard, "Reference", req.reference)
                wizard.UseGaussianQuadrature = True
                wizard.Rings = req.rings
                wizard.UseAllFields = True
                wizard.UseAllConfigurations = False
                wizard.ConfigurationNumber = self.system.MCE.CurrentConfiguration
                wizard.StartAt = 1
                wizard.Apply()
                current["applied_fields"].append("wizard")
            for index, item in enumerate(req.operands):
                phase = "add_operand"
                select(index, None, item.type)
                current["attempted_field"] = "add_operand"
                if mfe.NumberOfOperands == 1 and str(mfe.GetOperandAt(1).Type) == "BLNK":
                    number, row = 1, mfe.GetOperandAt(1)
                else:
                    row = mfe.AddOperand()
                    number = int(mfe.NumberOfOperands)
                    added.append(number)
                apply(row, item, index, number)
            phase = "readback"
            for number,expected_type,item,fields in expected_rows:
                select(None,number,expected_type)
                row=mfe.GetOperandAt(number)
                if str(row.Type)!=expected_type:raise ZemaxError('SETTING_REJECTED','评价函数最终行类型已改变。',operand=number,requested=expected_type,actual=str(row.Type))
                for field in ('target','weight'):
                    if field in fields and float(getattr(row,field.title()))!=float(getattr(item,field)):raise ZemaxError('SETTING_REJECTED','评价函数最终目标或权重未采用。',operand=number,field=field,requested=getattr(item,field),actual=float(getattr(row,field.title())))
                for column,value in item.parameters.items():
                    actual=self._cell_value(row.GetCellAt(column))
                    if actual!=value:raise ZemaxError('SETTING_REJECTED','评价函数最终参数未采用。',operand=number,column=column,requested=value,actual=actual)
            current.clear()
            return self.get_merit_function(None)
        except Exception as exc:
            error = exc if isinstance(exc, ZemaxError) else ZemaxError("NATIVE_ERROR", str(exc), type=type(exc).__name__)
            error.details.update(merit_mode=req.mode, phase=phase, initial_operand_count=initial_count,
                                 completed_operands=[item["operand"] for item in completed], completed_operations=completed,
                                 removed_operands=removed, added_operands=added, failed_operation=current,
                                 rollback_performed=False, mutation_started=mutated, checkpoint=self.last_checkpoint,
                                 recovery_hint="未自动回退或恢复设计；请先读取评价函数核对受影响操作数，再决定如何处理或重试。")
            if current.get("request_index") is not None:
                error.details["failed_index"] = current["request_index"]
            try:
                error.details["operand_count_after_error"] = int(mfe.NumberOfOperands)
            except Exception:
                pass
            if error is exc:
                raise
            raise error from exc

    def evaluate_merit_function(self, req):
        self._require_sequential()
        value = float(self.system.MFE.CalculateMeritFunction())
        result = {"merit_function": value, "operands": self.get_merit_function(None), "analysis_conditions": {}}
        try:
            settings = self.get_system_settings(None)
            result["system_settings"] = settings
            conditions = result["analysis_conditions"]
            if any(str(self.system.MFE.GetOperandAt(i).Type) == "CONF"
                   for i in range(1, int(self.system.MFE.NumberOfOperands) + 1)):
                result["condition_scope"] = "multi_configuration_merit; use operand definitions"
                return result
            for key in ("configuration", "temperature_c"):
                if settings.get(key) is not None:
                    conditions[key] = settings[key]
            waves, fields = settings.get("wavelengths", []), settings.get("fields", [])
            if len(waves) == 1:
                conditions["wavelength_um"] = waves[0]["wavelength_um"]
            if settings.get("field_type") == "Angle" and len(fields) == 1 and fields[0].get("x") == 0:
                conditions["field_deg"] = fields[0]["y"]
            result["condition_scope"] = "single_system_setting; operand definitions retained separately"
        except Exception as exc:
            result["settings_error"] = str(exc)
        return result

    def _analysis_selection(self, req):
        self._require_sequential(focused=True)
        if req.field > self.system.SystemData.Fields.NumberOfFields:
            raise ZemaxError("INDEX_OUT_OF_RANGE", "视场编号超出范围。")
        if req.wavelength > self.system.SystemData.Wavelengths.NumberOfWavelengths:
            raise ZemaxError("INDEX_OUT_OF_RANGE", "波长编号超出范围。")

    def _start_task(self, kind, native, settings, before=None, analysis=False, collector=None, budget_seconds=None):
        task_id = uuid.uuid4().hex
        task = {"task_id": task_id, "request_id": self.request_id, "kind": kind, "state": "running", "created_at": utc_now(),
                "settings": settings, "context": self.context(), "system_settings": None,
                "progress": None, "can_cancel": False, "cancel_requested": False,
                "before": before or {}, "native": native, "analysis": analysis, "result": None}
        task["started_monotonic"] = time.monotonic()
        if collector is not None:
            task["collector"] = collector
        if budget_seconds is not None:
            task["budget_seconds"] = budget_seconds
            task["budget_deadline"] = task["started_monotonic"] + budget_seconds
        self.tasks[task_id] = task
        self.active = task
        self._record_task_history(task)
        try:
            task["system_settings"] = self.get_system_settings(None)
            task["can_cancel"] = bool(analysis or native.CanCancel)
            if analysis:
                native.Apply()
            elif not native.Run():
                raise ZemaxError("TASK_START_FAILED", str(native.ErrorMessage))
        except Exception as exc:
            failure = exc if isinstance(exc, ZemaxError) else ZemaxError(
                "TASK_START_FAILED", str(exc), type=type(exc).__name__)
            failure.details["task_id"] = task_id
            task["state"] = "failed"
            task["finished_at"] = utc_now()
            task["error"] = failure.as_dict()
            self._close_task_native(task)
            task["native"] = None
            self.active = None
            task["result"] = {"completed": False, "task": self._task_view(task),
                              "checkpoint": self.last_checkpoint, "context": task["context"],
                              "system_settings": task["system_settings"]}
            self._record_task_history(task)
            if failure is exc:
                raise
            raise failure from exc
        self.tick()
        return self._task_view(task)

    def run_fft_mtf(self, req):
        self._analysis_selection(req)
        if str(self.system.SystemData.Units.MTFUnits) != req.frequency_unit:
            raise ZemaxError("UNIT_MISMATCH", "请求频率单位与系统 MTF 单位不同，请显式修改系统设置。", actual=str(self.system.SystemData.Units.MTFUnits))
        analysis = self.system.Analyses.New_FftMtf()
        try:
            settings = unwrap(analysis.GetSettings())
            settings.Field.SetFieldNumber(req.field)
            settings.Wavelength.SetWavelengthNumber(req.wavelength)
            settings.Surface.UseImageSurface()
            self.native.set_enum(settings, "SampleSize", req.sampling)
            settings.MaximumFrequency = req.maximum_frequency
            settings.UsePolarization = req.use_polarization
            self.native.set_enum(settings, "Type", "Modulation")
            actual = {"field": int(settings.Field.GetFieldNumber()), "wavelength": int(settings.Wavelength.GetWavelengthNumber()),
                      "sampling": str(settings.SampleSize), "maximum_frequency": float(settings.MaximumFrequency),
                      "frequency_unit": str(self.system.SystemData.Units.MTFUnits),
                      "frequency_space": "image" if req.frequency_unit == "CyclesPerMillimeter" else "object angular",
                      "use_polarization": bool(settings.UsePolarization), "type": str(settings.Type)}
            actual["surface"]="image"
        except Exception:
            self._close_task_native({"native": analysis})
            raise
        return self._start_task("fft_mtf", analysis, actual, analysis=True)

    def run_spot_analysis(self, req):
        self._analysis_selection(req)
        analysis = getattr(self.system.Analyses,'New_Analysis_SettingsFirst',self.system.Analyses.New_Analysis)(self.native.api.Analysis.AnalysisIDM.StandardSpot)
        try:
            settings = unwrap(analysis.GetSettings())
            settings.Field.SetFieldNumber(req.field)
            settings.Wavelength.SetWavelengthNumber(req.wavelength)
            self.native.set_enum(settings, "ReferTo", req.reference)
            self.native.set_enum(settings, "Pattern", req.pattern)
            settings.RayDensity = req.ray_density
            settings.UsePolarization = req.use_polarization
            settings.Configuration = self.system.MCE.CurrentConfiguration
            settings.DeltaFocus = 0
            settings.DirectionCosines = False
            settings.IgnoreLateralColor = False
            settings.ScatterRays = False
            actual = {"field": int(settings.Field.GetFieldNumber()), "wavelength": int(settings.Wavelength.GetWavelengthNumber()),
                      "reference": str(settings.ReferTo), "pattern": str(settings.Pattern), "ray_density": int(settings.RayDensity),
                      "configuration": int(settings.Configuration), "use_polarization": bool(settings.UsePolarization),
                      "ignore_lateral_color": bool(settings.IgnoreLateralColor), "scatter_rays": bool(settings.ScatterRays),
                      "delta_focus": float(settings.DeltaFocus), "direction_cosines": bool(settings.DirectionCosines)}
        except Exception:
            self._close_task_native({"native": analysis})
            raise
        return self._start_task("spot", analysis, actual, analysis=True)

    def run_quick_focus(self, req):
        self._require_sequential(focused=True)
        index = self.system.LDE.NumberOfSurfaces - 2
        cell = self._row(index).ThicknessCell
        self._guard_cell(cell, req.replace_solve)
        before = {"surface": index, "thickness": float(cell.DoubleValue), "solve": str(cell.Solve), "model_revision": self.revision}
        self._mutate("focus")
        if req.replace_solve and str(cell.Solve) not in ("Fixed", "Variable"):
            cell.MakeSolveFixed()
        native = self.system.Tools.OpenQuickFocus()
        try:
            self.native.set_enum(native, "Criterion", req.criterion)
            native.UseCentroid = req.use_centroid
            actual = {"criterion": str(native.Criterion), "use_centroid": bool(native.UseCentroid), "adjusted_surface": index}
        except Exception:
            self._close_task_native({"native": native})
            raise
        return self._start_task("quick_focus", native, actual, before)

    def optimization_diagnostics(self):
        import math
        self._require_sequential()
        variables=self.get_variables(None)["variables"]
        mfe=self.system.MFE
        rows=[];issues=[]
        if not variables: issues.append({"code":"NO_VARIABLES","field":"variables","next_action":"get_variables / set_variables"})
        weighted=False
        for i in range(1,mfe.NumberOfOperands+1):
            row=mfe.GetOperandAt(i);weight=float(row.Weight)
            row_active=bool(getattr(row,"IsActive",True))
            cell_active={key:bool(getattr(getattr(row,attribute,None),"IsActive",True))
                         for key,attribute in (("target","TargetCell"),("weight","WeightCell"),
                                               ("value","ValueCell"),("contribution","ContributionCell"))}
            objective_active=row_active and cell_active["weight"]
            weighted |= objective_active and math.isfinite(weight) and weight>0
            rows.append(dict(operand=i,type=str(row.Type),weight=weight,target=float(row.Target),
                             objective_active=objective_active,cell_active=cell_active))
        if not weighted: issues.append({"code":"NO_MERIT_FUNCTION","field":"operands","next_action":"get_merit_function / update_merit_function"})
        native_status=None
        if callable(getattr(self.system,"GetCurrentStatus",None)):
            try:
                native_status=str(self.system.GetCurrentStatus())
                if native_status.strip(): issues.append({"code":"INVALID_NATIVE_SYSTEM","reason":native_status,"next_action":"get_system_summary / get_batch_rays"})
            except Exception as exc:
                issues.append({"code":"NATIVE_VALIDITY_UNCONFIRMED","reason":str(exc)})
        merit=None
        try:
            merit=float(mfe.CalculateMeritFunction())
            for row in rows:
                actual=mfe.GetOperandAt(row["operand"])
                row.update(value=float(actual.Value),contribution=float(actual.Contribution))
                if row["objective_active"] and not all(math.isfinite(row[key]) for key in ("value","contribution","weight","target") if row["cell_active"][key]):
                    issues.append({"code":"INVALID_MERIT_FUNCTION","operand":row["operand"],"reason":"nonfinite_operand"})
            if not math.isfinite(merit): issues.append({"code":"INVALID_MERIT_FUNCTION","reason":"nonfinite_merit"})
        except Exception as exc:
            issues.append({"code":"MERIT_EVALUATION_FAILED","reason":str(exc),"next_action":"get_merit_function / get_batch_rays"})
        return dict(ready=not issues,merit_function=merit,variables=variables,rows=rows,issues=issues,
                    model_revision=self.revision,native_system_status=native_status,evaluation_source="native_CalculateMeritFunction",
                    ray_validity="not_separately_checked",finite_value_interpretation="finite values retained; inspect native evaluation and ray diagnostics")

    def _optimization_preflight(self):
        diagnostics = self.optimization_diagnostics()
        if not diagnostics['ready']:
            raise ZemaxError(diagnostics['issues'][0]['code'], '优化预检未通过，请检查变量、评价函数和原生系统状态。', diagnostics=diagnostics)
        return diagnostics

    def run_local_optimization(self, req):
        self._require_sequential()
        self._require_work()
        diagnostics = self._optimization_preflight()
        before = dict(merit_function=diagnostics['merit_function'], variables=diagnostics['variables'], model_revision=self.revision, diagnostics=diagnostics)
        self._mutate('optimization')
        native = self.system.Tools.OpenLocalOptimization()
        try:
            if req.number_of_cores > native.MaxCores:
                raise ZemaxError('INVALID_ARGUMENT', '线程数超过本机工具上限。', maximum=int(native.MaxCores))
            self.native.set_enum(native, 'Algorithm', req.algorithm)
            self.native.set_enum(native, 'Cycles', req.cycles)
            native.NumberOfCores = req.number_of_cores
            actual = dict(algorithm=str(native.Algorithm), cycles=str(native.Cycles), number_of_cores=int(native.NumberOfCores))
        except Exception:
            self._close_task_native({'native': native})
            raise
        return self._start_task('local_optimization', native, actual, before)

    @staticmethod
    def _task_view(task):
        keys = ("task_id", "request_id", "kind", "state", "created_at", "finished_at", "progress", "native_progress", "status", "phase", "can_cancel", "cancel_requested", "settings", "context", "error", "close_attempted", "cleanup_warnings", "native_trace_complete", "native_dead_ray_errors", "result_path", "result_artifacts", "budget_seconds", "budget_stop_requested", "budget_stop_attempted", "budget_stop_error", "telemetry_error", "poll_error", "cancellation_effect", "history_warnings")
        view = {k: task[k] for k in keys if k in task}
        if "started_monotonic" in task:
            now = task.get("finished_monotonic", time.monotonic())
            view["elapsed_seconds"] = round(max(0, now - task["started_monotonic"]), 3)
            if "budget_deadline" in task:
                view["budget_remaining_seconds"] = round(max(0, task["budget_deadline"] - now), 3)
                view["budget_expired"] = now >= task["budget_deadline"]
        child = task.get("child")
        if child:
            child_view = Backend._task_view(child)
            view["active_step"] = {k: child_view[k] for k in (
                "task_id", "kind", "state", "progress", "native_progress", "status", "elapsed_seconds",
                "budget_seconds", "budget_remaining_seconds", "budget_expired", "budget_stop_requested", "budget_stop_attempted", "budget_stop_error", "telemetry_error", "poll_error") if k in child_view}
            if task.get("kind") in {"hammer_optimization", "global_optimization"}:
                view["progress"] = None
                if not task.get("cancel_requested"):
                    view["status"] = child_view.get("status", "正在执行原生步骤")
        return view

    def _task(self, task_id):
        if task_id not in self.tasks:
            raise ZemaxError("TASK_NOT_FOUND", "找不到该任务编号。", task_id=task_id)
        return self.tasks[task_id]

    def get_task_status(self, req):
        return self._task_view(self._task(req.task_id))

    def get_task_result(self, req):
        task = self._task(req.task_id)
        if task["state"] not in TERMINAL:
            raise ZemaxError("TASK_NOT_FINISHED", "任务尚未结束。", task=self._task_view(task))
        if task.get("result_path"):
            try:
                with Path(task["result_path"]).open(encoding="utf-8") as stream:
                    result = json.load(stream)
            except (OSError, ValueError) as exc:
                raise ZemaxError("RESULT_UNAVAILABLE", "结果文件无法读取。", path=task["result_path"], reason=str(exc)) from exc
        else:
            result = task["result"] or self._task_view(task)
        if isinstance(result, dict) and "task" in result:
            result["task"] = self._task_view(task)
        return self._page_task_result(result, req)

    def _page_task_result(self, result, req):
        if req.series is not None:
            series=result.get('series',[])
            if req.series>=len(series):raise ZemaxError('INDEX_OUT_OF_RANGE','曲线编号越界。')
            item=series[req.series];end=min(req.start+req.count,len(item['x']))
            page={**item,'x':item['x'][req.start:end],'y':item['y'][req.start:end]}
            for key in ('native_x','field_coordinates','point_labels'):
                if key in item:
                    if len(item[key])!=len(item['x']):
                        raise ZemaxError('INVALID_RESULT_DATA','曲线附加坐标数量与横轴不一致。',coordinate=key)
                    page[key]=item[key][req.start:end]
            if 'enclosure_radius_um' in item.get('native_binning',{}):
                radii=item['native_binning']['enclosure_radius_um']
                if len(radii)!=len(item['x']):
                    raise ZemaxError('INVALID_RESULT_DATA','累计能量分箱边界数量与横轴不一致。')
                page['native_binning']={**item['native_binning'],'enclosure_radius_um':radii[req.start:end]}
            return {**{k:result[k] for k in ('task','context','artifacts','history') if k in result},
                    'series':[page],
                    'total':len(item['x']),'next_start':end if end<len(item['x'])else None}
        if result.get("scatter"):
            result={**result,"scatter":[{k:v for k,v in item.items() if k!="points"}|{"point_count":len(item.get("points",[]))} for item in result["scatter"]],"scatter_data_in_artifacts":True}
        if result.get("grids"):
            grids=result["grids"]
            def metadata(g):
                value={k:v for k,v in g.items()if k!="values"}
                if "valid_mask" in value:
                    value.pop("valid_mask");value["valid_mask_in_artifacts"]=True
                if "pupil_mapping"in value:value["pupil_mapping"]={k:v for k,v in value["pupil_mapping"].items()if k!="points"}|dict(points_in_artifacts=True)
                return value
            if req.grid is not None:
                if req.grid>=len(grids):
                    raise ZemaxError("INDEX_OUT_OF_RANGE","网格编号越界。")
                g=grids[req.grid]
                array=g["values"]
                ny=len(array); nx=len(array[0]) if ny else 0
                if req.x_start>nx or req.y_start>ny:
                    raise ZemaxError("INDEX_OUT_OF_RANGE","区域起点越界。")
                xend=min(nx,req.x_start+req.width); yend=min(ny,req.y_start+req.height)
                meta=metadata(g)
                if "valid_mask" in g:
                    meta.pop("valid_mask_in_artifacts",None)
                    meta["valid_mask"]=[row[req.x_start:xend] for row in g["valid_mask"][req.y_start:yend]]
                if "pupil_mapping"in g:
                    meta["pupil_mapping"]={**meta["pupil_mapping"],"points":[row[req.x_start:xend]for row in g["pupil_mapping"]["points"][req.y_start:yend]]}
                return {**{k:result[k] for k in ("task","context","artifacts","history") if k in result},
                        "grid":{**meta,"x_start":req.x_start,"y_start":req.y_start,
                                "values":[row[req.x_start:xend] for row in array[req.y_start:yend]],
                                "next_x":xend if xend<nx else None,"next_y":yend if yend<ny else None}}
            result={**result,"grids":[metadata(g)for g in grids],"grid_data_in_artifacts":True}
        if "rows" in result:
            rows = result["rows"]
            end = min(req.start + req.count, len(rows))
            return {**result, "rows": rows[req.start:end], "total": len(rows),
                    "next_start": end if end < len(rows) else None}
        if "series" in result:
            size = sum(len(s["x"]) + sum(len(row) for row in s["y"]) for s in result["series"])
            if size > 5000:
                return {**result, "inline_data_truncated": True,
                        "series": [{"series": s["series"], "description": s["description"], "labels": s["labels"],
                                    "x_label": s["x_label"], "point_count": len(s["x"])} for s in result["series"]]}
        return result

    def cancel_task(self, req):
        task = self._task(req.task_id)
        if task["state"] in TERMINAL:
            return self._task_view(task)
        if task.get("composite"):
            task["cancel_requested"] = True
            task["state"] = "cancelling"
            task["status"] = ("等待当前原生步骤停止；保留中断候选，不会自动恢复基线"
                              if task.get("cancellation_effect") == "retain_candidate" else "等待当前原生步骤停止后恢复基线")
            child = task.get("child")
            if child and child["state"] not in TERMINAL:
                if child.get('composite'):
                    from .models import TaskRequest
                    self.cancel_task(TaskRequest(task_id=child['task_id']))
                    return self._task_view(task)
                native = child["native"]
                if child["analysis"]:
                    native.Terminate()
                    child["cancel_requested"] = True
                elif native.CanCancel and native.Cancel():
                    child["cancel_requested"] = True
            return self._task_view(task)
        native = task["native"]
        if not task["analysis"] and not native.CanCancel:
            raise ZemaxError("CANCEL_UNSUPPORTED", "该工具当前不支持取消。", task_id=req.task_id)
        if task["analysis"]:
            native.Terminate()
        else:
            if not native.Cancel():
                raise ZemaxError("CANCEL_REJECTED", "原生工具没有接受取消请求。")
        task["cancel_requested"] = True
        task["state"] = "cancelling"
        self.tick()
        return self._task_view(task)

    def _collect_analysis(self, task):
        result = unwrap(task["native"].GetResults())
        if result is None or not result.IsValid:
            raise ZemaxError("ANALYSIS_FAILED", "没有有效的原生分析结果。")
        messages = [{"code": str(result.GetMessageAt(i).ErrorCode), "text": str(result.GetMessageAt(i).Text)}
                    for i in range(result.NumberOfMessages)]
        header = [str(line) for line in result.HeaderData.Lines]
        text_path = self.directory / f"{task['task_id']}_native.txt"
        if not result.GetTextFile(str(text_path)):
            raise ZemaxError("EXPORT_FAILED", "原生分析文本导出失败。")
        data = {"native_header": header, "native_messages": messages,
                "artifacts": [{"kind": "native_text", "path": str(text_path)}]}
        if task["kind"] == "fft_mtf":
            series = []
            for i in range(result.NumberOfDataSeries):
                item = result.GetDataSeries(i)
                series.append({"series": i, "description": str(item.Description), "x_label": str(item.XLabel),
                               "labels": [str(x) for x in item.SeriesLabels],
                               "x": dotnet_array(item.XData.Data), "y": dotnet_array(item.YData.Data)})
            if not series:
                raise ZemaxError("NO_RESULT_DATA", "FFT MTF 没有提供数据序列。", native_text=str(text_path))
            data["series"] = series
            if any(len(s["x"]) != len(s["y"]) or any(not math.isfinite(v) for v in s["x"])
                   or any(not math.isfinite(v) for row in s["y"] for v in row) for s in series):
                raise ZemaxError("INVALID_RESULT_DATA", "MTF 序列尺寸不一致或包含非有限值。", native_text=str(text_path), messages=messages)
        else:
            spot = result.SpotData
            if spot is None:
                raise ZemaxError("NO_RESULT_DATA", "此接口没有原生 SpotData。", native_text=str(text_path))
            metrics = []
            selection = task["settings"]
            fields = [selection["field"]] if selection["field"] else range(1, spot.NumberOfFields + 1)
            for field in fields:
                # 2024 R2 returns the selected analysis aggregate for every wavelength slot.
                # Use the first slot once; do not mislabel repeated aggregate data as monochromatic.
                metrics.append({"field_number": field, "wavelength_selection": selection["wavelength"],
                                "aggregation": "polychromatic" if selection["wavelength"] == 0 else "monochromatic",
                                "rms_radius": float(spot.GetRMSSpotSizeFor(field, 1)),
                                "geo_radius": float(spot.GetGeoSpotSizeFor(field, 1)),
                                "reference_x": float(spot.GetReferenceCoordinate_X_For(field, 1)),
                                "reference_y": float(spot.GetReferenceCoordinate_Y_For(field, 1))})
            data.update(metrics=metrics, radius_unit="micrometers", reference_coordinate_unit="lens units",
                        native_wavelength_slot=1)
            if not metrics or any(not math.isfinite(m[key]) or m[key] < 0 for m in metrics for key in ("rms_radius", "geo_radius")):
                raise ZemaxError("INVALID_RESULT_DATA", "光斑结果缺失或包含无效半径。", native_text=str(text_path), messages=messages)
        return data

    def _collect(self, task):
        if task.get("collector"):
            return task["collector"](task)
        if task["analysis"]:
            return self._collect_analysis(task)
        if not task["native"].Succeeded:
            raise ZemaxError("TASK_FAILED", str(task["native"].ErrorMessage) or "原生工具未成功完成。")
        if task["kind"] == "quick_focus":
            index = task["before"]["surface"]
            return {"before": task["before"], "after": {"surface": index,
                    "thickness": float(self._row(index).Thickness), "solve": str(self._row(index).ThicknessCell.Solve)},
                    "geometry_unit": str(self.system.SystemData.Units.LensUnits)}
        native_value = float(task["native"].CurrentMeritFunction)
        if not self._close_task_native(task):
            raise ZemaxError("CLEANUP_FAILED", "优化工具资源释放未确认。")
        return {"before": task["before"], "native_final_merit": native_value, "after": {
            "merit_function": float(self.system.MFE.CalculateMeritFunction()),
            "variables": self.get_variables(None)["variables"], "operands": self.get_merit_function(None)}}

    def _save_task_result(self, task, result):
        result.update(result_schema_version=RESULT_VERSION, task=self._task_view(task), context=task["context"], system_settings=task["system_settings"])
        path = self.directory / f"{task['task_id']}.json"
        artifacts = result.setdefault("artifacts", [])
        artifacts.append({"kind": "json", "path": str(path)})
        if "series" in result:
            import csv
            csv_path = self.directory / f"{task['task_id']}.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["series", "description", "frequency", "label", "value"])
                for item in result["series"]:
                    for i, x in enumerate(item["x"]):
                        for j, label in enumerate(item["labels"]):
                            writer.writerow([item["series"], item["description"], x, label, item["y"][i][j]])
            artifacts.append({"kind": "csv", "path": str(csv_path)})
        write_json(path, result, create_parent=False)
        task["result_path"] = str(path)
        task["result_artifacts"] = list(artifacts)
        task["result"] = None
        self._record_task_history(task)

    def tick(self):
        task = self.active
        if task is None:
            return
        if task.get("composite"):
            self._tick_composite(task)
            return
        native = task["native"]
        stopped_confirmed = False
        try:
            running = native.IsRunning() if task["analysis"] else native.IsRunning
            if running:
                if not task["analysis"]:
                    try:
                        task["can_cancel"] = bool(native.CanCancel)
                    except Exception as exc:
                        task["can_cancel"] = False
                        task["telemetry_error"] = {"field": "CanCancel", "message": str(exc)}
                    expired = task.get("budget_deadline") is not None and time.monotonic() >= task["budget_deadline"]
                    # Enforce the search budget independently of optional progress
                    # telemetry (Hammer is normally indefinite and may report 0).
                    if expired and not task.get("budget_stop_attempted") and task["can_cancel"]:
                        task["budget_stop_attempted"] = True
                        try:
                            if native.Cancel() is False:
                                raise ZemaxError("CANCEL_REJECTED", "原生工具拒绝预算停止请求。")
                            task["budget_stop_requested"] = True
                        except Exception as exc:
                            # A failed cancellation does NOT mean the optical
                            # job stopped. Keep the native handle and busy lock,
                            # observe termination, and do not auto-retry Cancel.
                            task["budget_stop_error"] = (exc.as_dict() if isinstance(exc, ZemaxError)
                                                         else {"code": "CANCEL_UNCONFIRMED", "message": str(exc)})
                    try:
                        task["native_progress"] = int(native.Progress)
                        task["progress"] = None if getattr(native, "IsFiniteDuration", True) is False else task["native_progress"]
                    except Exception:
                        task["progress"] = None
                    if expired:
                        if task.get("budget_stop_error"):
                            task["status"] = "时间预算已到，停止请求未确认；原生任务仍在运行，保持系统忙碌"
                        else:
                            task["status"] = ("时间预算已到，已请求停止，等待原生工具确认"
                                              if task.get("budget_stop_requested") else "时间预算已到，等待可取消的原生安全边界")
                    else:
                        try:
                            task["status"] = str(native.Status)
                        except Exception:
                            task["status"] = "原生任务运行中（未提供进度）"
                return
            stopped_confirmed = True
            native.WaitForCompletion()
            task["finished_at"] = utc_now()
            task["finished_monotonic"] = time.monotonic()
            if task["cancel_requested"]:
                task["state"] = "cancelled"
                self._save_task_result(task, {"completed": False, "before": task["before"], "checkpoint": task["context"]["checkpoint"]})
            else:
                result = self._collect(task)
                task["state"] = "succeeded"
                task["progress"] = 100
                self._save_task_result(task, result)
        except Exception as exc:
            if not stopped_confirmed:
                # A polling/transport failure is not evidence of native stop.
                # Retain ownership and require explicit recovery; read-only
                # status remains available and later ticks may confirm stop.
                task["poll_error"] = exc.as_dict() if isinstance(exc, ZemaxError) else {"code": "TASK_STATE_UNKNOWN", "message": str(exc)}
                task["can_cancel"] = False
                task["status"] = "原生运行状态未确认，保留任务占用；请核对后台状态"
                self.requires_reconnect = True
                return
            task["state"] = "failed"
            task["finished_at"] = utc_now()
            task["error"] = exc.as_dict() if isinstance(exc, ZemaxError) else {"code": "NATIVE_ERROR", "message": str(exc)}
            task["result"] = {"completed": False, "task": self._task_view(task), "checkpoint": self.last_checkpoint}
        finally:
            if task["state"] in TERMINAL:
                self._close_task_native(task)
                self._record_task_history(task)
                task["native"] = None
                self.active = None

    def _close_task_native(self, task):
        if task.get("close_attempted"):
            return not bool(task.get("cleanup_warnings"))
        task["close_attempted"] = True
        try:
            if task["native"].Close() is False:
                raise RuntimeError("原生 Close 返回 false；资源释放未确认。")
        except Exception as exc:
            task.setdefault("cleanup_warnings", []).append(str(exc))
            self.requires_reconnect = True
            return False
        return True

    @staticmethod
    def _state_dir():
        """Directory shared with the host for lifecycle receipts."""
        value = os.environ.get("ZEMAX_STATE_DIR")
        return Path(value) if value else None

    def _write_close_receipt(self, receipt):
        directory = self._state_dir()
        if directory is None:
            return
        path = directory / "close_receipt.json"
        temporary = directory / f"close_receipt.{uuid.uuid4().hex}.tmp"
        try:
            directory.mkdir(parents=True, exist_ok=True)
            temporary.write_text(json.dumps(clean(receipt), ensure_ascii=False, indent=2, allow_nan=False),
                                 encoding="utf-8")
            os.replace(temporary, path)
        except Exception as exc:
            print(f"无法写入关闭回执：{exc}", file=sys.stderr, flush=True)
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def shutdown(self):
        """Close only the instance this worker created, and leave a truthful receipt.

        The host cannot see this process exit, so without the receipt it can only
        guess whether the native application is still running.
        """
        started_at = utc_now()
        receipt = {
            "schema_version": 1,
            "generation": os.environ.get("ZEMAX_GENERATION"),
            "session_id": self.session_id,
            "started_at": started_at,
            "active_cancelled": False,
            "forced": False,
            "checkpoint": {"attempted": False, "path": None, "ok": False, "error": None},
            "was_connected": getattr(self.native, "application", None) is not None,
            "native": {"attempted": False, "closed": False, "error": None},
        }
        try:
            if self.active:
                task = self.active
                try:
                    from .models import TaskRequest
                    self.cancel_task(TaskRequest(task_id=task["task_id"]))
                    deadline = time.monotonic() + 15
                    while self.active and time.monotonic() < deadline:
                        self.tick()
                        time.sleep(0.1)
                except Exception as exc:
                    receipt["cancel_error"] = str(exc)
                if self.active:
                    receipt["forced"] = True
                    print("关闭仍有运行状态的自有后台实例；未确认任务安全取消。", file=sys.stderr, flush=True)
                else:
                    receipt["active_cancelled"] = True
            if self.work_path and not self.active and not self.requires_reconnect:
                receipt["checkpoint"]["attempted"] = True
                try:
                    receipt["checkpoint"]["path"] = self._checkpoint("shutdown")
                    receipt["checkpoint"]["ok"] = True
                except Exception as exc:
                    receipt["checkpoint"]["error"] = str(exc)
        finally:
            receipt["native"]["attempted"] = True
            try:
                self.native.disconnect()
                receipt["native"]["closed"] = getattr(self.native, "application", None) is None
            except Exception as exc:
                receipt["native"]["error"] = str(exc)
            receipt["closed_at"] = utc_now()
            self._write_close_receipt(receipt)
