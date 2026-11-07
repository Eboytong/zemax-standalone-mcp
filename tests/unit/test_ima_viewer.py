import struct
import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.ima_viewer import parse_image
from zemax_mcp.errors import ZemaxError


@pytest.mark.parametrize('extra',[{'input_file':'../x.ima'},{'input_file':'x.png'},{'map_index':0},{'map_index':1.5},{'wavelength':1},{'method':'auto'}])
def test_viewer_contract(extra):
    with pytest.raises(ValidationError):RunAnalysis(request={'kind':'ima_bim_viewer','input_file':'x.IMA',**extra})


def test_text_orientation_and_normalization():
    image=parse_image(b'3\n090\n005\n100\n','.ima')
    assert image['values']==[[1,0,0],[0,0,5],[0,9,0]]
    assert image['normalized'][1][2]==5/9


def test_binary_plane_selection_retains_precision_and_orientation():
    image=parse_image(struct.pack('<hhh',0,2,3)+bytes([0,1,2,3,10,20,30,40,1,2,3,4]),'.IMA',2)
    assert image['maps']==3 and image['values']==[[30,40],[10,20]]
    assert image['normalized']==[[.75,1],[.25,.5]]


def test_bim_bottom_left_and_exact_double():
    raw=struct.pack('<ii4d',2,2,0,.123456789012345,1,2)
    image=parse_image(raw,'.bim')
    assert image['values']==[[0,.123456789012345],[1,2]]
    assert image['normalized'][0][1]==.123456789012345/2


@pytest.mark.parametrize('raw,suffix',[
    (b'', '.ima'),(b'2\n01\n2a\n','.ima'),(b'2\n01\n22\nextra','.ima'),
    (struct.pack('<hhh',0,2,3)+b'123','.ima'),(struct.pack('<ii',2,3)+bytes(48),'.bim'),
    (struct.pack('<ii4d',2,2,0,1,2,float('nan')),'.bim'),
    (struct.pack('<ii4d',2,2,0,1,2,-1),'.bim'),(struct.pack('<ii',8000,8000),'.bim'),
])
def test_malformed_before_native(raw,suffix):
    with pytest.raises(ZemaxError) as error:parse_image(raw,suffix)
    assert error.value.code=='INVALID_RESOURCE_DATA'


def test_zero_and_map_boundary():
    image=parse_image(b'2\n00\n00\n','.ima')
    assert image['peak']==0 and image['normalized']==[[0,0],[0,0]]
    with pytest.raises(ZemaxError) as error:parse_image(b'2\n00\n00\n','.ima',2)
    assert error.value.code=='INDEX_OUT_OF_RANGE'

def test_extracted_plane_cleanup_on_child_failure_or_cancellation(tmp_path):
    from types import SimpleNamespace
    from zemax_mcp.ima_viewer import run_viewer
    path=tmp_path/'four.IMA';path.write_bytes(struct.pack('<hhh',0,2,4)+bytes(range(16)))
    class Backend:
        native=SimpleNamespace(application=SimpleNamespace(ImagesDir=str(tmp_path)))
        def _require_work(self):pass
        def _require_sequential(self,**kwargs):pass
        def _cancel_boundary(self,task):pass
        def _composite(self,kind,settings,factory,**kwargs):
            self.task={'context':{'configuration':1},'rows':[]}
            return factory(self.task)
        def _child_job(self,*args):
            assert len(list(tmp_path.glob('mcp_viewer_*.BIM')))==1
            yield
            raise ZemaxError('CHILD_TASK_FAILED','controlled failure')
    for cancelled in (False,True):
        b=Backend();iterator=run_viewer(b,RunAnalysis(request=dict(kind='ima_bim_viewer',input_file='four.IMA',map_index=4)).request)
        next(iterator)
        if cancelled:iterator.close()
        else:
            with pytest.raises(ZemaxError,match='controlled failure'):next(iterator)
        assert not list(tmp_path.glob('mcp_viewer_*.BIM'))
        assert b.task['payload']['temporary_input_removed']
