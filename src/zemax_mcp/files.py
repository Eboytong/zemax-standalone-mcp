"""Native design, archive and project operations owned by the serial worker."""
from pathlib import Path

from .errors import ZemaxError


def output_path(path, extensions, overwrite=False):
    p = Path(path)
    if not p.is_absolute() or p.suffix.lower() not in extensions:
        raise ZemaxError("INVALID_OUTPUT_FILE", "需要绝对路径及允许的扩展名。", extensions=sorted(extensions))
    p = p.resolve()
    if p.exists() and (not overwrite or not p.is_file()):
        raise ZemaxError("OUTPUT_EXISTS", "目标已存在；文件覆盖须显式允许。", path=str(p))
    return p


def input_path(path, extensions):
    p = Path(path)
    if not p.is_absolute() or p.suffix.lower() not in extensions or not p.is_file():
        raise ZemaxError("INVALID_INPUT_FILE", "需要现有文件的绝对路径及允许的扩展名。", extensions=sorted(extensions))
    return p.resolve()


class FilesMixin:
    @staticmethod
    def _copy_project_resources(source,destination):
        """Stage project resource folders before native SaveAs changes its lookup root."""
        import shutil
        source,destination=Path(source).resolve(),Path(destination).resolve()
        if source==destination:return
        names=('ABg_Data','ScatterData','Glasscat','Coatings','Profiles','DLL','Objects','POP','MeritFunction','Tolerance','Configs')
        pairs=[(source/name,destination/name) for name in names if (source/name).is_dir()]
        for original,target in pairs:
            if target.is_relative_to(original):
                raise ZemaxError('PROJECT_COPY_FAILED','工作目录不能位于待复制资源目录内部。',source=str(original),target=str(target))
            if target.exists():
                raise ZemaxError('OUTPUT_EXISTS','项目输出目录已包含同名资源目录。',path=str(target))
        destination.mkdir(parents=True,exist_ok=True)
        try:
            for original,target in pairs:shutil.copytree(original,target)
        except OSError as exc:
            raise ZemaxError('PROJECT_COPY_FAILED','项目资源复制失败。',source=str(source),destination=str(destination),reason=str(exc)) from exc

    def _require_work(self):
        if self.work_path is None:
            raise ZemaxError("NO_WORKING_MODEL", "请先新建或打开镜头。")

    def _release_owned(self, native):
        holder = {"native": native}
        if not self._close_task_native(holder):
            raise ZemaxError("CLEANUP_FAILED", "原生资源释放未确认。", warnings=holder.get("cleanup_warnings"))

    def copy_system(self, req):
        self._require_work()
        path = output_path(req.path, {".zos", ".zmx"}, req.overwrite)
        path.parent.mkdir(parents=True, exist_ok=True)
        copy = self.system.CopySystem()
        if copy is None:
            raise ZemaxError("COPY_FAILED", "未能创建独立系统副本。")
        try:
            copy.SaveAs(str(path))
            return {"path": str(path), "system_id": int(copy.SystemID),
                    "artifacts": [{"kind": "lens", "path": str(path)}]}
        finally:
            try:
                if copy.Close(False) is False:
                    raise RuntimeError("副本 Close 返回 false。")
            except Exception as exc:
                self.requires_reconnect = True
                raise ZemaxError("CLEANUP_FAILED", str(exc)) from exc

    def save_merit_function(self, req):
        self._require_work()
        path = output_path(req.path, {".mf"}, req.overwrite)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.system.MFE.SaveMeritFunction(str(path))
        return {"path": str(path), "artifacts": [{"kind": "merit_function", "path": str(path)}]}

    def load_merit_function(self, req):
        self._require_work()
        path = input_path(req.path, {".mf"})
        self._mutate("before_merit_load")
        self.system.MFE.LoadMeritFunction(str(path))
        return {"path": str(path), "merit_function": self.get_merit_function(None)}

    def create_archive(self, req):
        self._require_work()
        path = output_path(req.path, {".zar"}, req.overwrite)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.system.Save()
        tool = self.system.Tools.OpenCreateZAR()
        try:
            if not tool.SetArchiveFileName(str(path)):
                raise ZemaxError("INVALID_OUTPUT_FILE", "原生工具拒绝归档路径。", path=str(path))
            tool.UseDataCompression = req.compression
        except Exception:
            self._release_owned(tool)
            raise
        def collect(task):
            if not tool.Succeeded:
                raise ZemaxError("ARCHIVE_FAILED", str(tool.ErrorMessage))
            return {"path": str(path), "artifacts": [{"kind": "archive", "path": str(path)}]}
        return self._start_task("create_archive", tool, req.model_dump(), collector=collect)

    def load_archive(self, req):
        self._require_work()
        path = input_path(req.path, {".zar"})
        folder = Path(req.output_directory)
        if not folder.is_absolute() or folder.exists():
            raise ZemaxError("INVALID_OUTPUT_DIRECTORY", "归档须解包到尚不存在的绝对目录。")
        folder = folder.resolve()
        # Configure the native tool before changing the model revision.
        self._mutate("before_archive_load")
        folder.mkdir(parents=True)
        tool = self.system.Tools.OpenRestoreZAR()
        try:
            status = str(tool.SetFileName(str(path)))
            if status != "Okay":
                raise ZemaxError("INVALID_ARCHIVE", "原生归档读取失败。", status=status)
            tool.ExtractAllFilesToProjectDirectory = True
            if not tool.SetOutputFolder(str(folder)):
                raise ZemaxError("INVALID_OUTPUT_DIRECTORY", "原生工具拒绝解包目录。")
            tool.SetFilesNoOverwrite()
            names = [str(tool.GetFileNameInArchive(i)) for i in range(1, tool.NumberOfFilesInArchive+1)]
        except Exception:
            self._release_owned(tool)
            raise
        def collect(task):
            if not tool.Succeeded:
                raise ZemaxError("ARCHIVE_FAILED", str(tool.ErrorMessage))
            if not self._close_task_native(task):
                raise ZemaxError("CLEANUP_FAILED", "归档工具释放失败。")
            # RestoreZAR loads the extracted design into its owning system.
            self.source_path = str(path)
            self.work_path = None
            self.system_context = {}
            loaded=Path(str(self.system.SystemFile)).resolve()
            if not loaded.is_relative_to(folder):
                self.requires_reconnect=True
                raise ZemaxError("RESTORE_FAILED","原生归档未确认加载到指定目录。",system_file=str(loaded),output_directory=str(folder))
            self.work_path=loaded
            self.system.Save()
            summary = self.get_system_summary(None)
            task["context"] = self.context()
            task["system_settings"] = self.get_system_settings(None)
            return {"archive": str(path), "output_directory": str(folder), "files": names,
                    "system": summary}
        # RestoreZAR may replace detector state during Run, including partial failure.
        # Loaded detector data has no trace provenance within this service session.
        self._reset_detector_history(False)
        return self._start_task("load_archive", tool, req.model_dump(), collector=collect)

    def get_project_settings(self, req):
        self._require_work()
        return {"is_project_directory": bool(self.system.IsProjectDirectory),
                "system_file": str(self.system.SystemFile),
                "directory": str(Path(str(self.system.SystemFile)).parent)}

    def update_project_settings(self, req):
        self._require_work()
        folder = None
        if req.operation == "convert":
            folder = Path(req.directory)
            if not folder.is_absolute() or folder.exists():
                raise ZemaxError("INVALID_OUTPUT_DIRECTORY", "项目目录须为尚不存在的绝对目录。")
            folder = folder.resolve()
            folder.parent.mkdir(parents=True, exist_ok=True)
        self._mutate("before_project_update")
        okay = self.system.ConvertToProjectDirectory(str(folder)) if folder else self.system.TurnOffProjectDirectory()
        if not okay:
            raise ZemaxError("PROJECT_UPDATE_FAILED", "原生项目设置失败。")
        self.work_path = Path(str(self.system.SystemFile))
        return self.get_project_settings(None)

    def get_external_dependencies(self, req):
        self._require_work()
        tool = self.system.Tools.OpenFileManager()
        try:
            self.native.set_enum(tool, "Operation", "GetFilesInUse")
            if not tool.RunAndWaitForCompletion() or not tool.Succeeded:
                raise ZemaxError("DEPENDENCY_READ_FAILED", str(tool.ErrorMessage))
            rows = []
            project = Path(str(self.system.SystemFile)).parent
            root = Path(str(self.native.application.ZemaxDataDir))
            folders={"Project":"", "ABgData":"ABg_Data","GlassCat":"Glasscat","Coatings":"Coatings","Configs":"Configs","Profiles":"Profiles","ScatterData":"ScatterData","PopBeamFiles":"POP","MeritFunction":"MeritFunction","Tolerance":"Tolerance","ObjectsCadFiles":"Objects/CAD Files","ObjectsGridFiles":"Objects/Grid Files","ObjectsApertures":"Objects/Apertures","ObjectsSourcesSourceFiles":"Objects/Sources/Source Files","ObjectsSourcesSpectrumFiles":"Objects/Sources/Spectrum Files"}
            for i in range(1, tool.NumberOfFiles+1):
                f = tool.GetFile(i)
                rel = Path(str(f.RelativePath))
                base = project if str(f.Source)=="Project" or str(f.KnownFolder)=="Project" else root
                candidates = [rel] if rel.is_absolute() else [base/rel]
                if not rel.is_absolute() and str(f.KnownFolder)in folders:candidates.append(base/folders[str(f.KnownFolder)]/rel)
                candidates += [p/str(f.Name) for p in list(candidates) if p.name.casefold()!=str(f.Name).casefold()]
                found = next((p for p in candidates if p.is_file()), None)
                rows.append({"name": str(f.Name), "known_folder": str(f.KnownFolder),
                             "relative_path": str(f.RelativePath), "source": str(f.Source),
                             "resolved_path": str(found) if found else None,
                             "resolution": "found" if found else "unresolved",
                             "candidate_paths": [str(p) for p in candidates]})
            end = min(req.start+req.count, len(rows))
            return {"rows": rows[req.start:end], "total": len(rows), "next_start": end if end<len(rows) else None}
        finally:
            self._release_owned(tool)
