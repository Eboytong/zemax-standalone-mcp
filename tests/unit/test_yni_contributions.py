import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.basic_analyses import parse_directivity_plot, parse_polarization_transmission_fan, parse_source_spectrum, parse_yni_contributions
from zemax_mcp.errors import ZemaxError
from types import SimpleNamespace
from zemax_mcp.basic_analyses import yni_operands


def operand_backend(value=1.25, surface_count=3):
    calls=[]
    def operand(*args):
        calls.append(args)
        return value
    def composite(kind, settings, flow):
        task=dict(context=dict(lens_units='Millimeters',configuration=1),rows=[])
        list(flow(task))
        return task
    return SimpleNamespace(
        system=SimpleNamespace(SystemData=SimpleNamespace(Wavelengths=SimpleNamespace(
            NumberOfWavelengths=2,GetWavelength=lambda n:SimpleNamespace(Wavelength=.55))),
            LDE=SimpleNamespace(NumberOfSurfaces=surface_count),MFE=SimpleNamespace(GetOperandValue=operand)),
        native=SimpleNamespace(api=SimpleNamespace(Editors=SimpleNamespace(MFE=SimpleNamespace(MeritOperandType=object()))),
                               enum=lambda _,name:name),
        _require_sequential=lambda:None,_composite=composite,_cancel_boundary=lambda _:None,calls=calls)


def test_yni_operand_preserves_explicit_arguments_and_result_units():
    backend=operand_backend()
    q=RunAnalysis(request=dict(kind='yni_contributions',wavelength=2)).request
    task=yni_operands(backend,q)
    assert backend.calls==[('YNIP',1,2,0.,0.,0.,0.,0.,0.)]
    assert task['rows'][0]['unit']=='Millimeters'
    assert task['payload']['actual_settings']['wavelength']==2
    assert task['payload']['series'][0]['y']==[[1.25]]


@pytest.mark.parametrize('value,surfaces',[(float('nan'),3),(float('inf'),3),(1.25,2)])
def test_yni_operand_rejects_invalid_or_empty_results(value,surfaces):
    q=RunAnalysis(request=dict(kind='yni_contributions',wavelength=1)).request
    with pytest.raises(ZemaxError):
        yni_operands(operand_backend(value,surfaces),q)


def test_yni_operand_rejects_out_of_range_before_queries():
    backend=operand_backend()
    q=RunAnalysis(request=dict(kind='yni_contributions',wavelength=3)).request
    with pytest.raises(ZemaxError):
        yni_operands(backend,q)
    assert backend.calls==[]


def test_yni_operand_cancellation_boundary_precedes_native_query():
    from zemax_mcp.evaluation import Cancelled
    backend=operand_backend()
    def cancel(_):
        raise Cancelled()
    backend._cancel_boundary=cancel
    q=RunAnalysis(request=dict(kind='yni_contributions',wavelength=1)).request
    with pytest.raises(Cancelled):
        yni_operands(backend,q)
    assert backend.calls==[]


def test_yni_request_has_no_unverified_settings():
    request = RunAnalysis(request={"kind": "yni_contributions"})
    assert request.request.model_dump(exclude_none=True) == {"kind": "yni_contributions"}
    with pytest.raises(ValidationError):
        RunAnalysis(request={"kind": "yni_contributions", "wavelength": 0})
    assert RunAnalysis(request={"kind":"yni_contributions","wavelength":2}).request.wavelength == 2


def test_parse_native_yni_report_to_rows_and_series():
    text = """YNI Contributions
Units are mm.
Wavelength: 0.55000 um
Surf       YNI
   1       1.25
   2      -0.50
"""
    result = parse_yni_contributions(text, "Millimeters")
    assert result["wavelength_um"] == 0.55
    assert result["position_unit"] == "Millimeters"
    assert result["rows"] == [
        {"index": 0, "surface": 1, "value": 1.25, "unit": "Millimeters", "source_line": 5, "raw": "   1       1.25"},
        {"index": 1, "surface": 2, "value": -0.5, "unit": "Millimeters", "source_line": 6, "raw": "   2      -0.50"},
    ]
    assert result["series"][0]["x"] == [1, 2]
    assert result["series"][0]["y"] == [[1.25], [-0.5]]


@pytest.mark.parametrize("text", ["", "Surf YNI\n1 2\n", "Wavelength: 0.55 μm\nSurf YNI\n"])
def test_reject_incomplete_yni_report(text):
    with pytest.raises(ZemaxError, match="YNI报告缺少"):
        parse_yni_contributions(text, "Millimeters")


@pytest.mark.parametrize('table', [
    '1 1.0\n2 NaN\n3 2.0', '1 inf', '1 1e999',
    '1 1.0\n1 2.0', '2 1.0\n1 2.0', '1 bad',
])
def test_yni_rejects_corrupt_rows_instead_of_returning_partial_results(table):
    with pytest.raises(ZemaxError):
        parse_yni_contributions('Wavelength: 0.55 um\nSurf YNI\n'+table, 'Millimeters')


@pytest.mark.parametrize('wave', ['0', '-0.5', '1e999'])
def test_yni_rejects_nonpositive_or_overflow_wavelength(wave):
    with pytest.raises(ZemaxError):
        parse_yni_contributions(f'Wavelength: {wave} um\n1 1.0', 'Millimeters')


def test_yni_accepts_native_micro_sign_and_zero_contribution():
    result = parse_yni_contributions('Wavelength: 0.55 µm\n1 0', 'Millimeters')
    assert result['wavelength_um'] == .55
    assert result['rows'][0]['value'] == 0


def test_parse_source_spectrum_report_and_normalized_weights():
    text = """光源光谱列表
波长值为微米级
输入: X = 1.0000, Y = 1.0000, Z = 1.0000
拟合 : X = 1.0000, Y = 1.0000, Z = 1.0000
CRI = 70.1766 (CCT = 5188 K)
波长  权重
0.440000 0.5
0.450526 1.00000000
"""
    result = parse_source_spectrum(text)
    assert result["input_xyz"] == [1, 1, 1]
    assert result["fitted_xyz"] == [1, 1, 1]
    assert result["cri"] == pytest.approx(70.1766)
    assert result["cct_kelvin"] == pytest.approx(5188)
    assert result["series"][0]["x"] == [0.44, 0.450526]
    assert result["series"][0]["y"] == [[0.5], [1.0]]


def test_reject_source_spectrum_without_colorimetric_summary():
    with pytest.raises(ZemaxError, match="缺少XYZ拟合"):
        parse_source_spectrum("0.44 0.5\n0.45 1.0\n")


def spectrum_text(rows, xyz='1.0'):
    return (f'输入: X = {xyz}, Y = 1.0, Z = 1.0\n拟合: X = 1.0, Y = 1.0, Z = 1.0\n'
            'CRI = 70.0 (CCT = 5100 K)\n波长 权重\n'+rows)


@pytest.mark.parametrize('rows', ['0.44 .5\n0.45 NaN\n0.46 1',
    '0.44 .5\n0.45 -0.1', '0.44 .5\n0.45 1e999',
    '0.44 .5\n0.45 1.1', '0.44 .5\n0 1', '0.44 .5\nbad row',
    '0.44 .5\n0.45 1 2'])
def test_spectrum_rejects_corrupt_rows_instead_of_partial_curve(rows):
    with pytest.raises(ZemaxError):
        parse_source_spectrum(spectrum_text(rows))


def test_spectrum_rejects_overflow_metadata_and_retains_input_identity():
    with pytest.raises(ZemaxError):
        parse_source_spectrum(spectrum_text('0.44 .5\n0.45 1',xyz='1e999'))
    result=parse_source_spectrum(spectrum_text('4.4e-1 5e-1\n4.5e-1 1',xyz='1e-1'))
    assert result['input_xyz'][0]==.1
    assert result['input_definition']=='native XYZ tristimulus fitting input'
    assert result['source_object_binding']=='not exposed by installed analysis settings'


def test_parse_directivity_curve_and_photometric_metadata():
    text = """IESNA 光源文件: sample.ies
峰值强度: 1.8000E+01 坎德拉
文件中的总光通量: 1.1281E+02 流明
扫描角度: 0.00 度
角度 归一化坎德拉
-180.00 0.000E+00
-90.00 5.000E-01
0.00 1.000E+00
90.00 5.000E-01
180.00 0.000E+00
"""
    result = parse_directivity_plot(text)
    assert result["ies_file"] == "sample.ies"
    assert result["peak_intensity_candela"] == pytest.approx(18)
    assert result["total_luminous_flux_lumens"] == pytest.approx(112.81)
    assert result["series"][0]["x"] == [-180, -90, 0, 90, 180]
    assert result["series"][0]["y"] == [[0], [0.5], [1], [0.5], [0]]


def test_parse_polarization_transmission_fan_rows_and_curves():
    text = """单位是归一化强度。
场是非偏振的。
子午光扇，视场号1 = 0.00 (度)
  光瞳       0.4800       0.5500       0.6500
 -1.000       0.9483       0.9606       0.9404
  0.000       0.9440       0.9607       0.9436
  1.000       0.9483       0.9606       0.9404
弧矢光扇，视场号1 = 0.00 (度)
  光瞳       0.4800       0.5500       0.6500
 -1.000       0.9500       0.9600       0.9410
  1.000       0.9500       0.9600       0.9410
"""
    result = parse_polarization_transmission_fan(text)
    assert len(result["rows"]) == 5
    assert len(result["series"]) == 6
    first = result["series"][0]
    assert first["fan"] == "tangential"
    assert first["wavelength_um"] == pytest.approx(0.48)
    assert first["x"] == [-1, 0, 1]
    assert first["y"] == [[0.9483], [0.944], [0.9483]]
    assert result["series"][-1]["fan"] == "sagittal"


@pytest.mark.parametrize('rows', ['-90 .5\n0 NaN\n90 .5', '-90 .5\n0 -1',
    '-90 .5\n0 1e999', '-90 .5\n0 bad', '-90 .5\n0 1 2',
    '-90 .5\n-90 1', '-90 .5\nbad row'])
def test_directivity_rejects_corrupt_curve_instead_of_partial_results(rows):
    text='IESNA 光源文件: sample.ies\n峰值强度: 18 坎德拉\n文件中的总光通量: 112.81 流明\n扫描角度: 0 度\n角度 归一化坎德拉\n'+rows
    with pytest.raises(ZemaxError):
        parse_directivity_plot(text)


@pytest.mark.parametrize('peak,flux',[('1e999','10'),('-1','10'),('18','-1'),('18','1e999')])
def test_directivity_rejects_invalid_photometry(peak,flux):
    with pytest.raises(ZemaxError):
        parse_directivity_plot(f'IESNA 光源文件: sample.ies\n峰值强度: {peak} 坎德拉\n文件中的总光通量: {flux} 流明\n扫描角度: 0 度\n-90 .5\n90 .5')
