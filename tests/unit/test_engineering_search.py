"""Discovery relevance, composition and compact response budgets."""
import json
from pathlib import Path

import pytest

from zemax_mcp.capability_index import CapabilitySearch, search


def ids(result):
    return [item['capability_id'] for item in result['items']]


@pytest.mark.parametrize('query,expected', [
    ('检查镜头的波前像差', ['analysis:wavefront']),
    ('计算调制传递函数评价成像清晰度', ['tool:run_fft_mtf']),
    ('查询光学材料的折射率与色散', ['tool:get_material_properties']),
    ('求镀膜的反射透射和吸收', ['tool:get_coating_rta']),
    ('寻找最佳焦点使光斑最小', ['tool:run_quick_focus','analysis:rms_vs_focus']),
    ('导出三维光路布局图', ['tool:run_layout_export']),
    ('分析加工误差引起的成像合格率', ['tool:run_tolerance_analysis','analysis:design_desensitize']),
    ('把镜片中心厚度改成五毫米', ['tool:update_surfaces']),
    ('这个镜头看东西有多清楚', ['tool:run_fft_mtf','tool:run_spot_analysis']),
    ('追踪杂散光到光电接收面的能量分布', ['tool:run_nsc_ray_trace','tool:get_detector_data']),
    ('读取先前算过的结果', ['tool:get_historical_result','tool:list_task_history','tool:get_task_result']),
    ('计算高斯光束经过系统后的复振幅', ['tool:run_pop']),
])
def test_additional_engineering_requests(query, expected):
    assert set(ids(search(query))) & set(expected)


def test_compound_discovery_preserves_each_intent_and_deduplicates():
    result = search('读取波前再保存候选设计')
    assert {'analysis:wavefront', 'tool:manage_candidates'} <= set(ids(result))
    assert len(result['intents']) == 2
    assert result['intents'][0]['capability_ids'][0] == 'analysis:wavefront'
    assert len(ids(result)) == len(set(ids(result))) == 5
    assert len(result['retry_requests']) <= 2
    for request in result['retry_requests']:
        CapabilitySearch(**request)
        assert search(**request)['items']
    assert len(json.dumps(result,ensure_ascii=False).encode('utf-8')) <= 8000


@pytest.mark.parametrize('query,expected', [
    ('装配误差与成品率', 'tool:run_tolerance_analysis'),
    ('评估镜片的清晰程度', 'tool:run_fft_mtf'),
    ('读取感光面功率', 'tool:get_detector_data'),
    ('追踪杂散光', 'tool:run_nsc_ray_trace'),
])
def test_synonyms_report_expansion(query, expected):
    result = search(query)
    assert expected in ids(result)
    assert result['expanded_terms']


def test_exact_ids_outrank_generic_words_and_prefixes():
    for capability in ('analysis:wavefront', 'tool:run_fft_mtf', 'action:manage_candidates:list'):
        assert ids(search('计算分析镜头 ' + capability))[0] == capability
    assert ids(search('run_fft_mtf'))[0] == 'tool:run_fft_mtf'


@pytest.mark.parametrize('limit', [1, 2, 5, 50])
def test_compound_limits_and_category(limit):
    result = search('读取波前，然后分析成像质量，再评估加工误差',limit=limit,category='analysis')
    assert len(result['items']) <= limit
    assert all(item['category']=='analysis' for item in result['items'])
    assert len(ids(result)) == len(set(ids(result)))


@pytest.mark.parametrize('query', ['火星天气预报 xyzq','zzzzqqqqxxxx','订购午餐然后查询天气'])
def test_unrelated_queries_stay_empty(query):
    assert search(query)['items'] == []


@pytest.mark.parametrize('query', [
    '完成光学设计报告，提供镜头结构图、MTF曲线和点列图',
    '镜头结构图、MTF 曲线、标准点列图',
    'Create report figures with a lens layout, FFT MTF curve and a standard spot diagram',
])
def test_report_figures_lead_to_all_required_tools(query):
    result = search(query)
    required = {'tool:run_layout_export', 'tool:run_fft_mtf', 'tool:run_spot_analysis', 'tool:export_analysis_image'}
    assert required <= set(ids(result))
    for item in result['items']:
        if item['capability_id'] in required:
            assert item['call'] == 'execute_capability'
            assert item['example']['capability_id'] == item['capability_id']
            assert item['prerequisites'] and item['result']


def test_report_search_does_not_suggest_surface_removal():
    assert 'tool:delete_surfaces' not in ids(search('输出装调公差报告和像质图'))
    assert 'tool:delete_surfaces' in ids(search('删除曲面，然后输出报告'))


def test_overview_representatives_and_examples_resolve():
    from jsonschema import validate
    from zemax_mcp.capability_index import CONCEPTS, build_index, describe, EXAMPLES
    from zemax_mcp.models import Capabilities

    index = {item['capability_id']: item for item in build_index()}
    overview = describe(Capabilities(topic='overview'))
    assert sum(group['count'] for group in overview['groups']) == overview['total'] == len(index)
    for group in overview['groups']:
        assert set(group['capability_ids']) <= index.keys()
    for _, _, preferred in CONCEPTS:
        assert set(preferred) <= index.keys()
    for name, example in EXAMPLES.items():
        validate(example, index[f'tool:{name}']['request_schema'])
    for kind in ('relative_illumination', 'field_curvature_distortion'):
        assert describe(Capabilities(topic='detail', capability_id=f'analysis:{kind}'))['description']
