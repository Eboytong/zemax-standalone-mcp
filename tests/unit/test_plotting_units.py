from types import SimpleNamespace as NS
import pytest
from zemax_mcp.plotting import export_image


@pytest.mark.parametrize('kind',['series','grid'])
def test_unknown_units_render_without_relabeling_result(tmp_path,monkeypatch,kind):
    from matplotlib.axes import Axes
    labels=[];original=Axes.set_xlabel
    def xlabel(self,text,*args,**kwargs):labels.append(text);return original(self,text,*args,**kwargs)
    monkeypatch.setattr(Axes,'set_xlabel',xlabel)
    data=dict(x_label='parameter',x_unit=None,y_unit=None,value_unit=None,value_label='PMVA')
    if kind=='series':data.update(series=0,x=[1,2],y=[[1],[2]],labels=['PMVA'])
    else:data.update(nx=2,ny=2,min_x=1,min_y=1,dx=1,dy=1,values=[[1,2],[1,2]])
    result=export_image({kind if kind=='series'else'grids':[data]},NS(source='data_plot',item=0,width=400,height=300),tmp_path/(kind+'.png'))
    assert 'parameter (单位见结果)'in labels
    assert data['x_unit']is None and result['image_source']=='data_plot'


def test_equal_axis_diagram_scale_and_surface_annotations(tmp_path,monkeypatch):
    from matplotlib.axes import Axes
    calls=[];original=Axes.annotate
    def annotate(self,text,*args,**kwargs):calls.append(text);return original(self,text,*args,**kwargs)
    monkeypatch.setattr(Axes,'annotate',annotate)
    s=dict(description='Y-Ybar',labels=['Y'],x=[-2,3],y=[[5],[0]],x_label='Y-bar',x_unit='Millimeters',
        y_label='Y',y_unit='Millimeters',point_labels=['1','2'],axis_limits=[-10,10],aspect='equal')
    r=export_image(dict(series=[s]),NS(source='data_plot',item=0,width=400,height=400),tmp_path/'yybar.png')
    assert r['plotting_settings']['axis_limits']==[-10,10] and r['plotting_settings']['aspect']=='equal'
    assert calls==['1','2']


def test_material_display_range_is_applied_to_y_axis(tmp_path):
    s=dict(labels=['glass'],x=[.4,.8],y=[[1.6],[1.5]],x_unit='micrometers',y_limits=[1.4,1.7])
    r=export_image(dict(series=[s]),NS(source='data_plot',item=0,width=400,height=300),tmp_path/'material.png')
    assert r['plotting_settings']['y_limits']==[1.4,1.7]


def test_seidel_coefficients_render_as_grouped_bars(tmp_path,monkeypatch):
    from matplotlib.axes import Axes
    calls=[];original=Axes.bar
    def bar(self,x,height,*args,**kwargs):calls.append(list(height));return original(self,x,height,*args,**kwargs)
    monkeypatch.setattr(Axes,'bar',bar)
    s=dict(plot_kind='bar',labels=['SPHA','COMA'],x=[0,1],y=[[.1,-.2],[.3,.4]],tick_labels=['2','Sum'],
        x_unit='index',y_unit='Millimeters',suppress_frame=True,y_limits=[-.5,.5])
    r=export_image(dict(series=[s]),NS(source='data_plot',item=0,width=600,height=400),tmp_path/'seidel.png')
    assert calls==[[.1,.3],[-.2,.4]]
    assert r['plotting_settings']['plot_kind']=='bar' and r['plotting_settings']['suppress_frame']
