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
    ('导出三维光路布局图', ['tool:run_layout_export','analysis:system_drawing']),
    ('分析加工误差引起的成像合格率', ['tool:run_tolerance_analysis','analysis:design_desensitize']),
    ('把镜片中心厚度改成五毫米', ['tool:update_surfaces']),
    ('这个镜头看东西有多清楚', ['tool:run_fft_mtf','analysis:spot']),
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
