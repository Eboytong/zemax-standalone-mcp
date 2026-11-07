"""Native path statistics, exact native sequences and owned task lifecycle."""
import math,shutil,uuid
from pathlib import Path
from .data import unwrap,dotnet_array
from .errors import ZemaxError
from .files import input_path
from .analyses import scalar_settings
from .imaging import new_analysis,checked,check
from .detectors import check_setting_value

SORT_ALIAS={'NumberOfUniqueObjectsStruck':'NumberOfUniqueObjectsStruct'}
FIELDS=dict(first_ray='FirstRay',last_ray='LastRay',filter='FilterString',generate_path_filters='GeneratePathFilters',relative_minimum_flux='RelativeMinimumFlux')
COUNTS=dict(path_number='PathNumber',rays='RaysInPath',hits='HitsInPath',ghosts='GhostsInPath',unique_objects='UniqueObjectsInPath',object_count='NumberOfObjectsInPath',source='PathSource')


def finite(value,name):
    value=float(value)
    if not math.isfinite(value):raise ZemaxError('INVALID_RESULT_DATA','原生路径统计包含非有限值。',field=name)
    return value


def entry_data(entry):
    if entry is None:raise ZemaxError('INVALID_RESULT_DATA','原生路径条目为空。')
    row={key:int(getattr(entry,name))for key,name in COUNTS.items()}
    count=row['object_count']
    if not 0<=count<=10000:raise ZemaxError('INVALID_RESULT_DATA','原生路径对象数超出读取界限。',count=count)
    objects=[int(v)for v in entry.PathObjectList]
    matrix=entry.PathObjectAndFaceList
    shape=[int(matrix.GetLength(i))for i in range(matrix.Rank)]
    if matrix.Rank!=2 or shape not in [[count,2],[2,count]]:
        raise ZemaxError('INVALID_RESULT_DATA','路径对象/面数组形状不符。',count=count,shape=shape)
    faces=dotnet_array(matrix)
    if len(objects)>count:raise ZemaxError('INVALID_RESULT_DATA','路径对象数组长度超过交互数。',declared=count,actual=len(objects))
    row.update(total_path_flux_w=finite(entry.TotalPathFlux,'TotalPathFlux'),objects=objects,
        native_object_list_length=len(objects),native_object_face_matrix=[[int(v)for v in line]for line in faces],native_object_face_shape=[int(matrix.GetLength(i))for i in range(2)],
        object_face_axis_definition='native dimensions retained; use path_sequence for unambiguous ordered object.face sequence')
    return row


def collect_paths(backend,task):
    r=unwrap(task['native'].GetResults())
    if r is None or not r.IsValid:raise ZemaxError('ANALYSIS_FAILED','路径分析没有有效原生结果。')
    data=unwrap(r.PathAnalysisData)
    if data is None:raise ZemaxError('RESULT_UNAVAILABLE','原生未提供PathAnalysisData。')
    count=int(data.NumPaths)
    if not 0<=count<=10000:raise ZemaxError('RESULT_TOO_LARGE','原生路径数量超出10000条读取上限。',count=count)
    entries=list(data.Paths)
    if len(entries)!=count:raise ZemaxError('INVALID_RESULT_DATA','原生路径数量与条目数组不符。',declared=count,actual=len(entries))
    rows=[];seen=set()
    for entry in entries:
        row=entry_data(unwrap(entry));number=row['path_number']
        if number in seen:raise ZemaxError('INVALID_RESULT_DATA','原生路径编号重复。',path_number=number)
        seen.add(number)
        data.PathNumber=number
        check_setting_value('PathNumber',number,int(data.PathNumber))
        row.update(path_sequence=str(data.PathSequence),branches=int(data.PathBranches),last_object=int(data.LastObject),last_face=int(data.LastFace),
            flux_out_w=finite(data.PathFluxOut,'PathFluxOut'),flux_percent=finite(data.PathFluxPercent,'PathFluxPercent'),selected_source=int(data.PathSource),category='classified')
        rows.append(row)
    uncategorized_message=None
    try:
        native_uncategorized=data.GetPathUncategorized()
    except Exception as exc:
        message=str(getattr(exc,'Message',str(exc)))
        if message.partition('\n')[0].rstrip('\r')!='There are no uncategorized paths.':raise
        uncategorized=None
        uncategorized_message=message
    else:
        uncategorized=entry_data(unwrap(native_uncategorized))
        uncategorized['category']='uncategorized'
    result=dict(analysis_kind='path_analysis',computation_method='native_PathAnalysisData',rows=rows,uncategorized=uncategorized,
        uncategorized_native_message=uncategorized_message,
        summary=dict(native_path_count=count,total_rays=int(data.TotalRays),total_hits=int(data.TotalHits),total_flux_in_w=finite(data.TotalFluxIn,'TotalFluxIn'),total_flux_out_w=finite(data.TotalFluxOut,'TotalFluxOut')),
        units=dict(flux='W',flux_percent='percent of total input flux',object_numbers='current NSC editor',face_numbers='native face IDs'),
        native_header=[str(x)for x in r.HeaderData.Lines],native_messages=[dict(code=str(r.GetMessageAt(i).ErrorCode),text=str(r.GetMessageAt(i).Text))for i in range(r.NumberOfMessages)],
        native_limits=dict(object_interactions_per_sequence=100,unique_paths=10000,overflow='native uncategorized path'),artifacts=[])
    path=backend.directory/(task['task_id']+'_native.txt')
    try:
        if r.GetTextFile(str(path)):result['artifacts'].append(dict(kind='native_text',path=str(path)))
        else:result['native_export_error']='GetTextFile returned false'
    except Exception as exc:result['native_export_error']=dict(type=type(exc).__name__,message=str(exc))
    return result


def run_path_analysis(backend,q):
    backend._require_nsc();backend._require_work()
    source=input_path(q.path,{'.zrd','.paf'})
    working=Path(str(backend.system.SystemFile)).parent/('path_'+uuid.uuid4().hex+source.suffix.lower())
    shutil.copyfile(source,working)
    backend.system.UpdateFileLists()
    tool=new_analysis(backend,'PathAnalysis')
    try:
        s=unwrap(tool.GetSettings())
        available=[str(x)for x in s.AvailableRayDatabaseFiles]
        selected=next((x for x in available if x.casefold()==working.name.casefold()),None)
        if selected is None:raise ZemaxError('INVALID_RESOURCE','原生路径分析资源列表没有工作副本。',source=str(source),working=str(working),available=available)
        values={name:getattr(q,key)for key,name in FIELDS.items()}
        values.update(RayDatabaseFile=selected,SortBy=SORT_ALIAS.get(q.sort_by,q.sort_by))
        if q.generate_path_filters:backend._mutate('path_analysis_generate_filters')
        # Resource selection precedes dependent ray/filter values.
        checked(backend.native,s,'RayDatabaseFile',values.pop('RayDatabaseFile'))
        for name,value in values.items():checked(backend.native,s,name,value)
        values['RayDatabaseFile']=selected
        for name,value in values.items():check(backend.native,s,name,value)
        actual=scalar_settings(s)
        if actual.get('unavailable_fields'):raise ZemaxError('SETTING_UNAVAILABLE','路径分析设置回读失败。',details=actual['unavailable_fields'])
        settings=dict(kind=q.kind,requested=q.model_dump(),native=actual,source_database=str(source),working_database=str(working),
            path_filters_effect='checkpoint and revision; named _n filters may persist in working lens'if q.generate_path_filters else'disabled')
    except Exception as exc:
        holder={'native':tool}
        if not backend._close_task_native(holder):
            failure=exc if isinstance(exc,ZemaxError)else ZemaxError('NATIVE_ERROR',str(exc),type=type(exc).__name__)
            failure.details['cleanup_warnings']=holder.get('cleanup_warnings',[])
            if failure is not exc:raise failure from exc
        raise
    return backend._start_task('path_analysis',tool,settings,analysis=True,collector=lambda task:collect_paths(backend,task))
