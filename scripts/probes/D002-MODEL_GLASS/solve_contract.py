"""Pure contracts for D002 MaterialModel solve readback and close-receipt judging.

Kept free of zemax imports so ordinary tests can exercise it without native.
Mirrors the public ``get_surfaces`` shape produced by ``Backend._surface_data``:
``surface["cells"]["material"]["solve"]`` = {"type": <SolveType>, **SOLVE_FIELDS["MaterialModel"]}
where SOLVE_FIELDS["MaterialModel"] maps to IndexNd/AbbeVd/dPgF/VaryIndex/VaryAbbe/VarydPgF.
"""
import math

# Field order matches modeling.SOLVE_FIELDS["MaterialModel"] (public readback keys).
SOLVE_PARAM_KEYS = ("index_nd", "abbe_vd", "dpgf", "vary_index", "vary_abbe", "vary_dpgf")


def solve_actual(surface):
    """Pull the six MaterialModel solve fields from a get_surfaces surface payload."""
    cell = (surface.get("cells") or {}).get("material") or {}
    solve = cell.get("solve") or {}
    out = dict(model_type=solve.get("type"))
    for key in SOLVE_PARAM_KEYS:
        out[key] = solve.get(key)
    return out


def _match(requested, actual, rtol=1e-9, atol=1e-12):
    """Strict comparison: bools must both be real bools and equal; numbers finite/convertible."""
    if isinstance(requested, bool) or isinstance(actual, bool):
        return isinstance(requested, bool) and isinstance(actual, bool) and requested is actual
    try:
        left = float(requested)
        right = float(actual)
    except (TypeError, ValueError):
        return False
    if not (math.isfinite(left) and math.isfinite(right)):
        return False
    return abs(right - left) <= atol + rtol * abs(left)


def solve_readback_checks(model, actual):
    """Compare each requested field that appears in ``model`` against the actual readback."""
    checks = {}
    for key in SOLVE_PARAM_KEYS:
        if key in model:
            checks[key] = dict(requested=model[key], actual=actual.get(key),
                               match=_match(model[key], actual.get(key)))
    return checks


def close_receipt_verdict(content):
    """Judge the shutdown receipt content written by Backend._write_close_receipt.

    Strict pass: ``native.closed is True`` AND ``forced is False`` AND native error empty.
    A missing ``forced`` field cannot prove a non-forced close, so it fails.
    """
    if not content:
        return dict(passed=False, reason="close_receipt_missing")
    native = content.get("native") or {}
    checkpoint = content.get("checkpoint") or {}
    native_closed = native.get("closed") is True
    forced = content.get("forced")
    native_error = native.get("error")
    passed = native_closed and forced is False and native_error in (None, "")
    return dict(passed=passed, native_closed=native_closed, forced=forced,
                native_error=native_error,
                checkpoint_attempted=bool(checkpoint.get("attempted")),
                checkpoint_ok=checkpoint.get("ok"))


def session_closed(receipt_verdict, active_task_after_shutdown, cleanup_error):
    """Final ``closed`` = clean close receipt AND no active task AND no cleanup error.

    ``closed`` must not be inferred from a ``disconnect`` return value; it is only
    established after shutdown from these three facts.
    """
    receipt_passed = bool((receipt_verdict or {}).get("passed"))
    no_active_task = active_task_after_shutdown is False
    no_cleanup_error = cleanup_error is None
    return dict(closed=receipt_passed and no_active_task and no_cleanup_error,
                receipt_passed=receipt_passed, no_active_task=no_active_task,
                no_cleanup_error=no_cleanup_error)
