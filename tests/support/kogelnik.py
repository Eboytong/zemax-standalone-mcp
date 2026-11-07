"""Lossless unslanted transmission-grating reference, lengths in micrometers.

Independent closed-form evaluation of the coupled-wave equations documented in
Ansys' Kogelnik article and Kick et al., JEOS-RP 14, 15 (2018), equations 3–4.
"""
import math


def unslanted_transmission(angle_degrees,wavelength_um,polarization='S',
                          construction_angle_degrees=math.degrees(math.atan(.5)),
                          construction_wavelength_um=.55,index=1.5,modulation=.02,thickness_um=10):
    beta=2*math.pi*index/wavelength_um
    ky=2*math.pi*math.sin(math.radians(angle_degrees))/wavelength_um
    kz=math.sqrt(beta*beta-ky*ky)
    grating=4*math.pi*math.sin(math.radians(construction_angle_degrees))/construction_wavelength_um
    cosine=kz/beta
    detuning=(2*ky*grating-grating*grating)/(2*beta)
    kappa=math.pi*modulation/wavelength_um
    if polarization=='P':
        # TM fields follow the elastic diffracted ray on the k-sphere. The
        # off-shell coupled vector used in detuning has a different z component.
        diffracted_z=math.sqrt(beta*beta-(ky-grating)**2)
        kappa*=(ky*(ky-grating)+kz*diffracted_z)/(beta*beta)
    elif polarization!='S':raise ValueError('polarization must be S or P')
    nu=kappa*thickness_um/cosine
    xi=detuning*thickness_um/(2*cosine)
    v=nu*nu+xi*xi
    return nu*nu/v*math.sin(math.sqrt(v))**2 if v else 0.
