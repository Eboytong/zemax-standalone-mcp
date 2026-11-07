from zemax_mcp.surface_mtf import describe_surface_mtf
import pytest
from zemax_mcp.errors import ZemaxError


def test_huygens_dc_origin_and_native_axes():
    g=dict(nx=128,ny=128,min_x=-256,min_y=-256,dx=2,dy=2,value_label='native',values=[[0]*128 for _ in range(128)])
    r=describe_surface_mtf(dict(grids=[g]),dict(kind='huygens_surface_mtf',mtf_type='MTF_Incoherent'),'CyclesPerMillimeter')
    assert g['min_x']==-128 and g['min_y']==-128
    assert g['native_axes']['min_x']==-256
    assert g['min_x']+g['zero_frequency_index']['x']*g['dx']==0
    assert r['frequency_unit']=='CyclesPerMillimeter'


def test_fft_preserves_zero_frequency_origin():
    g=dict(nx=256,ny=256,min_x=-254,min_y=-254,dx=2,dy=2,value_label='native',values=[[0]*256 for _ in range(256)])
    describe_surface_mtf(dict(grids=[g]),dict(kind='fft_surface_mtf',mtf_type='Real_Incoherent',rotation='Rotate_90',scale_factor=2),'CyclesPerMillimeter')
    assert g['zero_frequency_index']==dict(x=127,y=127)
    assert g['min_x']==-254 and g['native_value_label']=='native'


def test_surface_mtf_missing_grid():
    with pytest.raises(ZemaxError)as e:describe_surface_mtf(dict(grids=[]),dict(kind='fft_surface_mtf'),'CyclesPerMillimeter')
    assert e.value.code=='NO_RESULT_DATA'


@pytest.mark.parametrize('labels',[(None,None),('None','None'),('native X','native Y')])
def test_surface_mtf_frequency_labels_preserve_native_metadata(labels):
    g=dict(nx=3,ny=5,min_x=-1,min_y=-2,dx=1,dy=1,value_label='native',
           x_label=labels[0],y_label=labels[1],values=[[0]*3 for _ in range(5)])
    describe_surface_mtf(dict(grids=[g]),dict(kind='huygens_surface_mtf',mtf_type='MTF_Incoherent'),'CyclesPerMillimeter')
    assert g['x_label']=='Spatial frequency X' and g['y_label']=='Spatial frequency Y'
    assert g['native_axis_labels']==dict(x_label=labels[0],y_label=labels[1])
