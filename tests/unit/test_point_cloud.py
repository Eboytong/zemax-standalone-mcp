from pathlib import Path
from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError
from zemax_mcp.point_cloud import PointCloudExport,export,read_header
from zemax_mcp.errors import ZemaxError
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


@pytest.mark.parametrize('patch',[{'x_sampling':True},{'y_sampling':1},{'x_sampling':4097},
    {'x_sampling':4096,'y_sampling':4096},{'format':'PLY'},{'surface':-1},{'sampling':21}])
def test_point_cloud_typed_request(patch):
    with pytest.raises(ValidationError):PointCloudExport(**{**dict(surface=1,path='a.pcd'),**patch})


def fixture_backend(tmp_path,*,code=0,write=True,close=True,available=True,raises=False,actual=None,grid=None):
    events=[]
    def run(surface,path,nx,ny,normals,fmt):
        events.append(('export',surface,nx,ny,normals,fmt))
        if raises:raise RuntimeError('native point cloud exception')
        if write:
            fields='x y z normal_x normal_y normal_z' if normals else 'x y z'
            data=actual or {'ASCII':'ascii','Binary':'binary','CompressedBinary':'binary_compressed'}[fmt]
            width,height=grid or (nx,ny)
            Path(path).write_bytes(f'# .PCD v0.7\nVERSION .7\nFIELDS {fields}\nWIDTH {width}\nHEIGHT {height}\nPOINTS {width*height}\nDATA {data}\n'.encode()+b'0 0 0\n1 0 0\n')
        return N(ErrorCode=code,Text='fixture native message')
    def release(value):events.append(('close',value));return close
    copy=N(LDE=N(RunTool_ExportPointCloudFile=run),Close=release)
    system=N(Mode='Sequential',LDE=N(NumberOfSurfaces=4,CanExportPointCloud=lambda s:available),CopySystem=lambda:copy,
             SystemData=N(Units=N(LensUnits='Millimeters')))
    b=Backend(Config(Path('unused'),tmp_path));b.native=N(system=system,api=N(Editors=N(LDE=N(PointCloudFileFormat='enum'))),enum=lambda t,v:v)
    b._require_work=lambda:None
    return b,events


@pytest.mark.parametrize('fmt',['ASCII','Binary','CompressedBinary'])
@pytest.mark.parametrize('normals',[True,False])
def test_point_cloud_native_method_on_owned_copy(tmp_path,fmt,normals):
    b,events=fixture_backend(tmp_path)
    r=export(b,PointCloudExport(surface=1,path=str(tmp_path/'a.pcd'),format=fmt,include_surface_normals=normals))
    assert r['copy_closed'] and r['system_tool_count']==0
    assert r['header']['points']==441 and r['model_revision']==0
    assert events==[('export',1,21,21,normals,fmt),('close',False)]


@pytest.mark.parametrize('options,expected',[
    ({'code':2},'POINT_CLOUD_EXPORT_FAILED'),({'write':False},'NO_RESULT_DATA'),
    ({'close':False},'CLEANUP_FAILED'),({'actual':'binary'},'SETTING_REJECTED'),({'grid':(2,3)},'SETTING_REJECTED')])
def test_point_cloud_failures_release_copy(tmp_path,options,expected):
    b,events=fixture_backend(tmp_path,**options)
    with pytest.raises(ZemaxError) as caught:export(b,PointCloudExport(surface=1,path=str(tmp_path/'a.pcd')))
    assert caught.value.code==expected and events[-1]==('close',False)
    if options.get('close') is False:assert b.requires_reconnect


def test_point_cloud_original_failure_and_close_failure(tmp_path):
    b,events=fixture_backend(tmp_path,raises=True,close=False)
    with pytest.raises(ZemaxError) as caught:export(b,PointCloudExport(surface=1,path=str(tmp_path/'a.pcd')))
    assert caught.value.code=='POINT_CLOUD_EXPORT_FAILED'
    assert 'native point cloud exception' in str(caught.value)
    assert 'cleanup_error' in caught.value.details and b.requires_reconnect


def test_point_cloud_unavailable_preflight(tmp_path):
    b,events=fixture_backend(tmp_path,available=False)
    with pytest.raises(ZemaxError) as caught:export(b,PointCloudExport(surface=1,path=str(tmp_path/'a.pcd')))
    assert caught.value.code=='POINT_CLOUD_UNAVAILABLE' and not events


@pytest.mark.parametrize('text',['','DATA binary\n','FIELDS x y z\nWIDTH 2\nHEIGHT 1\nPOINTS 1\nDATA ascii\n',
    'FIELDS x y z\nWIDTH 2\nWIDTH 3\nDATA ascii\n'])
def test_point_cloud_invalid_header(tmp_path,text):
    p=tmp_path/'a.pcd';p.write_text(text,encoding='ascii')
    with pytest.raises(ZemaxError,match='PCD'):read_header(p)


