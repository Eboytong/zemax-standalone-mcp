"""A report requested with charts must retain scatter analysis images."""
from pathlib import Path
from zemax_mcp.reports import export_saved_report


def test_scatter_chart_is_in_report_artifacts_and_markdown(tmp_path):
    scatter=dict(description='Pupil intensity',x_label='Pupil X',y_label='Pupil Y',points=[dict(x=-1,y=0,value=.8),dict(x=0,y=0,value=1),dict(x=1,y=0,value=.8)])
    result=export_saved_report(tmp_path,[dict(task_id='pupil',result=dict(scatter=[scatter]))],'Pupil',True,['markdown'])
    plot=next(a for a in result['artifacts']if a['kind']=='plot')
    assert Path(plot['path']).is_file()
    assert '!['in(tmp_path/'report.md').read_text(encoding='utf-8')
    assert Path(plot['path']).name in(tmp_path/'report.md').read_text(encoding='utf-8')
