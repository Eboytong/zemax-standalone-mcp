"""Detector-arrival attribution from native ZRD ancestry and copied NSC trials."""
import math
from pathlib import Path
from typing import Annotated,Literal

from pydantic import Field,model_validator

from .data import unwrap
from .detectors import check_setting_value
from .errors import ZemaxError
from .schema import FiniteFloat,Index,PositiveIndex,Request


class PathHit(Request):
    object: PositiveIndex
    face: Index | None = None


class GhostChange(Request):
    object: PositiveIndex
    face: Index | None = None
    coating: str | None = None
    material: str | None = None
    x: FiniteFloat | None = None
    y: FiniteFloat | None = None
    z: FiniteFloat | None = None
    tilt_x: FiniteFloat | None = None
    tilt_y: FiniteFloat | None = None

    @model_validator(mode='after')
    def contract(self):
        if (self.coating is None)!=(self.face is None):raise ValueError('镀膜修改须同时提供face和coating。')
        if not any(getattr(self,k) is not None for k in ['coating','material','x','y','z','tilt_x','tilt_y']):raise ValueError('候选修改不能为空。')
        return self


class GhostCandidate(Request):
    name: Annotated[str,Field(min_length=1,max_length=80)]
    changes: Annotated[list[GhostChange],Field(min_length=1,max_length=20)]


class GhostDiagnostics(Request):
    kind: Literal['ghost_diagnostics']
    detector: PositiveIndex
    expected_paths: Annotated[list[Annotated[list[PathHit],Field(min_length=1,max_length=100)]],Field(min_length=1,max_length=20)]
    allowed_objects: Annotated[list[PositiveIndex],Field(max_length=100)] = []
    candidates: Annotated[list[GhostCandidate],Field(max_length=10)] = []
    rays_per_source: Annotated[int,Field(strict=True,ge=1,le=100000)] = 1000
    random_seed: Annotated[int,Field(strict=True,ge=0,le=2147483647)] = 42
    scatter_rays: bool = False
    filter: Annotated[str,Field(max_length=1000)] = ''
    max_segments: Annotated[int,Field(strict=True,ge=1,le=100000)] = 20000
    max_paths: Annotated[int,Field(strict=True,ge=1,le=10000)] = 1000
    minimum_relative_power: Annotated[FiniteFloat,Field(ge=0,le=1)] = 0
    minimum_expected_fraction: Annotated[FiniteFloat,Field(ge=0,le=1)] = .9
    trace_budget_seconds: Annotated[FiniteFloat,Field(gt=0,le=3600)] = 120
    save_best: bool = True

    @model_validator(mode='after')
    def paths(self):
        if any(p[-1].object!=self.detector for p in self.expected_paths):raise ValueError('期望路径须以目标探测器结束，省略光源起点。')
        if len({c.name for c in self.candidates})!=len(self.candidates):raise ValueError('候选名称不得重复。')
        return self


def matches(sequence,expected):
    return len(sequence)==len(expected) and all(a[0]==e.object and (e.face is None or a[1]==e.face) for a,e in zip(sequence,expected))


def ancestry(segments,index):
    chain=[];visited=set()
    while True:
        if index in visited or index not in segments:raise ZemaxError('INVALID_ZRD_ANCESTRY','父段缺失或循环。',segment=index)
        visited.add(index);row=segments[index];chain.append(row)
        if index==0:break
        parent=int(row['SegmentParent'])
        if parent>=index:raise ZemaxError('INVALID_ZRD_ANCESTRY','父段编号未先于子段。',segment=index,parent=parent)
        index=parent
    return list(reversed(chain))


def classify_arrivals(rows,q,detector_power):
    rays={};groups={};errors=[];read_power=0.;ancestry_power=0.
    for row in rows:rays.setdefault(int(row['ray_index']),{})[int(row['segment_index'])]=row
    for ray_id,segments in rays.items():
        for index,row in segments.items():
            if int(row['HitObject'])!=q.detector:continue
            power=float(row['Intensity'])
            if not math.isfinite(power) or power<0:raise ZemaxError('INVALID_RESULT_DATA','探测器到达功率无效。',ray=ray_id,segment=index)
            read_power+=power
            try:chain=ancestry(segments,index)
            except ZemaxError as exc:errors.append(dict(ray=ray_id,segment=index,power=power,error=exc.details));ancestry_power+=power;continue
            if any(v.get('RayError') for v in chain):
                errors.append(dict(ray=ray_id,segment=index,power=power,error='native RayError in ancestry'));ancestry_power+=power;continue
            sequence=[(int(v['HitObject']),int(v['HitFace'])) for v in chain if int(v['HitObject'])>0]
            reflections=[];unknown_normals=0
            for parent,child in zip(chain,chain[1:]):
                normal=[parent.get(k) for k in ['XNorm','YNorm','ZNorm']]
                if any(v is None for v in normal) or sum(float(v)**2 for v in normal)<.5:
                    if parent.get('SegReflected'):unknown_normals+=1
                    continue
                incoming=[float(parent[k]) for k in ['L','M','N']];outgoing=[float(child[k]) for k in ['L','M','N']]
                a=sum(v*float(n) for v,n in zip(incoming,normal));c=sum(v*float(n) for v,n in zip(outgoing,normal))
                if a*c<-1e-12:reflections.append((int(parent['HitObject']),int(parent['HitFace'])))
            scattering=any(v.get('SegScattered') or v.get('SegBulkScattered') for v in chain)
            if any(matches(sequence,p) for p in q.expected_paths):category='expected'
            elif scattering:category='scatter_related'
            elif reflections:category='ghost'
            elif q.allowed_objects and all(obj in q.allowed_objects or obj==q.detector for obj,face in sequence):category='allowed'
            else:category='unexpected'
            key=(category,tuple(sequence),tuple(reflections))
            item=groups.setdefault(key,dict(category=category,sequence=[dict(object=o,face=f) for o,f in sequence],
                reflection_faces=[dict(object=o,face=f) for o,f in reflections],power=0.,arrivals=0,normal_unknown=0,
                representative=dict(ray_index=ray_id,segment_index=index,wavelength_um=float(row['WlUM']),position=[float(row[k]) for k in ['X','Y','Z']])))
            item['power']+=power;item['arrivals']+=1;item['normal_unknown']+=unknown_normals
    ordered=sorted(groups.values(),key=lambda g:-g['power']);retained=[];excluded=[]
    for group in ordered:
        group['fraction_of_detector']=group['power']/detector_power if detector_power>0 else None
        if group['power']<q.minimum_relative_power*detector_power:excluded.append(group|dict(reason='relative_power_threshold'))
        elif len(retained)>=q.max_paths:excluded.append(group|dict(reason='path_limit'))
        else:retained.append(group)
    totals={name:sum(g['power'] for g in retained if g['category']==name) for name in ['expected','allowed','ghost','scatter_related','unexpected']}
    retained_power=sum(totals.values());residual=detector_power-read_power
    return dict(paths=retained,excluded_paths=excluded,ancestry_errors=errors,
        power=dict(detector=detector_power,read_arrivals=read_power,retained=retained_power,**totals,
            excluded=sum(g['power'] for g in excluded),ancestry_unclassified=ancestry_power,unread_or_precision_residual=residual,
            unclassified=detector_power-retained_power),
        precision='ZRD uncompressed intensity stored in native single precision; detector scalar retained independently',
        reflection_definition='sign change of direction-normal product between parent incoming and child outgoing segment',
        scatter_definition='ancestry contains native scattering flag; specular/scattered children of that interaction share this attribution')


def apply_changes(b,system,candidate):
    actual=[]
    for change in candidate.changes:
        if change.object>int(system.NCE.NumberOfObjects):raise ZemaxError('INDEX_OUT_OF_RANGE','候选对象编号越界。',object=change.object)
        row=system.NCE.GetObjectAt(change.object);values={}
        for key,attr,col in [('x','XPosition','XPosition'),('y','YPosition','YPosition'),('z','ZPosition','ZPosition'),('tilt_x','TiltAboutX','TiltX'),('tilt_y','TiltAboutY','TiltY'),('material','Material','Material')]:
            value=getattr(change,key)
            if value is None:continue
            b._guard_nsc_cell(row.GetObjectCell(b.native.enum(b.native.api.Editors.NCE.ObjectColumn,col)),False)
            setattr(row,attr,value);check_setting_value(key,value,getattr(row,attr));values[key]=getattr(row,attr)
        if change.coating is not None:
            data=row.CoatScatterData
            if not data.IsCoatScatterAvailable or change.face>=int(data.NumberOfFaces):raise ZemaxError('INDEX_OUT_OF_RANGE','候选面号越界。')
            face=data.GetFaceData(change.face)
            if change.coating not in [str(v) for v in face.GetAvailableCoatings()]:raise ZemaxError('INVALID_RESOURCE','候选镀膜不存在。',coating=change.coating)
            if not face.UseCustomSettings():raise ZemaxError('SETTING_REJECTED','候选面自定义设置未采用。')
            face.Coating=change.coating;check_setting_value('Coating',change.coating,str(face.Coating));values.update(face=change.face,coating=str(face.Coating))
        actual.append(dict(object=change.object,values=values))
    system.UpdateStatus()
    # Check the final combination after all dependent edits and native update.
    for change,item in zip(candidate.changes,actual):
        row=system.NCE.GetObjectAt(change.object)
        for key,attr in [('x','XPosition'),('y','YPosition'),('z','ZPosition'),('tilt_x','TiltAboutX'),('tilt_y','TiltAboutY'),('material','Material')]:
            if getattr(change,key) is not None:
                value=getattr(row,attr);check_setting_value(key,getattr(change,key),value);item['values'][key]=value
        if change.coating is not None:
            value=str(row.CoatScatterData.GetFaceData(change.face).Coating)
            check_setting_value('Coating',change.coating,value);item['values']['coating']=value
    return actual


def face_metadata(system,paths):
    pairs=sorted({(h['object'],h['face']) for p in paths for h in p['sequence']});result=[]
    for obj,number in pairs:
        row=system.NCE.GetObjectAt(obj);item=dict(object=obj,face=number,type=str(row.Type),material=str(row.Material))
        data=row.CoatScatterData
        if data.IsCoatScatterAvailable and number<int(data.NumberOfFaces):
            face=data.GetFaceData(number);item.update(coating=str(face.Coating),scatter_model=str(face.CurrentScatterModel))
        result.append(item)
    return result


def run_ghost_diagnostics(b,q):
    from .nonsequential import NonSequentialMixin
    from .nsc_models import ZrdRead
    from .evaluation import Cancelled
    class Reader:
        read_zrd=NonSequentialMixin.read_zrd
        def __init__(self,system):self.system=system;self.native=b.native;self._composite=b._composite;self._cancel_boundary=b._cancel_boundary;self._release_owned=b._release_owned
        def _require_nsc(self):pass
    b._require_nsc();b._require_work()
    def flow(task):
        system=None;error=None;created=0;closed=0;cleanup=[]
        task['payload']=dict(analysis_kind=q.kind,series=[],grids=[],candidates=[],units=dict(power='W',position='lens units'),
            computation_method='native polarized splitting NSC trace, native ZRD parent tree, detector arrival power')
        task['restoration']=dict(required=False,restored=True,reason='each baseline/candidate uses own copy; source detector buffers unchanged')
        def close():
            nonlocal system,closed
            if system is None:return
            try:
                if system.Close(False) is False:raise RuntimeError('Close(False) returned false')
                closed+=1
            except Exception as exc:cleanup.append(str(exc));b.requires_reconnect=True
            finally:system=None
        try:
            for index,candidate in enumerate([None]+q.candidates):
                b._cancel_boundary(task);entry=dict(candidate=index,name=candidate.name if candidate else 'baseline')
                try:
                    system=b.system.CopySystem()
                    if system is None:raise ZemaxError('COPY_FAILED','无法创建鬼像诊断副本。')
                    created+=1
                    if q.detector>int(system.NCE.NumberOfObjects) or str(system.NCE.GetObjectAt(q.detector).Type)!='DetectorRectangle':raise ZemaxError('UNSUPPORTED_DETECTOR','鬼像诊断使用DetectorRectangle。')
                    if str(system.SystemData.Units.SourceUnits)!='Watts' or str(system.SystemData.Units.SourceUnitPrefix)!='None':raise ZemaxError('UNSUPPORTED_UNITS','鬼像功率采用无前缀Watts。')
                    from .analyses import scalar_settings
                    entry['native_trace_limits']=scalar_settings(system.SystemData.NonSequentialData)
                    entry['actual_changes']=apply_changes(b,system,candidate) if candidate else []
                    sources=[]
                    for i in range(1,int(system.NCE.NumberOfObjects)+1):
                        r=system.NCE.GetObjectAt(i);data=unwrap(r.ObjectData)
                        if not bool(r.SourcesData.IsSourcesAvailable):continue
                        if not hasattr(data,'NumberOfAnalysisRays'):raise ZemaxError('UNSUPPORTED_SOURCE','源缺少正式分析光线数入口。',object=i)
                        data.NumberOfAnalysisRays=q.rays_per_source;check_setting_value('NumberOfAnalysisRays',q.rays_per_source,int(data.NumberOfAnalysisRays))
                        if hasattr(data,'RandomSeedCell'):b._write_cell(data.RandomSeedCell,0)
                        if not hasattr(data,'Power'):raise ZemaxError('UNSUPPORTED_SOURCE','源缺少正式功率入口。',object=i)
                        power=float(data.Power)
                        if not math.isfinite(power) or power<0:raise ZemaxError('INVALID_SOURCE_POWER','源功率须为有限非负值。',object=i,power=str(power))
                        sources.append(dict(object=i,type=str(r.Type),power=power,rays=int(data.NumberOfAnalysisRays)))
                    if not sources or len(sources)*q.rays_per_source>1000000:raise ZemaxError('RESOURCE_LIMIT','光源须非空且总发射光线数不超过1000000。')
                    entry['sources']=sources
                    model=Path(b.directory)/(task['task_id']+f'_ghost_{index}.zos');system.SaveAs(str(model))
                    basename=task['task_id']+f'_ghost_{index}.zrd';zrd=model.parent/basename
                    def start(_):
                        tool=system.Tools.OpenNSCRayTrace()
                        try:
                            if str(tool.ClearDetectors(0))!='Success':raise ZemaxError('DETECTOR_CLEAR_FAILED','副本探测器清空失败。')
                            for name,value in dict(UsePolarization=True,SplitNSCRays=True,ScatterNSCRays=q.scatter_rays,IgnoreErrors=False,NumberOfCores=1,SaveRays=True,SaveRaysFile=basename,Filter='').items():
                                setattr(tool,name,value);check_setting_value(name,value,getattr(tool,name))
                            tool.SetRandomSeed(q.random_seed)
                            def collect(child):
                                if not tool.Succeeded:raise ZemaxError('NSC_TRACE_FAILED',str(tool.ErrorMessage))
                                dead=float(tool.DeadRayErrors)
                                if not math.isfinite(dead) or dead!=0:raise ZemaxError('NSC_TRACE_ERRORS','诊断追迹含错误光线。',dead_ray_errors=dead)
                                if not b._close_task_native(child):raise ZemaxError('CLEANUP_FAILED','诊断追迹工具关闭失败。')
                                ok,power=system.NCE.GetDetectorData(q.detector,0,0,0.)
                                if not ok or not math.isfinite(float(power)):raise ZemaxError('INVALID_DETECTOR_DATA','探测器总功率读取失败。')
                                return dict(detector_power=float(power),dead_ray_errors=dead,zrd=str(zrd))
                            return b._start_task('ghost_nsc_trace',tool,dict(use_polarization=True,split_rays=True,scatter_rays=q.scatter_rays,random_seed=q.random_seed,number_of_cores=1),collector=collect,budget_seconds=q.trace_budget_seconds)
                        except Exception:tool.Close();raise
                    trace=yield from b._child_job(task,start,None);entry['trace']=trace
                    reader=Reader(system)
                    database=yield from b._child_job(task,reader.read_zrd,ZrdRead(path=str(zrd),filter=q.filter,max_segments=q.max_segments))
                    result=classify_arrivals(database['rows'],q,trace['detector_power'])
                    entry.update(result,read_summary=database['summary'],face_metadata=face_metadata(system,result['paths']),state='succeeded',saved_model=str(model),zrd=str(zrd))
                    for rank,path in enumerate(result['paths']):task['rows'].append(dict(candidate=index,rank=rank,**path))
                except Cancelled:raise
                except Exception as exc:
                    entry.update(state='failed',error=b._evaluation_error(exc))
                    if b.requires_reconnect:raise
                finally:close();entry['copy_closed']=not cleanup
                task['payload']['candidates'].append(entry)
                if cleanup:raise ZemaxError('CLEANUP_FAILED','鬼像副本关闭失败。',cleanup_errors=cleanup,operation_error=entry.get('error'))
                yield
            valid=[c for c in task['payload']['candidates'] if c['state']=='succeeded']
            if not valid:raise ZemaxError('NO_VALID_CANDIDATE','基线及候选均未完成诊断。')
            baseline=next((c for c in valid if c['candidate']==0),None)
            if baseline is None:raise ZemaxError('NO_VALID_BASELINE','原模型未完成诊断，无法建立同条件候选对照。')
            for entry in valid:
                entry['eligible']=entry['power']['expected']>=q.minimum_expected_fraction*baseline['power']['expected']
                entry['change_from_baseline']={k:entry['power'][k]-baseline['power'][k] for k in entry['power']}
            # Preserve useful throughput while reducing unwanted detector contribution.
            best=min([c for c in valid if c['eligible']],key=lambda c:(c['power']['ghost']+c['power']['scatter_related']+c['power']['unexpected']+max(0,c['power']['unclassified']),-c['power']['expected']))
            task['summary']=dict(candidate_count=len(task['payload']['candidates']),succeeded=len(valid),best_candidate=best['candidate'],best_name=best['name'],
                best_model=best['saved_model'] if q.save_best else None,best_power=best['power'],
                ranking='retain minimum_expected_fraction of baseline expected power; minimum unwanted detector power, then maximum expected-path power',
                limits=dict(max_segments=q.max_segments,max_paths=q.max_paths,minimum_relative_power=q.minimum_relative_power,filter=q.filter))
            task['payload']['artifacts']=[dict(kind='zrd',path=c['zrd']) for c in valid]
            task['payload']['series']=[dict(series=0,description='Detector path power',x_label='candidate',x_unit='index',y_unit='W',labels=['expected','ghost','unclassified'],
                x=[c['candidate'] for c in valid],y=[[c['power'][k] for k in ['expected','ghost','unclassified']] for c in valid])]
        except BaseException as exc:error=exc;raise
        finally:
            close();task['payload']['resources']=dict(copies_created=created,copies_closed=closed,all_copies_closed=created==closed,cleanup_errors=cleanup)
            if cleanup:raise ZemaxError('CLEANUP_FAILED','鬼像副本关闭失败。',cleanup_errors=cleanup,operation_error=b._evaluation_error(error) if error else None)
    return b._composite(q.kind,q.model_dump(),flow,require_sequential=False)
