from zemax_mcp.imaging import geometric_grid_coordinates


def test_non_square_top_down_pixel_centers():
    values=[[1,2,3],[4,5,6]]
    original=dict(min_x=-3,min_y=2,dx=2,dy=2)
    array,axes=geometric_grid_coordinates(values,original,3,2)
    assert array==[[4,5,6],[1,2,3]]
    assert axes['min_x']==-2 and axes['min_y']==-1
    assert axes['dy']==2 and axes['native_axes']==original
    assert values==[[1,2,3],[4,5,6]]
