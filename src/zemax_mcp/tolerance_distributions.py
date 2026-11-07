"""Native tolerance histogram counters, including values outside the plotted bins."""
import re
from .errors import ZemaxError


def describe_distribution(data,kind,text):
    def count(label):
        m=re.search(r'^'+label+r'\s*[:：]\s*(\d+)\s*$',text,re.MULTILINE)
        return int(m[1])if m else None
    summary=dict(source='native ZTD stored values',sample_count=count('样本尺寸'),
                 interpretation='native stored-value distribution; failed trial status must be obtained from tolerance trial results',
                 failure_handling='native stored values retained, including finite failed-criterion sentinels; no trial-status filtering')
    if kind=='tolerance_histogram':
        summary.update(underflow=count('下溢计数'),overflow=count('溢出计数'))
        if any(summary[k]is None for k in ['sample_count','underflow','overflow']):
            raise ZemaxError('INVALID_RESULT_DATA','原生直方图计数格式无法识别。',native_text=text)
        summary['in_range_count']=sum(row[0]for s in data['series']for row in s['y'])
        if summary['in_range_count']+summary['underflow']+summary['overflow']!=summary['sample_count']:
            raise ZemaxError('INVALID_RESULT_DATA','原生直方图分段计数与样本数不符。',counts=summary)
    data['distribution']=summary
    for s in data['series']:
        s['y_unit']='count'if kind=='tolerance_histogram'else'percent'
        s['x_unit']='native selected ZTD column unit; see original report'
    return data
