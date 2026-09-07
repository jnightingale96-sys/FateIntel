from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def _array(value, *, name: str) -> FloatArray:
    arr = np.asarray(value, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values")
    return arr


@dataclass(frozen=True)
class SoilProfile:
    thickness_m: FloatArray
    bulk_density_kg_m3: FloatArray
    freundlich_kf_m3_kg: FloatArray
    freundlich_n: FloatArray
    freundlich_c_ref_kg_m3: FloatArray
    theta_ref: FloatArray
    depth_transformation_factor: FloatArray
    dispersivity_m: FloatArray
    molecular_diffusion_m2_d: FloatArray

    def __post_init__(self) -> None:
        fields = {
            "thickness_m": _array(self.thickness_m, name="thickness_m"),
            "bulk_density_kg_m3": _array(self.bulk_density_kg_m3, name="bulk_density_kg_m3"),
            "freundlich_kf_m3_kg": _array(self.freundlich_kf_m3_kg, name="freundlich_kf_m3_kg"),
            "freundlich_n": _array(self.freundlich_n, name="freundlich_n"),
            "freundlich_c_ref_kg_m3": _array(self.freundlich_c_ref_kg_m3, name="freundlich_c_ref_kg_m3"),
            "theta_ref": _array(self.theta_ref, name="theta_ref"),
            "depth_transformation_factor": _array(self.depth_transformation_factor, name="depth_transformation_factor"),
            "dispersivity_m": _array(self.dispersivity_m, name="dispersivity_m"),
            "molecular_diffusion_m2_d": _array(self.molecular_diffusion_m2_d, name="molecular_diffusion_m2_d"),
        }
        sizes = {arr.size for arr in fields.values()}
        if len(sizes) != 1 or 0 in sizes:
            raise ValueError("All soil arrays must have the same positive length")
        for name, arr in fields.items():
            object.__setattr__(self, name, arr)
        if np.any(self.thickness_m <= 0):
            raise ValueError("Layer thicknesses must be positive")
        if np.any(self.bulk_density_kg_m3 <= 0):
            raise ValueError("Bulk density must be positive")
        if np.any(self.freundlich_kf_m3_kg < 0):
            raise ValueError("Freundlich Kf cannot be negative")
        if np.any(self.freundlich_n <= 0):
            raise ValueError("Freundlich exponent must be positive")
        if np.any(self.theta_ref <= 0):
            raise ValueError("Reference water content must be positive")
        if np.any(self.depth_transformation_factor < 0):
            raise ValueError("Depth transformation factors cannot be negative")

    @property
    def n_layers(self) -> int:
        return int(self.thickness_m.size)

    @property
    def interface_depth_m(self) -> FloatArray:
        return np.concatenate(([0.0], np.cumsum(self.thickness_m)))

    @property
    def centre_depth_m(self) -> FloatArray:
        interfaces = self.interface_depth_m
        return 0.5 * (interfaces[:-1] + interfaces[1:])


@dataclass(frozen=True)
class Chemical:
    dt50_ref_d: float
    temperature_ref_c: float = 20.0
    activation_energy_kj_mol: float = 65.4
    moisture_exponent: float = 0.0
    root_uptake_factor: float = 0.0


@dataclass(frozen=True)
class HydrologySeries:
    dt_d: float
    theta: FloatArray
    water_flux_interfaces_m_d: FloatArray
    temperature_c: FloatArray
    root_water_uptake_d1: FloatArray

    def __post_init__(self) -> None:
        theta = np.asarray(self.theta, dtype=float)
        q = np.asarray(self.water_flux_interfaces_m_d, dtype=float)
        temperature = np.asarray(self.temperature_c, dtype=float)
        uptake = np.asarray(self.root_water_uptake_d1, dtype=float)
        if self.dt_d <= 0:
            raise ValueError("Hydrology time step must be positive")
        if theta.ndim != 2 or temperature.shape != theta.shape or uptake.shape != theta.shape:
            raise ValueError("theta, temperature and root uptake must be equal two-dimensional arrays")
        if q.shape != (theta.shape[0], theta.shape[1] + 1):
            raise ValueError("Water-flux array must contain N+1 interfaces for N layers")
        if np.any(theta <= 0):
            raise ValueError("Water content must be positive")
        if np.any(uptake < 0):
            raise ValueError("Root uptake cannot be negative")
        object.__setattr__(self, "theta", theta)
        object.__setattr__(self, "water_flux_interfaces_m_d", q)
        object.__setattr__(self, "temperature_c", temperature)
        object.__setattr__(self, "root_water_uptake_d1", uptake)

    @property
    def n_steps(self) -> int:
        return int(self.theta.shape[0])

    @property
    def n_layers(self) -> int:
        return int(self.theta.shape[1])


@dataclass(frozen=True)
class ApplicationEvent:
    time_d: float
    dose_kg_m2: float
    target_layer: int = 0


@dataclass(frozen=True)
class SimulationResult:
    time_d: FloatArray
    layer_mass_kg_m2: FloatArray
    liquid_concentration_kg_m3: FloatArray
    sorbed_content_kg_kg: FloatArray
    cumulative_applied_kg_m2: FloatArray
    cumulative_degraded_kg_m2: FloatArray
    cumulative_uptake_kg_m2: FloatArray
    cumulative_bottom_leached_kg_m2: FloatArray
    cumulative_target_leached_kg_m2: FloatArray
    cumulative_surface_export_kg_m2: FloatArray
    mass_balance_error_kg_m2: FloatArray
