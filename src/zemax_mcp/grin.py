"""Parameter identities for the installed Gradient2/Gradient3 surfaces."""

from .errors import ZemaxError

GRIN_PARAMETERS = {
    "Gradient2": (("delta_t", 1), ("n0", 0), ("nr2", -2), ("nr4", -4),
                  ("nr6", -6), ("nr8", -8), ("nr10", -10), ("nr12", -12)),
    "Gradient3": (("delta_t", 1), ("n0", 0), ("nr2", -2), ("nr4", -4),
                  ("nr6", -6), ("nz1", -1), ("nz2", -2), ("nz3", -3)),
}


def validate_grin_patch(surface_type, change):
    if surface_type not in GRIN_PARAMETERS:
        return
    parameters = set(change.parameters)
    parameters.update(int(cell.removeprefix("parameter_")) for cell in change.solves
                      if cell.startswith("parameter_"))
    invalid = sorted(parameters - set(range(1, 9)))
    if invalid:
        raise ZemaxError("INVALID_ARGUMENT", "此GRIN面型使用参数1至8。", surface=change.surface,
                         surface_type=surface_type, parameters=invalid)
    for number in (1, 2):
        if number in change.parameters and change.parameters[number] <= 0:
            raise ZemaxError("INVALID_ARGUMENT", "GRIN积分步长和原点折射率项须为正。",
                             surface=change.surface, parameter=number, value=change.parameters[number])


def grin_definition(surface_type):
    """Return JSON metadata; length powers refer to current lens units."""
    if surface_type not in GRIN_PARAMETERS:
        return None
    return dict(
        polynomial_quantity="index_squared" if surface_type == "Gradient2" else "index",
        formula=("n^2 = n0 + nr2*r^2 + nr4*r^4 + nr6*r^6 + nr8*r^8 + nr10*r^10 + nr12*r^12"
                 if surface_type == "Gradient2" else
                 "n = n0 + nr2*r^2 + nr4*r^4 + nr6*r^6 + nz1*z + nz2*z^2 + nz3*z^3"),
        coordinates="r=sqrt(x*x+y*y); z measured from front vertex; current lens units",
        dispersion="coefficients are wavelength independent",
        parameters=[dict(parameter=i, cell=f"parameter_{i}", name=name,
                         unit="dimensionless" if power == 0 else f"lens_unit^{power}")
                    for i, (name, power) in enumerate(GRIN_PARAMETERS[surface_type], 1)],
    )
