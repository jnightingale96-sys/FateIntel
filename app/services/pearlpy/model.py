from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from typing import Iterable
import numpy as np

from .types import ApplicationEvent, Chemical, HydrologySeries, SimulationResult, SoilProfile
from .sorption import freundlich_partition
from .processes import exact_first_order_loss, interface_transport_fluxes, transformation_rate_d1


@dataclass
class PearlLiteModel:
    soil: SoilProfile
    chemical: Chemical
    hydrology: HydrologySeries
    applications: Iterable[ApplicationEvent] = ()
    max_transport_substep_d: float = 0.25
    negativity_tolerance_kg_m2: float = 1e-16
    monitor_interface_index: int | None = None

    def __post_init__(self) -> None:
        if self.hydrology.n_layers != self.soil.n_layers:
            raise ValueError("Hydrology and soil must have the same number of layers")
        if self.max_transport_substep_d <= 0:
            raise ValueError("max_transport_substep_d must be positive")
        if self.monitor_interface_index is not None and not (0 < self.monitor_interface_index <= self.soil.n_layers):
            raise ValueError("monitor_interface_index must identify an internal or bottom interface")
        self.applications = tuple(sorted(self.applications, key=lambda x: x.time_d))
        for event in self.applications:
            if event.target_layer >= self.soil.n_layers:
                raise ValueError("Application target layer is outside profile")

    def _partition(self, mass_kg_m2: np.ndarray, theta: np.ndarray):
        c_star = mass_kg_m2 / self.soil.thickness_m
        return freundlich_partition(
            c_star_kg_m3=c_star,
            theta=theta,
            bulk_density_kg_m3=self.soil.bulk_density_kg_m3,
            kf_m3_kg=self.soil.freundlich_kf_m3_kg,
            exponent=self.soil.freundlich_n,
            c_ref_kg_m3=self.soil.freundlich_c_ref_kg_m3,
        )

    def _transport(self, mass, theta, q_interfaces, dt_d):
        remaining = dt_d
        bottom_loss = 0.0
        target_loss = 0.0
        surface_loss = 0.0
        current = mass.copy()
        while remaining > 1e-14:
            proposed = min(self.max_transport_substep_d, remaining)
            while True:
                c_liq, _ = self._partition(current, theta)
                flux = interface_transport_fluxes(
                    c_liq_kg_m3=c_liq,
                    water_flux_interfaces_m_d=q_interfaces,
                    thickness_m=self.soil.thickness_m,
                    dispersivity_m=self.soil.dispersivity_m,
                    molecular_diffusion_m2_d=self.soil.molecular_diffusion_m2_d,
                )
                delta = (flux[:-1] - flux[1:]) * proposed
                candidate = current + delta
                if np.all(candidate >= -self.negativity_tolerance_kg_m2):
                    candidate[candidate < 0.0] = 0.0
                    current = candidate
                    bottom_loss += max(flux[-1], 0.0) * proposed
                    if self.monitor_interface_index is not None:
                        target_loss += max(flux[self.monitor_interface_index], 0.0) * proposed
                    surface_loss += max(-flux[0], 0.0) * proposed
                    remaining -= proposed
                    break
                proposed *= 0.5
                if proposed < 1e-10:
                    raise RuntimeError("Transport time step collapsed while preventing negative mass")
        return current, bottom_loss, target_loss, surface_loss

    def run(self, initial_mass_kg_m2: np.ndarray | None = None) -> SimulationResult:
        n_steps, n_layers, dt = self.hydrology.n_steps, self.soil.n_layers, self.hydrology.dt_d
        mass = np.zeros(n_layers, dtype=float) if initial_mass_kg_m2 is None else np.asarray(initial_mass_kg_m2, dtype=float).copy()
        if mass.shape != (n_layers,) or np.any(mass < 0):
            raise ValueError(f"initial_mass_kg_m2 must be a non-negative vector of length {n_layers}")
        initial_total = float(mass.sum())
        time = np.arange(n_steps + 1, dtype=float) * dt
        mass_hist = np.zeros((n_steps + 1, n_layers), dtype=float)
        c_liq_hist = np.zeros_like(mass_hist)
        sorbed_hist = np.zeros_like(mass_hist)
        applied_hist = np.zeros(n_steps + 1)
        degraded_hist = np.zeros(n_steps + 1)
        uptake_hist = np.zeros(n_steps + 1)
        bottom_hist = np.zeros(n_steps + 1)
        target_hist = np.zeros(n_steps + 1)
        surface_hist = np.zeros(n_steps + 1)
        balance_hist = np.zeros(n_steps + 1)
        events_by_step = defaultdict(list)
        for event in self.applications:
            step = int(np.floor(event.time_d / dt + 1e-12))
            if 0 <= step < n_steps:
                events_by_step[step].append(event)
        c0, x0 = self._partition(mass, self.hydrology.theta[0])
        mass_hist[0], c_liq_hist[0], sorbed_hist[0] = mass, c0, x0
        cumulative_applied = cumulative_degraded = cumulative_uptake = cumulative_bottom = cumulative_target = cumulative_surface = 0.0
        for step in range(n_steps):
            theta = self.hydrology.theta[step]
            temperature = self.hydrology.temperature_c[step]
            q = self.hydrology.water_flux_interfaces_m_d[step]
            root_uptake = self.hydrology.root_water_uptake_d1[step]
            for event in events_by_step.get(step, []):
                mass[event.target_layer] += event.dose_kg_m2
                cumulative_applied += event.dose_kg_m2
            k = transformation_rate_d1(
                dt50_ref_d=self.chemical.dt50_ref_d,
                temperature_c=temperature,
                temperature_ref_c=self.chemical.temperature_ref_c,
                activation_energy_kj_mol=self.chemical.activation_energy_kj_mol,
                theta=theta,
                theta_ref=self.soil.theta_ref,
                moisture_exponent=self.chemical.moisture_exponent,
                depth_factor=self.soil.depth_transformation_factor,
            )
            mass, degraded = exact_first_order_loss(mass, k, dt)
            cumulative_degraded += float(degraded.sum())
            mass, bottom_loss, target_loss, surface_loss = self._transport(mass, theta, q, dt)
            cumulative_bottom += bottom_loss
            cumulative_target += target_loss
            cumulative_surface += surface_loss
            c_liq, _ = self._partition(mass, theta)
            uptake_rate = root_uptake * self.chemical.root_uptake_factor * c_liq * self.soil.thickness_m
            uptake_loss = np.minimum(mass, uptake_rate * dt)
            mass -= uptake_loss
            cumulative_uptake += float(uptake_loss.sum())
            c_liq, x_sorbed = self._partition(mass, theta)
            idx = step + 1
            mass_hist[idx], c_liq_hist[idx], sorbed_hist[idx] = mass, c_liq, x_sorbed
            applied_hist[idx], degraded_hist[idx], uptake_hist[idx] = cumulative_applied, cumulative_degraded, cumulative_uptake
            bottom_hist[idx], target_hist[idx], surface_hist[idx] = cumulative_bottom, cumulative_target, cumulative_surface
            expected = initial_total + cumulative_applied
            accounted = float(mass.sum()) + cumulative_degraded + cumulative_uptake + cumulative_bottom + cumulative_surface
            balance_hist[idx] = expected - accounted
        return SimulationResult(
            time_d=time,
            layer_mass_kg_m2=mass_hist,
            liquid_concentration_kg_m3=c_liq_hist,
            sorbed_content_kg_kg=sorbed_hist,
            cumulative_applied_kg_m2=applied_hist,
            cumulative_degraded_kg_m2=degraded_hist,
            cumulative_uptake_kg_m2=uptake_hist,
            cumulative_bottom_leached_kg_m2=bottom_hist,
            cumulative_target_leached_kg_m2=target_hist,
            cumulative_surface_export_kg_m2=surface_hist,
            mass_balance_error_kg_m2=balance_hist,
        )
