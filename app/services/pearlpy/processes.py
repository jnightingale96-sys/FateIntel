from __future__ import annotations

import math
import numpy as np


def exact_first_order_loss(mass_kg_m2: np.ndarray, rate_d1: np.ndarray, dt_d: float):
    remaining = np.asarray(mass_kg_m2, dtype=float) * np.exp(-np.asarray(rate_d1, dtype=float) * dt_d)
    return remaining, np.asarray(mass_kg_m2, dtype=float) - remaining


def transformation_rate_d1(
    *,
    dt50_ref_d: float,
    temperature_c: np.ndarray,
    temperature_ref_c: float,
    activation_energy_kj_mol: float,
    theta: np.ndarray,
    theta_ref: np.ndarray,
    moisture_exponent: float,
    depth_factor: np.ndarray,
):
    if dt50_ref_d <= 0:
        raise ValueError("DT50 must be positive")
    k_ref = math.log(2.0) / dt50_ref_d
    kelvin = np.asarray(temperature_c, dtype=float) + 273.15
    ref_kelvin = temperature_ref_c + 273.15
    if np.any(kelvin <= 0) or ref_kelvin <= 0:
        raise ValueError("Temperature must be above absolute zero")
    gas_constant = 8.31446261815324
    temperature_factor = np.exp(
        -(activation_energy_kj_mol * 1000.0) / gas_constant * (1.0 / kelvin - 1.0 / ref_kelvin)
    )
    if moisture_exponent == 0:
        moisture_factor = np.ones_like(kelvin)
    else:
        moisture_factor = np.power(np.maximum(np.asarray(theta) / np.asarray(theta_ref), 1e-12), moisture_exponent)
    return k_ref * temperature_factor * moisture_factor * np.asarray(depth_factor)


def interface_transport_fluxes(
    *,
    c_liq_kg_m3: np.ndarray,
    water_flux_interfaces_m_d: np.ndarray,
    thickness_m: np.ndarray,
    dispersivity_m: np.ndarray,
    molecular_diffusion_m2_d: np.ndarray,
):
    """Conservative 1-D liquid-phase flux at N+1 interfaces.

    Positive flux is downward. Infiltrating water and upward bottom inflow are
    treated as chemical-free boundary water. Internal transport combines
    upwind advection and a simple hydrodynamic-dispersion gradient term.
    """
    c = np.asarray(c_liq_kg_m3, dtype=float)
    q = np.asarray(water_flux_interfaces_m_d, dtype=float)
    dz = np.asarray(thickness_m, dtype=float)
    alpha = np.asarray(dispersivity_m, dtype=float)
    diffusion = np.asarray(molecular_diffusion_m2_d, dtype=float)
    n = c.size
    if q.shape != (n + 1,):
        raise ValueError("Interface water flux must have length N+1")
    flux = np.zeros(n + 1, dtype=float)

    flux[0] = q[0] * (0.0 if q[0] >= 0 else c[0])
    for interface in range(1, n):
        q_i = q[interface]
        upstream = c[interface - 1] if q_i >= 0 else c[interface]
        advective = q_i * upstream
        distance = 0.5 * (dz[interface - 1] + dz[interface])
        alpha_i = 0.5 * (alpha[interface - 1] + alpha[interface])
        diffusion_i = 0.5 * (diffusion[interface - 1] + diffusion[interface])
        dispersion = abs(q_i) * alpha_i + diffusion_i
        dispersive = -dispersion * (c[interface] - c[interface - 1]) / distance
        flux[interface] = advective + dispersive
    flux[-1] = q[-1] * (c[-1] if q[-1] >= 0 else 0.0)
    return flux
