from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def kf_from_koc(koc_m3_kg_oc: float | FloatArray, organic_carbon_fraction: float | FloatArray):
    return np.asarray(koc_m3_kg_oc, dtype=float) * np.asarray(organic_carbon_fraction, dtype=float)


def kf_from_kom(kom_m3_kg_om: float | FloatArray, organic_matter_fraction: float | FloatArray):
    return np.asarray(kom_m3_kg_om, dtype=float) * np.asarray(organic_matter_fraction, dtype=float)


def _fixed_point_scalar(c_star, theta, rho_b, kf, exponent, c_ref, relative_tolerance, max_iterations):
    if c_star <= 0.0:
        return 0.0
    if kf == 0.0:
        return c_star / theta
    c_old = max(c_star / (theta + rho_b * kf), np.finfo(float).tiny)
    for _ in range(max_iterations):
        x_over_c = kf * (c_ref ** (1.0 - exponent)) * (c_old ** (exponent - 1.0))
        c_new = c_star / (theta + rho_b * x_over_c)
        if not np.isfinite(c_new) or c_new <= 0:
            return None
        c_new = 0.5 * c_old + 0.5 * c_new
        if abs(c_new - c_old) <= relative_tolerance * max(c_new, c_old, 1e-30):
            return c_new
        c_old = c_new
    return None


def _bisection_scalar(c_star, theta, rho_b, kf, exponent, c_ref, relative_tolerance, max_iterations):
    if c_star <= 0.0:
        return 0.0
    if kf == 0.0:
        return c_star / theta

    def residual(c_liq):
        x_sorbed = kf * c_ref * (c_liq / c_ref) ** exponent
        return theta * c_liq + rho_b * x_sorbed - c_star

    low, high = 0.0, c_star / theta
    if residual(high) < 0:
        raise RuntimeError("Failed to bracket Freundlich partition root")
    for _ in range(max_iterations * 4):
        mid = 0.5 * (low + high)
        if residual(mid) > 0:
            high = mid
        else:
            low = mid
        if (high - low) <= relative_tolerance * max(high, 1e-30):
            return 0.5 * (low + high)
    return 0.5 * (low + high)


def freundlich_partition(
    c_star_kg_m3,
    theta,
    bulk_density_kg_m3,
    kf_m3_kg,
    exponent,
    c_ref_kg_m3=1e-3,
    relative_tolerance: float = 1e-11,
    max_iterations: int = 200,
):
    arrays = np.broadcast_arrays(
        np.asarray(c_star_kg_m3, dtype=float),
        np.asarray(theta, dtype=float),
        np.asarray(bulk_density_kg_m3, dtype=float),
        np.asarray(kf_m3_kg, dtype=float),
        np.asarray(exponent, dtype=float),
        np.asarray(c_ref_kg_m3, dtype=float),
    )
    c_star, theta_a, rho, kf, n, c_ref = arrays
    if np.any(c_star < 0) or np.any(theta_a <= 0) or np.any(rho <= 0) or np.any(kf < 0) or np.any(n <= 0) or np.any(c_ref <= 0):
        raise ValueError("Invalid Freundlich partition inputs")

    # Linear Freundlich sorption (N = 1) is common in screening runs and has
    # an exact vector solution. Avoiding scalar iteration makes multi-year
    # FOCUS-style simulations substantially faster without changing results.
    if np.all(np.isclose(n, 1.0, rtol=0.0, atol=1e-14)):
        c_liq = np.divide(c_star, theta_a + rho * kf, out=np.zeros_like(c_star), where=(theta_a + rho * kf) > 0)
        x_sorbed = kf * c_liq
        return c_liq, x_sorbed

    c_liq = np.empty_like(c_star)
    it = np.nditer(
        [c_star, theta_a, rho, kf, n, c_ref, c_liq],
        flags=["refs_ok", "zerosize_ok"],
        op_flags=[["readonly"]] * 6 + [["writeonly"]],
    )
    for c_s, th, rb, k_f, exp_n, c_r, out in it:
        solved = _fixed_point_scalar(float(c_s), float(th), float(rb), float(k_f), float(exp_n), float(c_r), relative_tolerance, max_iterations)
        if solved is None:
            solved = _bisection_scalar(float(c_s), float(th), float(rb), float(k_f), float(exp_n), float(c_r), relative_tolerance, max_iterations)
        out[...] = solved
    c_liq = it.operands[-1]
    x_sorbed = kf * c_ref * np.power(np.divide(c_liq, c_ref, out=np.zeros_like(c_liq), where=c_ref > 0), n)
    return c_liq, x_sorbed
