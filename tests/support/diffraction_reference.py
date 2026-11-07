"""Independent, DC-normalized linear autocorrelation for complex pupil samples."""
import numpy as np


def pupil_autocorrelation(pupil):
    pupil = np.asarray(pupil, dtype=complex)
    if pupil.ndim != 2 or not np.all(np.isfinite(pupil)):
        raise ValueError('Expected a finite two-dimensional complex pupil')
    power = float(np.sum(abs(pupil)**2))
    if power <= 0:
        raise ValueError('Pupil power must be positive')
    shape = tuple(2*n for n in pupil.shape)
    spectrum = np.fft.fft2(pupil, s=shape)
    return abs(np.fft.fftshift(np.fft.ifft2(abs(spectrum)**2)))/power
