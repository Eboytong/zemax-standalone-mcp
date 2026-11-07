import json
import pytest
from support.saved_imaging import validate_folder,fft_frequency_projection


def fixture(folder):
    for n in (256,512):
        for kind in ('fft_psf','huygens_psf','fft_mtf','huygens_mtf','diffraction_encircled_energy'):
            q=dict(field=1,wavelength=1,sampling=f'S_{n}x{n}')
            data=dict(task=dict(state='succeeded',kind='analysis',settings=dict(kind=kind,requested=q,native=dict(UseHuygensPSF=False))))
            if kind.endswith('psf'):
                values=[[0.]*4 for _ in range(4)];values[2][2]=1
                data['grids']=[dict(nx=4,ny=4,min_x=-1,min_y=-1,dx=.5,dy=.5,values=values)]
            else:
                data['series']=[dict(description='actual field',labels=['Tangential','Sagittal']if kind.endswith('mtf')else['energy'],
                    x=[0,10,20,25,40,50],y=[[1,1]if kind.endswith('mtf')else[1]for _ in range(6)])]
                if kind=='diffraction_encircled_energy':
                    data['series'].insert(0,dict(description='衍射极限',labels=['energy'],x=[0,50],y=[[.3],[.3]]))
            (folder/f'{kind}_{n}.json').write_text(json.dumps(data),encoding='utf-8')


def test_method_matched_saved_cross_ignores_diffraction_limit(tmp_path):
    fixture(tmp_path)
    result=validate_folder(tmp_path)
    assert result['status']=='numeric_pass'
    assert result['missing']==[]
    assert any(c['check']=='FFT PSF disk energy'for c in result['checks'])


def test_saved_cross_rejects_mixed_selection(tmp_path):
    fixture(tmp_path)
    path=tmp_path/'fft_mtf_256.json';data=json.loads(path.read_text());data['task']['settings']['requested']['field']=2
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='different fields'):validate_folder(tmp_path)


def test_partial_task_does_not_pass_saved_cross(tmp_path):
    fixture(tmp_path)
    path=tmp_path/'huygens_psf_512.json';data=json.loads(path.read_text());data['task']['state']='failed'
    path.write_text(json.dumps(data))
    assert validate_folder(tmp_path)['status']=='incomplete'


def test_refinement_can_reuse_saved_baseline_without_copying_results(tmp_path):
    base=tmp_path/'base';extra=tmp_path/'extra';base.mkdir();extra.mkdir()
    fixture(base)
    path=base/'huygens_psf_512.json'
    path.rename(extra/path.name)
    assert validate_folder(base)['status']=='incomplete'
    result=validate_folder(base,additional_folders=(extra,))
    assert result['status']=='numeric_pass'
    assert any(str(extra)in p for p in result['sources'])


def test_cropped_output_cannot_pass_pupil_refinement(tmp_path):
    fixture(tmp_path)
    path=tmp_path/'fft_psf_512.json';data=json.loads(path.read_text())
    data['grids'][0]['dx']=.25;data['grids'][0]['dy']=.25
    path.write_text(json.dumps(data),encoding='utf-8')
    result=validate_folder(tmp_path)
    assert result['status']=='incomplete'
    assert any('window differs'in r.get('reason','')for r in result['missing'])


def test_fft_frequency_uses_geometric_projection_and_primary_wave():
    chief=dict(field=3,wavelength=0,result=dict(rows=[dict(input=dict(wavelength=1),
        error_code=0,vignette_code=0,direction=[0,.6,.8],surface_normal=[0,0,-1])],
        system_settings=dict(wavelengths=[dict(number=1,primary=True),dict(number=2,primary=False)])))
    result=fft_frequency_projection(chief,3,0)
    assert result['tangential']==pytest.approx(1.25)and result['sagittal']==1
    chief['result']['rows'][0]['input']['wavelength']=2
    with pytest.raises(ValueError,match='actual selected/primary'):fft_frequency_projection(chief,3,0)


def test_fft_projection_does_not_apply_centered_y_rule_to_general_ray():
    chief=dict(field=2,wavelength=1,result=dict(rows=[dict(input=dict(wavelength=1),error_code=0,vignette_code=0,
        direction=[.6,0,.8],surface_normal=[0,0,-1])],system_settings=dict(wavelengths=[])))
    with pytest.raises(ValueError,match='centered Y-field'):fft_frequency_projection(chief,2,1)
