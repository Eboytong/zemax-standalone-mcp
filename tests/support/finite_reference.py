"""Independent references for the finite optical acceptance models.

No ZOS-API calls or production result adapters are used here.
"""
import math
from pathlib import Path


def glass_coefficients(name="N-BK7"):
    path = Path.home() / "Documents/Zemax/Glasscat/SCHOTT.AGF"
    selected = False
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if line.startswith("NM "):
            selected = line.split()[1] == name
        if selected and line.startswith("CD "):
            return tuple(map(float, line.split()[1:7]))
    raise ValueError(f"Material coefficients unavailable: {name}: {path}")


def sellmeier(wavelength_um, coefficients):
    w2 = wavelength_um ** 2
    return math.sqrt(1 + sum(coefficients[i] * w2 / (w2 - coefficients[i + 1])
                             for i in (0, 2, 4)))


def unit(vector):
    length = math.sqrt(sum(v*v for v in vector))
    if not math.isfinite(length) or length == 0:
        raise ValueError("A finite nonzero vector is required")
    return tuple(v / length for v in vector)


def snell(direction, normal, n1, n2):
    d, normal = unit(direction), unit(normal)
    dot = sum(a*b for a, b in zip(d, normal))
    if dot > 0:
        normal = tuple(-x for x in normal)
        dot = -dot
    eta = n1 / n2
    discriminant = 1 - eta*eta*(1-dot*dot)
    if discriminant < 0:
        raise ValueError("Total internal reflection")
    return unit(tuple(eta*a - (eta*dot + math.sqrt(discriminant))*b
                      for a, b in zip(d, normal)))


def sphere_intersection(origin, direction, vertex_z, radius):
    d = unit(direction)
    center = (0., 0., vertex_z + radius)
    q = tuple(a-b for a, b in zip(origin, center))
    b = sum(a*v for a, v in zip(q, d))
    c = sum(v*v for v in q) - radius*radius
    discriminant = b*b-c
    if discriminant < 0:
        raise ValueError("Sphere missed")
    roots = [v for v in (-b-math.sqrt(discriminant), -b+math.sqrt(discriminant)) if v >= 0]
    if not roots:
        raise ValueError("Sphere behind ray")
    distance = min(roots)
    p = tuple(a+distance*v for a, v in zip(origin, d))
    return p, unit(tuple(a-b for a, b in zip(p, center)))


def singlet_ray(x, y, angle_deg, index):
    """Dummy at z=0; R=50 vertex z=1, planar back z=6, all in mm."""
    angle = math.radians(angle_deg)
    d0 = (math.sin(angle), 0., math.cos(angle))
    front, normal = sphere_intersection((x, y, 0.), d0, 1., 50.)
    inside = snell(d0, normal, 1., index)
    t = (6-front[2])/inside[2]
    back = tuple(a+t*b for a, b in zip(front, inside))
    outside = snell(inside, (0., 0., -1.), index, 1.)
    return dict(front=front, inside=inside, back=back, outside=outside)


def normalized_otf(psf, dx_mm, dy_mm):
    import numpy as np
    values = np.asarray(psf, dtype=float)
    if not np.isfinite(values).all() or values.sum() <= 0:
        raise ValueError("Finite positive-energy PSF required")
    otf = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(values))) / values.sum()
    return (np.fft.fftshift(np.fft.fftfreq(values.shape[1], dx_mm)),
            np.fft.fftshift(np.fft.fftfreq(values.shape[0], dy_mm)), otf)


def polychromatic_otf(otfs, powers):
    """Combine complex OTFs, never the magnitudes of the OTFs."""
    import numpy as np
    weights = np.asarray(powers, dtype=float)
    if (weights < 0).any() or not np.isfinite(weights).all() or weights.sum() <= 0:
        raise ValueError("Nonnegative powers with positive sum required")
    return sum(w*np.asarray(v) for w, v in zip(weights, otfs, strict=True))/weights.sum()


def radial_grin_ray(x, y, length, n0, radial_quadratic, steps=1024):
    """Integrate d(n dr/ds)/ds=grad(n), using z as independent variable.

    State is x,y,p_x,p_y. Flat normal incidence gives initial transverse
    optical momentum zero. The final planar exit is into air.
    """
    def derivative(state):
        x,y,px,py=state
        n=n0+radial_quadratic*(x*x+y*y)
        pz=math.sqrt(n*n-px*px-py*py)
        return (px/pz,py/pz,n*2*radial_quadratic*x/pz,n*2*radial_quadratic*y/pz)
    state=(x,y,0.,0.);h=length/steps
    for _ in range(steps):
        k1=derivative(state)
        k2=derivative(tuple(a+h*b/2 for a,b in zip(state,k1)))
        k3=derivative(tuple(a+h*b/2 for a,b in zip(state,k2)))
        k4=derivative(tuple(a+h*b for a,b in zip(state,k3)))
        state=tuple(a+h*(b+2*c+2*d+e)/6 for a,b,c,d,e in zip(state,k1,k2,k3,k4))
    x,y,px,py=state
    if px*px+py*py>=1:raise ValueError('Total internal reflection at exit')
    return (x,y,0.),(px,py,math.sqrt(1-px*px-py*py))


def phasor_power_moments(mu,mu2,n):
    m=abs(mu)**2
    second=1/n+(1-1/n)*m
    fourth=(n*(2*n-1)+n*(n-1)*abs(mu2)**2+4*n*(n-1)**2*m
            +2*n*(n-1)*(n-2)*(mu2*mu.conjugate()**2).real
            +n*(n-1)*(n-2)*(n-3)*m*m)/n**4
    return second,max(0.,fourth-second*second)


def thermal_edge_gap(length,front_radius,rear_radius,mechanical_radius,mount_cte,glass_cte,delta_temperature):
    from .surface_reference import conic_sag
    mount=1+mount_cte*1e-6*delta_temperature
    glass=1+glass_cte*1e-6*delta_temperature
    contact=min(mechanical_radius*mount,mechanical_radius*glass)
    edge=length+conic_sag(0,mechanical_radius,rear_radius)-conic_sag(0,mechanical_radius,front_radius)
    mount_radius=mechanical_radius*mount
    # At lens-edge contact the edge gap must also be corrected from the
    # expanded mount radius to the contact radius before conversion to CT.
    adjustment=(conic_sag(0,mount_radius,front_radius*glass)-conic_sag(0,mount_radius,rear_radius*glass)
                -conic_sag(0,contact,front_radius*glass)+conic_sag(0,contact,rear_radius*glass))
    return (edge*mount+adjustment+conic_sag(0,contact,front_radius*glass)-conic_sag(0,contact,rear_radius*glass),
            dict(contact_radius_mm=contact,mount_radius_mm=mount_radius,edge_adjustment_mm=adjustment,
                 branch='mount'if mount<glass else'lens'if mount>glass else'equal'))
