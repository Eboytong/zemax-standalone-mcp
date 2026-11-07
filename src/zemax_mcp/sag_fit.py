"""Recover the sphere actually represented by native removed-sag data."""
import math
from .errors import ZemaxError

def infer_removed_sphere(samples,atol=1e-8,rtol=1e-6):
    """samples are (radial coordinate, raw sag, removed sag), including vertex.

    The returned data piston describes the numerical samples. Native SSAG can
    omit a manufacturing BFS vertex offset; that physical offset is separate.
    """
    rows=[tuple(map(float,row))for row in samples]
    if len(rows)<3 or any(len(row)!=3 or not all(math.isfinite(v)for v in row)for row in rows):
        raise ZemaxError('INVALID_RESULT_DATA','球面识别要求至少三个有限径向数据点。')
    vertex=next((row for row in rows if row[0]==0),None)
    other=next((row for row in rows if row[0]!=0),None)
    if vertex is None or other is None:raise ZemaxError('INVALID_RESULT_DATA','球面识别需要顶点和非零径向数据。')
    piston=vertex[1]-vertex[2];r=other[0];z=other[1]-other[2]-piston
    curvature=2*z/(r*r+z*z)
    residuals=[]
    for r,raw,removed in rows:
        discriminant=1-(curvature*r)**2
        if discriminant<0:raise ZemaxError('INVALID_RESULT_DATA','球面识别超出实数球面范围。',curvature=curvature,radius_coordinate=r)
        expected=piston+curvature*r*r/(1+math.sqrt(discriminant));actual=raw-removed
        error=abs(actual-expected);residuals.append(error)
        if error>atol+rtol*abs(expected):raise ZemaxError('INVALID_RESULT_DATA','原生移除结果不符合单一球面。',r=r,error=error,tolerance=atol+rtol*abs(expected))
    return dict(curvature=curvature,radius=1/curvature if curvature else None,data_piston=piston,
                maximum_residual=max(residuals),sample_count=len(rows),piston_definition='additive constant in supplied removed-sag data')

def slope_sphere_curvature(radius_coordinate,raw_slope,removed_slope):
    r=float(radius_coordinate);slope=float(raw_slope)-float(removed_slope)
    if not r or not all(math.isfinite(x)for x in [r,slope]):raise ZemaxError('INVALID_RESULT_DATA','球面斜率识别要求有限非零径向坐标。')
    return slope/(r*math.sqrt(1+slope*slope))
