"""Installed 2024 R2 system and sequential geometry adapters."""
import math
from .property_pages import SYSTEM_PAGES, SURFACE_PAGES, read_pages, apply_pages
from .errors import ZemaxError

POL = dict(unpolarized="Unpolarized", jx="Jx", jy="Jy", x_phase="XPhase", y_phase="YPhase", method="Method", convert_thin_film_phase="ConvertThinFilmPhaseToRayEquivalent")
AIM = dict(mode="RayAiming", method="Method", cache="UseRayAimingCache", robust="UseRobustRayAiming")
AIM.update(scale_pupil_shift_by_field="ScalePupilShiftFactorsByField", auto_pupil_shift="AutomaticallyCalculatePupilShiftsIsChecked", enhanced="UseEnhancedRayAiming", advanced_convergence="UseAdvancedConvergence", fallback_search="UseFallBackSearchDuringCacheSetup", pupil_shift_x="PupilShiftX", pupil_shift_y="PupilShiftY", pupil_shift_z="PupilShiftZ", pupil_compress_x="PupilCompressX", pupil_compress_y="PupilCompressY", cache_steps="NumStepsCacheSetup")
FILES = dict(coating_file="CoatingFile", scatter_profile="ScatterProfile", abg_file="ABgDataFile", gradium_profile="GradiumProfile")
FILE_METHODS = dict(coating_file="GetCoatingFiles", scatter_profile="GetScatterProfiles", abg_file="GetABgDataFiles", gradium_profile="GetGradiumProfiles")
UNIT_SETTINGS=dict(afocal_mode_units="AfocalModeUnits",source_units="SourceUnits",source_unit_prefix="SourceUnitPrefix",analysis_units="AnalysisUnits",analysis_unit_prefix="AnalysisUnitPrefix")
TILT = {prefix+suffix: native+attr for prefix,native in (("before_","BeforeSurface"),("after_","AfterSurface")) for suffix,attr in (("order","Order"),("decenter_x","DecenterX"),("decenter_y","DecenterY"),("tilt_x","TiltX"),("tilt_y","TiltY"),("tilt_z","TiltZ"))}
APERTURE = dict(width_of_arms="WidthOfArms",number_of_arms="NumberOfArms",aperture_file="ApertureFile",uda_scale="UDASCale",minimum_radius="MinimumRadius", maximum_radius="MaximumRadius", x_half_width="XHalfWidth", y_half_width="YHalfWidth", x_decenter="ApertureXDecenter", y_decenter="ApertureYDecenter")
SOLVES = dict(fixed="Fixed", variable="Variable", surface_pickup="SurfacePickup", f_number="FNumber", marginal_ray_height="MarginalRayHeight", chief_ray_height="ChiefRayHeight", edge_thickness="EdgeThickness", position="Position", pickup_chief_ray="PickupChiefRay")
SOLVE_FIELDS = dict(MarginalRayHeight=dict(height="Height", pupil_zone="PupilZone"), ChiefRayHeight=dict(height="Height"), EdgeThickness=dict(thickness="Thickness", radial_height="RadialHeight"), Position=dict(source_surface="FromSurface",length="Length"), PickupChiefRay=dict(field="Field",wavelength="Wavelength"))
SOLVES.update(zpl_macro="ZPLMacro", marginal_ray_angle="MarginalRayAngle", chief_ray_angle="ChiefRayAngle",
    marginal_ray_normal="MarginalRayNormal", chief_ray_normal="ChiefRayNormal", aplanatic="Aplanatic",
    element_power="ElementPower", concentric_surface="CocentricSurface", concentric_radius="CocentricRadius",
    optical_path_difference="OpticalPathDifference", compensator="Compensator", center_of_curvature="CenterOfCurvature",
    pupil_position="PupilPosition", material_model="MaterialModel", material_substitute="MaterialSubstitute",
    material_offset="MaterialOffset", automatic="Automatic", maximum="Maximum")
SOLVE_FIELDS.update(ZPLMacro=dict(macro="Macro"), MarginalRayAngle=dict(angle="Angle"), ChiefRayAngle=dict(angle="Angle"),
    MarginalRayNormal={}, ChiefRayNormal={}, Aplanatic={}, ElementPower=dict(power="Power"),
    CocentricSurface=dict(source_surface="AboutSurface"), CocentricRadius=dict(source_surface="WithSurface"),
    OpticalPathDifference=dict(opd="OPD", pupil_zone="PupilZone"), Compensator=dict(source_surface="RefSurface",sum="Sum"),
    CenterOfCurvature=dict(source_surface="RefSurface"), PupilPosition={},
    MaterialModel=dict(index_nd="IndexNd",abbe_vd="AbbeVd",dpgf="dPgF",vary_index="VaryIndex",vary_abbe="VaryAbbe",vary_dpgf="VarydPgF"),
    MaterialSubstitute=dict(catalog="Catalog"), MaterialOffset=dict(nd_offset="NdOffset",vd_offset="VdOffset"), Automatic={}, Maximum={})
SOLVE_ALIASES = dict(ConcentricSurface="CocentricSurface", ConcentricRadius="CocentricRadius")

SURFACE_TYPES = ["Standard","EvenAspheric","CoordinateBreak","OddAsphere","Toroidal","Biconic","Paraxial"]


def values(obj, mapping):
    return {k: str(getattr(obj,v)) if k in {"method","mode","before_order","after_order"} else getattr(obj,v) for k,v in mapping.items()}


def patch_values(patch):
    data=patch.model_dump(exclude_unset=True)
    if not data or any(v is None for v in data.values()):
        raise ZemaxError("INVALID_ARGUMENT", "设置对象须包含非空修改，省略不修改的字段。")
    return data


def validate_environment_patch(environment, patch):
    requested = {key: getattr(patch, key) for key in ('temperature_c', 'pressure_atm')
                 if getattr(patch, key) is not None}
    if not requested:
        return
    enabled = (bool(environment.AdjustIndexToEnvironment) if patch.adjust_index_to_environment is None
               else patch.adjust_index_to_environment)
    if not enabled:
        for key, fixed in (('temperature_c', 20.), ('pressure_atm', 1.)):
            if key in requested and requested[key] != fixed:
                raise ZemaxError('SETTING_INACTIVE', '关闭环境折射率修正时温度和压力采用固定基准。',
                    setting=key, requested=requested[key], fixed_value=fixed,
                    required_setting='adjust_index_to_environment=true',
                    condition_source='OpticStudio 2024 R2 Environment help')


class ModelingMixin:
    @staticmethod
    def _hologram2_persistence(value):
        return dict(status="verified_state_dependent", cell="parameter_13", value=value,
                    variable_persists=value == 1, fixed_persists=True,
                    reason="本机2024 R2：Volume Hologram?=0时Variable重载为Fixed；值为1时Variable可保持。",
                    reference="docs/solve-support.md#hologram2-模式持久化")

    def _validate_hologram2_mode(self, row, name, mode, value=None):
        if str(row.Type) != "Hologram2" or name != "parameter_13":
            return
        if value is None:
            value = self._cell_value(self._cell(row, name))
        if mode == "Variable" and value != 1:
            raise ZemaxError("UNSUPPORTED_SOLVE", "Volume Hologram?=0时Variable不能保存重载；该状态请使用Fixed。",
                             surface=int(row.SurfaceNumber), surface_type="Hologram2", cell=name,
                             requested="Variable", value=value, persistence=self._hologram2_persistence(value))

    def _validate_hologram2_batch(self, changes):
        """Check the final requested boolean/mode before any checkpoint or write."""
        for change in changes:
            row = self._row(change.surface)
            if (change.surface_type or str(row.Type)) != "Hologram2":
                continue
            cell = self._cell(row, "parameter_13") if str(row.Type) == "Hologram2" else None
            value = self._cell_value(cell) if cell is not None else 0
            mode = str(cell.Solve) if cell is not None else "Fixed"
            if 13 in change.parameters:
                value = change.parameters[13]
                if value not in (0, 1):
                    raise ZemaxError("INVALID_ARGUMENT", "Volume Hologram?只能为0或1。",
                                     surface=change.surface, cell="parameter_13", value=value)
                if change.replace_solves and mode not in ("Fixed", "Variable"):
                    mode = "Fixed"
            if "parameter_13" in change.solves:
                mode = SOLVES[change.solves["parameter_13"].mode]
            if mode == "Variable" and value != 1:
                raise ZemaxError("UNSUPPORTED_SOLVE", "请求的最终状态不能保持Variable；禁用体全息时请显式设为Fixed。",
                                 surface=change.surface, surface_type="Hologram2", cell="parameter_13",
                                 requested="Variable", value=value, persistence=self._hologram2_persistence(value))

    def _validate_aperture_batch(self, changes):
        """Validate the final graph, including unchanged pickup edges."""
        if not any(change.aperture is not None for change in changes):
            return
        edges = {}
        for index in range(self.system.LDE.NumberOfSurfaces):
            aperture = self._row(index).ApertureData
            if aperture.IsPickedUp:
                edges[index] = int(aperture.PickupFrom)
        for change in changes:
            if change.aperture is None:
                continue
            edges.pop(change.surface, None)
            if change.aperture.pickup_from is not None:
                self._row(change.aperture.pickup_from)
                edges[change.surface] = change.aperture.pickup_from
        finished = set()
        for start in edges:
            path, positions = [], {}
            node = start
            while node in edges and node not in finished:
                if node in positions:
                    cycle = path[positions[node]:] + [node]
                    raise ZemaxError("INVALID_SOLVE", "孔径拾取循环。", cycle=cycle)
                positions[node] = len(path)
                path.append(node)
                node = edges[node]
            finished.update(path)

    def _extended_settings(self):
        d=self.system.SystemData
        gcrs=getattr(getattr(d,"Aperture",None),"GCRS",None)
        return dict(afocal_mode_units=str(d.Units.AfocalModeUnits),settings_activity=dict(apodization_factor_is_used=bool(d.Aperture.ApodizationFactorIsUsed)),author=str(d.TitleNotes.Author),**read_pages(d,SYSTEM_PAGES),global_reference_surface=int(gcrs.GetSelectedSurface())if gcrs is not None and str(self.system.Mode)=="Sequential"else None,
            material_catalogs=[str(x) for x in d.MaterialCatalogs.GetCatalogsInUse() if str(x).strip()], polarization=values(d.Polarization,POL), ray_aiming=values(d.RayAiming,AIM), files=values(d.Files,FILES))

    def _validate_settings_extension(self,req):
        d=self.system.SystemData
        if req.temperature_c is not None or req.pressure_atm is not None:
            validate_environment_patch(d.Environment, req)
        if req.aperture_options is not None:self._require_sequential()
        apply_pages(getattr(self,"native",None),d,req,SYSTEM_PAGES,validate=True)
        if req.global_reference_surface is not None:
            self._require_sequential();self._row(req.global_reference_surface)
        for key,name in UNIT_SETTINGS.items():
            value=getattr(req,key)
            if value is not None:self.native.enum(d.Units.GetType().GetProperty(name).PropertyType,value)
        if req.material_catalogs is not None:
            available={str(x).casefold():str(x) for x in (*d.MaterialCatalogs.GetAvailableCatalogs(), *d.MaterialCatalogs.GetCatalogsInUse()) if str(x).strip()}
            names=[x.casefold() for x in req.material_catalogs]
            if len(set(names))!=len(names) or any(x not in available for x in names):
                raise ZemaxError("INVALID_RESOURCE","材料目录无效或重复。")
            sequential=str(self.system.Mode)=="Sequential"
            rows=[(i,self._row(i))for i in range(self.system.LDE.NumberOfSurfaces)] if sequential else [(i,self._object(i))for i in range(1,self.system.NCE.NumberOfObjects+1)]
            for i,row in rows:
                catalog=str(row.MaterialCatalog) if sequential else str(row.FindMaterialCatalog())
                if str(row.Material).strip().upper() not in {"", "-", "MIRROR", "ABSORB"} and catalog and catalog.casefold().removesuffix(".agf") not in names:
                    raise ZemaxError("CATALOG_IN_USE","曲面仍引用此目录。", surface=i,catalog=catalog)
        for patch,obj,mapping,enums in ((req.polarization,d.Polarization,POL,{"method"}),(req.ray_aiming,d.RayAiming,AIM,{"mode","method"})):
            if patch is not None:
                for key,value in patch_values(patch).items():
                    if key in enums: self.native.enum(obj.GetType().GetProperty(mapping[key]).PropertyType,value)
        if req.files is not None:
            for key,value in patch_values(req.files).items():
                if value not in list(getattr(d.Files,FILE_METHODS[key])()):
                    raise ZemaxError("INVALID_RESOURCE","文件不在本机可用列表中。",field=key,value=value)
        if req.field_updates:
            for update in req.field_updates:
                patch_values(update)
                if update.number>d.Fields.NumberOfFields or len(update.model_fields_set)<2:
                    raise ZemaxError("INVALID_ARGUMENT","视场编号越界或无渐晕修改。")

    def _apply_settings_extension(self,req):
        from .detectors import checked_setting
        d=self.system.SystemData
        apply_pages(getattr(self,"native",None),d,req,SYSTEM_PAGES)
        if req.author is not None:checked_setting(self.native,d.TitleNotes,"Author",req.author)
        if req.global_reference_surface is not None:
            from .detectors import check_setting_value
            selector=d.Aperture.GCRS
            if not selector.SetSelectedSurface(req.global_reference_surface):raise ZemaxError("SETTING_REJECTED","全局参考面未被原生采用。",requested=req.global_reference_surface)
            check_setting_value("global_reference_surface",req.global_reference_surface,selector.GetSelectedSurface())
        for key,name in UNIT_SETTINGS.items():
            if getattr(req,key)is not None:checked_setting(self.native,d.Units,name,getattr(req,key))
        if req.vignetting_action == "calculate": d.Fields.SetVignetting()
        elif req.vignetting_action == "clear": d.Fields.ClearVignetting()
        if req.material_catalogs is not None:
            catalog=d.MaterialCatalogs
            canonical={str(x).casefold():str(x) for x in (*catalog.GetAvailableCatalogs(), *catalog.GetCatalogsInUse()) if str(x).strip()}
            desired=[canonical[x.casefold()] for x in req.material_catalogs]
            current=[str(x) for x in catalog.GetCatalogsInUse() if str(x).strip()]
            for name in desired:
                if name.casefold() not in {str(x).casefold() for x in current} and not catalog.AddCatalog(name):
                    raise ZemaxError("RESOURCE_UPDATE_FAILED","添加目录失败。",catalog=name)
            for name in current:
                if str(name).casefold() not in {x.casefold() for x in desired} and not catalog.RemoveCatalog(name):
                    raise ZemaxError("RESOURCE_UPDATE_FAILED","移除目录失败。",catalog=str(name))
        for patch,obj,mapping,enums in ((req.polarization,d.Polarization,POL,{"method"}),(req.ray_aiming,d.RayAiming,AIM,{"mode","method"})):
            if patch is not None:
                updates = list(patch_values(patch).items())
                if mapping is POL:
                    target_unpolarized = dict(updates).get("unpolarized", bool(obj.Unpolarized))
                    # Native Jones/phase setters are inactive while Unpolarized is enabled.
                    if any(key != "unpolarized" for key, _ in updates):
                        if obj.Unpolarized:
                            checked_setting(self.native,obj,"Unpolarized",False)
                        updates = [(key, value) for key, value in updates if key != "unpolarized"]
                        updates.append(("unpolarized", target_unpolarized))
                    # Preserve a nonzero Jones vector while swapping X/Y polarization.
                    updates.sort(key=lambda item: (2 if item[0] == "unpolarized" else
                                                  0 if item[0] in {"jx", "jy"} and item[1] > 0 else 1))
                for key,value in updates:
                    checked_setting(self.native,obj,mapping[key],value)
                if mapping is POL:
                    from .detectors import check_setting_readback
                    for key,value in updates:
                        check_setting_readback(obj,mapping[key],value)
        if req.files is not None:
            for key,value in patch_values(req.files).items():checked_setting(self.native,d.Files,FILES[key],value)
            d.Files.ReloadFiles()
        if req.field_normalization is not None:
            checked_setting(self.native,d.Fields,"Normalization",req.field_normalization)
        for update in req.field_updates or []:
            field=d.Fields.GetField(update.number)
            for k,v in patch_values(update).items():
                if k!="number":checked_setting(self.native,field,k.upper(),v)

    def get_system_resources(self,req):
        if req.kind == 'test_plate_files':
            from .test_plates import catalog_resources
            directory,names=catalog_resources(self.native.application)
            items=[n for n in names if req.query.casefold() in n.casefold()]
            end=min(len(items),req.start+req.count)
            return dict(kind=req.kind,directory=str(directory),items=items[req.start:end],total=len(items),next_start=end if end<len(items) else None)
        if req.kind == 'extension_files':
            from .extension_resources import extension_files
            return extension_files(self.native.application, req)
        d=self.system.SystemData
        if req.kind=="catalogs": items=sorted({str(x) for x in (*d.MaterialCatalogs.GetAvailableCatalogs(), *d.MaterialCatalogs.GetCatalogsInUse()) if str(x).strip()})
        elif req.kind=="materials":
            if req.catalog.casefold() not in {str(x).casefold() for x in (*d.MaterialCatalogs.GetAvailableCatalogs(), *d.MaterialCatalogs.GetCatalogsInUse()) if str(x).strip()}:
                raise ZemaxError("INVALID_RESOURCE","目录不存在。",catalog=req.catalog)
            items=list(d.MaterialCatalogs.GetMaterialsInCatalog(req.catalog))
        elif req.kind in {"image_simulation_files","geometric_image_files"}:
            from .imaging import resource_names
            items=resource_names(self,req.kind)
        elif req.kind=="solve_macros":
            cell=self._cell(self._row(req.surface),req.cell)
            mode=self.native.api.Editors.SolveType.ZPLMacro
            if not cell.IsSolveTypeSupported(mode):
                raise ZemaxError("UNSUPPORTED_SOLVE","此单元格不支持 ZPLMacro。",cell=req.cell)
            items=list(cell.CreateSolveType(mode)._S_ZPLMacro.GetAvailableMacros())
        elif req.kind=="coatings": items=list(self._row(req.surface).CoatingData.GetAvailableCoatings())
        elif req.kind=="surface_types":items=[str(x) for x in self._row(req.surface).AvailableSurfaceTypes()]
        elif req.kind=="surface_files":
            row=self._row(req.surface)
            setting=row.GetSurfaceTypeSettings(self.native.enum(self.native.api.Editors.LDE.SurfaceType,req.surface_type or str(row.Type)))
            items=[str(x) for x in setting.GetFileNames()] if setting.RequiresFile else []
        elif req.kind=="aperture_files":
            a=self._row(req.surface).ApertureData
            holder=a.CreateApertureTypeSettings(self.native.api.Editors.LDE.SurfaceApertureTypes.UserAperture)
            items=list(holder._S_UserAperture.GetAvailableFiles())
        elif req.kind=="scattering_files":
            from .scattering_pages import settings,RESOURCES,resource_names
            _,obj=settings(self.native,self._row(req.surface),req.scattering_type)
            items=resource_names(obj,req.scattering_type) if req.scattering_type in RESOURCES else []
        elif req.kind=="surface_import_files":items=[str(x) for x in self._row(req.surface).ImportData.GetImportFiles("*.dat")]
        else:
            methods=dict(coating_files="GetCoatingFiles",scatter_profiles="GetScatterProfiles",abg_files="GetABgDataFiles",gradium_profiles="GetGradiumProfiles")
            items=list(getattr(d.Files,methods[req.kind])())
        items=[str(x) for x in items if req.query.casefold() in str(x).casefold()]
        end=min(len(items),req.start+req.count)
        result=dict(kind=req.kind,items=items[req.start:end],total=len(items),next_start=end if end<len(items) else None)
        if req.kind in {"image_simulation_files","geometric_image_files"}:
            result['directory']=str(self.native.application.ImagesDir)
        return result

    def _surface_properties(self,row):
        from .scattering_pages import read_scattering
        a=row.ApertureData
        setting=a.CurrentTypeSettings
        detail={}
        if str(a.CurrentType)!="None":
            obj=getattr(setting,"_S_"+str(a.CurrentType))
            detail={k:getattr(obj,v) for k,v in APERTURE.items() if hasattr(obj,v)}
        file_settings=row.CurrentTypeSettings
        mechanical={key:dict(value=float(getattr(row,attr)),solve=str(getattr(row,attr+'Cell').Solve))
                    for key,attr in (('mechanical_semi_diameter','MechanicalSemiDiameter'),('chip_zone','ChipZone'))if hasattr(row,attr)}
        return dict(property_activity=dict(has_mirror_settings=bool(row.DrawData.HasMirrorSettings),can_be_stop=bool(row.TypeData.CanBeStop),can_be_gcr=bool(row.TypeData.CanBeGCR)),scattering=read_scattering(row),**read_pages(row,SURFACE_PAGES),disable_clear_semi_diameter_margins=bool(a.DisableClearSemiDiameterMarginsForThisSurface),surface_file=str(file_settings.Filename) if file_settings.RequiresFile else None,coating=str(row.Coating),material_catalog=str(row.MaterialCatalog) if str(row.Material).strip() else None,mechanical=mechanical,aperture=dict(type=str(a.CurrentType),pickup_from=int(a.PickupFrom) if a.IsPickedUp else None,**detail),tilt_decenter=dict(**values(row.TiltDecenterData,TILT),after_mode=str(row.TiltDecenterData.AfterSurfaceMode)))

    def _validate_surface_extension(self,row,change):
        if change.scattering is not None:
            from .scattering_pages import set_scattering
            set_scattering(self.native,row,change.scattering,validate=True)
        apply_pages(getattr(self,"native",None),row,change,SURFACE_PAGES,validate=True)
        for key,attr in (('mechanical_semi_diameter','MechanicalSemiDiameter'),('chip_zone','ChipZone')):
            if getattr(change,key) is not None:
                cell=getattr(row,attr+'Cell')
                transition=(change.replace_solves and cell.IsActive and str(cell.Solve)=='Automatic'
                            and 'Fixed' in [str(value) for value in cell.GetAvailableSolveTypes()])
                if not transition:self._guard_cell(cell,change.replace_solves)
        if change.is_stop and (row.IsObject or row.IsImage): raise ZemaxError("INVALID_ARGUMENT","物面和像面不能设为光阑。")
        if change.coating is not None and change.coating and change.coating not in list(row.CoatingData.GetAvailableCoatings()):
            raise ZemaxError("INVALID_RESOURCE","镀膜不在可用列表中。",coating=change.coating)
        if change.aperture:
            spec=change.aperture
            if spec.type in {"UserAperture","UserObscuration"}:
                a=row.ApertureData
                holder=a.CreateApertureTypeSettings(self.native.enum(self.native.api.Editors.LDE.SurfaceApertureTypes,spec.type))
                if spec.aperture_file not in [str(x) for x in getattr(holder,"_S_"+spec.type).GetAvailableFiles()]:
                    raise ZemaxError("INVALID_RESOURCE","用户孔径文件不在可用列表中。",file=spec.aperture_file)
            if row.ApertureData.IsPickedUp and not spec.replace_pickup:
                raise ZemaxError("SOLVE_PROTECTED","孔径拾取受保护。")
            if spec.pickup_from is not None:
                self._row(spec.pickup_from)
        if change.tilt_decenter:
            spec=change.tilt_decenter; patch_values(spec)
            if (not change.surface_type or str(row.Type)==change.surface_type) and not row.TiltDecenterData.BeforeAfterSurfaceEnabled:
                raise ZemaxError("UNSUPPORTED_SETTING","此曲面不支持显式面前/面后倾斜偏心；坐标断点使用面型参数。")
            if any(k.startswith("after_") for k in spec.model_fields_set) and str(row.TiltDecenterData.AfterSurfaceMode)!="Explicit" and not spec.replace_pickup:
                raise ZemaxError("SOLVE_PROTECTED","面后倾斜偏心拾取受保护。")

    def _apply_surface_extension(self,row,change):
        from .detectors import checked_setting
        apply_pages(getattr(self,"native",None),row,change,SURFACE_PAGES)
        if change.scattering is not None:
            from .scattering_pages import set_scattering
            set_scattering(self.native,row,change.scattering)
        if change.disable_clear_semi_diameter_margins is not None:
            checked_setting(self.native,row.ApertureData,"DisableClearSemiDiameterMarginsForThisSurface",change.disable_clear_semi_diameter_margins)
        if change.is_stop: row.IsStop=True
        if change.coating is not None: row.Coating=change.coating
        if change.aperture:
            spec=change.aperture; a=row.ApertureData
            if spec.pickup_from is not None: a.PickupFrom=spec.pickup_from
            else:
                a.SetPickupNone()
                setting=a.CreateApertureTypeSettings(self.native.enum(self.native.api.Editors.LDE.SurfaceApertureTypes,spec.type))
                if spec.type!="None":
                    obj=getattr(setting,"_S_"+spec.type)
                    for key,attr in APERTURE.items():
                        value=getattr(spec,key)
                        if value is not None and hasattr(obj,attr): checked_setting(self.native,obj,attr,value)
                if not a.ChangeApertureTypeSettings(setting): raise ZemaxError("APERTURE_UPDATE_FAILED","孔径设置失败。")
                if str(a.CurrentType)!=spec.type:raise ZemaxError("SETTING_REJECTED","孔径类型未采用。",requested=spec.type,actual=str(a.CurrentType))
                if spec.type!='None':
                    from .detectors import check_setting_value
                    adopted=getattr(a.CurrentTypeSettings,'_S_'+spec.type)
                    for key,attr in APERTURE.items():
                        requested=getattr(spec,key)
                        if requested is not None and hasattr(adopted,attr):check_setting_value(key,requested,getattr(adopted,attr))

        if change.tilt_decenter:
            patch=patch_values(change.tilt_decenter); obj=row.TiltDecenterData
            if any(k.startswith("after_") for k in patch): obj.SetAfterSurfaceModeExplicit()
            for k,v in patch.items():
                if k=="replace_pickup": continue
                if k.endswith("order"): self.native.set_enum(obj,TILT[k],v)
                else: setattr(obj,TILT[k],v)

    def copy_surfaces(self,req):
        self._require_sequential(); total=int(self.system.LDE.NumberOfSurfaces)
        if req.start+req.count>total-1 or req.at>=total:
            raise ZemaxError("INDEX_OUT_OF_RANGE","复制范围和目标须位于物面与像面之间。")
        stop=int(self.system.LDE.StopSurface)
        self._mutate("copy_surfaces")
        copied=int(self.system.LDE.CopySurfaces(req.start,req.count,req.at))
        if copied!=req.count: raise ZemaxError("PARTIAL_UPDATE","原生复制数量不符。",copied=copied,expected=req.count)
        stop+=copied if req.at<=stop else 0
        self._row(stop).IsStop=True
        return dict(copied=copied,start=req.at,stop_surface=stop,total=int(self.system.LDE.NumberOfSurfaces))

    def get_surface_geometry(self,req):
        if req.scope == 'system':
            return self.start_geometry_check(req)
        self._row(req.surface)
        result=self.system.LDE.GetGlobalMatrix(req.surface)
        matrix=None
        if result[0]:
            matrix=dict(rotation=[list(result[1+i*3:4+i*3]) for i in range(3)],translation=list(result[10:13]))
        rows=[]
        for i,point in enumerate(req.points):
            try:
                ok,sag,alternate=self.system.LDE.GetSag(req.surface,point.x,point.y)
                if not ok or not all(math.isfinite(x) for x in (sag,alternate)): raise ValueError("原生 Sag 无有效结果。")
                rows.append(dict(index=i,x=point.x,y=point.y,sag=sag,alternateSag=alternate,error=None))
            except Exception as exc:
                rows.append(dict(index=i,x=point.x,y=point.y,sag=None,alternateSag=None,error=str(exc)))
        gcrs=self.system.SystemData.Aperture.GCRS
        return dict(surface=req.surface,units=str(self.system.SystemData.Units.LensUnits),global_transform=matrix,global_transform_valid=bool(result[0]),global_reference_surface=int(gcrs.GetSelectedSurface()),formula="global_position = rotation @ local_position + translation",rows=rows)

