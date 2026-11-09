"""Independent lossless spherical/plano lens Fresnel reference, axial incidence."""
import math


def interface_power(n1, n2, incidence):
    transmitted = math.asin(n1 * math.sin(incidence) / n2)
    ci, ct = math.cos(incidence), math.cos(transmitted)
    rs = ((n1 * ci - n2 * ct) / (n1 * ci + n2 * ct)) ** 2
    rp = ((n2 * ci - n1 * ct) / (n2 * ci + n1 * ct)) ** 2
    return 1 - rs, 1 - rp


def spherical_plano_power(x, y, radius=20., index=1.5, jx=1., jy=0.):
    r = math.hypot(x, y)
    theta = math.asin(r / radius)
    beta = theta - math.asin(math.sin(theta) / index)
    s1, p1 = interface_power(1., index, theta)
    s2, p2 = interface_power(index, 1., beta)
    if r == 0:
        return (s1 * s2 + p1 * p2) / 2
    # In each meridional plane the p component is radial, s is azimuthal.
    wp = (jx * x / r + jy * y / r) ** 2
    ws = (-jx * y / r + jy * x / r) ** 2
    return (wp * p1 * p2 + ws * s1 * s2) / (jx * jx + jy * jy)
