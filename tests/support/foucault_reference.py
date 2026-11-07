"""Discrete scalar diffraction reference for the controlled on-axis mirror."""
import numpy as np


def pupil(size=64):
    y, x = np.indices((size, size))
    return ((x-size//2)**2+(y-size//2)**2 <= (size//2-1)**2).astype(float)


def returned_amplitude(knife, size=64):
    """Half-weight the central Fourier bin; return the cropped complex field.

    The Fourier index signs here are array conventions, distinct from physical
    image-surface knife coordinates. Zero padding doubles the pupil array.
    """
    p = pupil(size)
    pad = size//2
    focal = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(np.pad(p, pad))))
    indices = np.arange(2*size)
    if knife in {"Horiz_Above", "Vert_Right"}:
        mask = (indices > size).astype(float)
    elif knife in {"Horiz_Below", "Vert_Left"}:
        mask = (indices < size).astype(float)
    else:
        raise ValueError(knife)
    mask[size] = .5
    mask = mask[:, None] if knife.startswith("Horiz") else mask[None, :]
    near = np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(focal*mask)))
    return near[pad:pad+size, pad:pad+size]


def shadowgram(knife, size=64):
    intensity = abs(returned_amplitude(knife, size))**2
    return intensity/intensity.max()
