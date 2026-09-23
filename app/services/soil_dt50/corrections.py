"""
Environmental-condition corrections for soil degradation half-lives.

The PEPPER prediction is a representative *laboratory* aerobic soil DT50
(OECD 307). In the training data the median incubation temperature is 20 °C
(IQR 20-20 °C) and moisture is typically 40-55 % MWHC, i.e. close to the
FOCUS/EFSA reference conditions (20 °C, pF2 / field capacity). These functions
move a reference DT50 to site conditions, or normalise a measured DT50 back to
reference conditions, following EU practice:

  * Temperature: Arrhenius with Ea = 65.4 kJ/mol (EFSA PPR Panel 2007;
    EFSA 2008 opinion; equivalent to Q10 = 2.58 around 20 °C). FOCUS models
    assume no degradation at or below 0 °C.
  * Moisture: Walker (1974) relationship  f_W = (theta / theta_ref) ** B,
    B = 0.7 (FOCUS 2006 generic value / EFSA 2014), capped at 1 when wetter
    than reference.
  * Depth: FOCUS groundwater default depth factors (0-30 cm: 1.0,
    30-60 cm: 0.5, 60-100 cm: 0.3, >100 cm: 0.0) - optional.

All rate factors multiply the degradation rate constant; DT50 is divided by them.
"""
from __future__ import annotations

import math

R_GAS = 8.314  # J mol-1 K-1
EA_DEFAULT = 65_400.0  # J mol-1 (EFSA)
B_WALKER_DEFAULT = 0.7
T_REF_C = 20.0


def temperature_factor(temp_c: float, ea: float = EA_DEFAULT, t_ref_c: float = T_REF_C) -> float:
    """Rate multiplier relative to t_ref (Arrhenius). Returns 0 at <= 0 °C (FOCUS)."""
    if temp_c <= 0:
        return 0.0
    t, t_ref = temp_c + 273.15, t_ref_c + 273.15
    return math.exp((ea / R_GAS) * (1.0 / t_ref - 1.0 / t))


def moisture_factor(theta: float, theta_ref: float, b: float = B_WALKER_DEFAULT) -> float:
    """Walker moisture rate multiplier. theta and theta_ref in the same units
    (e.g. % MWHC, or volumetric water content vs. content at pF2)."""
    if theta_ref <= 0:
        raise ValueError("theta_ref must be > 0")
    if theta <= 0:
        return 0.0
    return min(1.0, (theta / theta_ref) ** b)


def depth_factor(depth_cm: float) -> float:
    """FOCUS default depth-dependence of degradation rate."""
    if depth_cm < 30:
        return 1.0
    if depth_cm < 60:
        return 0.5
    if depth_cm <= 100:
        return 0.3
    return 0.0


def combined_factor(temp_c: float | None = None, theta: float | None = None,
                    theta_ref: float | None = None, depth_cm: float | None = None,
                    ea: float = EA_DEFAULT, b: float = B_WALKER_DEFAULT) -> dict:
    f_t = temperature_factor(temp_c, ea) if temp_c is not None else 1.0
    f_w = moisture_factor(theta, theta_ref, b) if (theta is not None and theta_ref) else 1.0
    f_d = depth_factor(depth_cm) if depth_cm is not None else 1.0
    return {"f_temperature": f_t, "f_moisture": f_w, "f_depth": f_d, "f_total": f_t * f_w * f_d}


def to_site_conditions(dt50_ref_days: float, **conditions) -> tuple[float, dict]:
    """Reference DT50 (20 °C, pF2) -> DT50 at site conditions."""
    f = combined_factor(**conditions)
    dt50 = math.inf if f["f_total"] == 0 else dt50_ref_days / f["f_total"]
    return dt50, f


def to_reference_conditions(dt50_obs_days: float, temp_c: float,
                            theta: float | None = None, theta_ref: float | None = None,
                            ea: float = EA_DEFAULT, b: float = B_WALKER_DEFAULT) -> float:
    """Normalise a measured DT50 to 20 °C / reference moisture (EFSA/FOCUS normalisation)."""
    f = combined_factor(temp_c=temp_c, theta=theta, theta_ref=theta_ref, ea=ea, b=b)["f_total"]
    return dt50_obs_days * f
