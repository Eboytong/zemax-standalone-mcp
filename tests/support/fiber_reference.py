"""Scalar overlap of a circular pupil with an unaberrated Gaussian fiber mode."""
import math


def circular_pupil_coupling(radius, image_distance, receiver_na, *,
                            object_distance=None, source_na=None):
    """Integrate Gaussian pupil amplitudes analytically in the paraxial limit.

    Receiver amplitude at the pupil is exp(-r²/(image_distance*NA)²).
    With a source, its denominator includes all emitted Gaussian power; the
    overlap numerator includes only the circular entrance pupil.
    """
    values = [radius, image_distance, receiver_na]
    if (object_distance is None) != (source_na is None):
        raise ValueError('source distance and NA must be supplied together')
    if source_na is not None:
        values += [object_distance, source_na]
    if any(not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('reference dimensions and NA must be finite and positive')
    ar = (radius / (image_distance * receiver_na)) ** 2
    if source_na is None:
        return 2 * (-math.expm1(-ar)) ** 2 / ar
    a_source = (radius / (object_distance * source_na)) ** 2
    combined = a_source + ar
    return 4 * a_source * ar * (-math.expm1(-combined) / combined) ** 2
