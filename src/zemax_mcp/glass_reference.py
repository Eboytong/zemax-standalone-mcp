"""Centered paraxial matrix reference for native-index glass contributions."""
import math

from .errors import ZemaxError


def multiply(a,b):
    return [a[0]*b[0]+a[1]*b[2],a[0]*b[1]+a[1]*b[3],
            a[2]*b[0]+a[3]*b[2],a[2]*b[1]+a[3]*b[3]]


def paraxial(rows,indices,stop,angle_deg):
    """Canonical vector (height, n*slope); object at infinity in air."""
    matrix=[1,0,0,1];to_stop=None;petzval=0
    for i,row in enumerate(rows,1):
        if i==stop:to_stop=matrix[:]
        n0,n1=indices[i-1],indices[i]
        curvature=row['curvature']
        power=(n1-n0)*curvature
        petzval-=power/(n0*n1)
        matrix=multiply([1,0,-power,1],matrix)
        if i<len(rows):matrix=multiply([1,row['thickness']/n1,0,1],matrix)
    if to_stop is None or abs(to_stop[0])<1e-15 or abs(matrix[2])<1e-15:
        raise ZemaxError('DEGENERATE_PARAXIAL_MODEL','近轴模型缺少有限焦点或光阑共轭。')
    image= multiply([1,rows[-1]['thickness']/indices[-1],0,1],matrix)
    slope=math.tan(math.radians(angle_deg))*indices[0]
    front_height=-to_stop[1]/to_stop[0]*slope
    return dict(effective_focal_length=-indices[-1]/matrix[2],
        back_focal_distance=-indices[-1]*matrix[0]/matrix[2],
        chief_image_height=image[0]*front_height+image[1]*slope,
        petzval_curvature=petzval,matrix=matrix,stop_matrix=to_stop)


def glass_contributions(rows,indices_by_wave,groups,stop,angle_deg):
    """First-order C-F dispersion sensitivities at the specified middle wavelength."""
    blue,reference,red=indices_by_wave
    base=paraxial(rows,reference,stop,angle_deg)
    h=1e-20;contributions=[]
    for group in groups:
        first,last=group['first_surface'],group['last_surface']
        perturbed=[complex(v) for v in reference]
        delta=red[first]-blue[first]
        if any(abs((red[i]-blue[i])-delta)>1e-12 or abs(reference[i]-reference[first])>1e-12 for i in range(first,last)):
            raise ZemaxError('INVALID_GLASS_GROUP','镜片内部各段需属于相同材料。',group=group)
        for i in range(first,last):perturbed[i]+=1j*h
        derivative=paraxial(rows,perturbed,stop,angle_deg)
        axial=derivative['back_focal_distance'].imag/h
        lateral=derivative['chief_image_height'].imag/h
        contributions.append(dict(**group,index=reference[first],delta_index_red_minus_blue=delta,
            axial_color=delta*axial,lateral_color=delta*lateral,
            axial_sensitivity=axial,lateral_sensitivity=lateral,
            petzval_curvature=-(1-1/reference[first])*(rows[first-1]['curvature']-rows[last-1]['curvature']),
            petzval_scope='material contribution -(1-1/n)*(entrance curvature-exit curvature), air index 1; cemented interface telescopes across adjacent materials'))
    exact_blue=paraxial(rows,blue,stop,angle_deg);exact_red=paraxial(rows,red,stop,angle_deg)
    return dict(reference=base,groups=contributions,
        exact_paraxial_axial_color=exact_red['back_focal_distance']-exact_blue['back_focal_distance'],
        exact_paraxial_lateral_color=exact_red['chief_image_height']-exact_blue['chief_image_height'],
        first_order_axial_sum=sum(c['axial_color'] for c in contributions),
        first_order_lateral_sum=sum(c['lateral_color'] for c in contributions),
        definition='complex-step derivative of canonical paraxial matrix at reference index times red-blue index dispersion; actual finite color evaluated separately',
        units=dict(axial_color='lens units',lateral_color='lens units',petzval_curvature='inverse lens units',index='dimensionless'))
