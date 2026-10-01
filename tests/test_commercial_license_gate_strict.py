"""COMMERCIAL_LICENSE_GATE_STRICT must close every licence-gated external-data provider's local/test
"academic evaluation" exemption -- enviPath, BioTransformer, soil_dt50 (PEPPER), OASIS soil DT50 and NITE
ready biodegradability all share the same restriction shape (app/config.py's own docstring on the flag).
This is what makes a build demonstrated to, or run by, someone outside the project safe to actually show:
without it, all five run live under envirochem_environment="local" even though no licence was ever confirmed.
"""

from __future__ import annotations

import pytest

from app.config import Settings
from app.services.envipath import _commercial_gate as envipath_gate
from app.services.nite_ready_biodegradability import commercial_gate as nite_gate
from app.services.oasis_soil_dt50 import commercial_gate as oasis_gate
from app.services.soil_dt50 import commercial_gate as pepper_gate
from app.services.transformation_pathways import _commercial_gate as biotransformer_gate

GATES = [envipath_gate, biotransformer_gate, oasis_gate, nite_gate, pepper_gate]


@pytest.mark.parametrize("gate", GATES, ids=[g.__module__ for g in GATES])
def test_strict_flag_closes_the_local_evaluation_exemption(gate):
    local_open = Settings(_env_file=None, envirochem_environment="local")
    assert gate(local_open)[0] is True, f"{gate.__module__} should be open under the default local/test exemption"

    local_strict = Settings(_env_file=None, envirochem_environment="local", commercial_license_gate_strict=True)
    assert gate(local_strict)[0] is False, f"{gate.__module__} must close under commercial_license_gate_strict even though environment is local"


@pytest.mark.parametrize("gate", GATES, ids=[g.__module__ for g in GATES])
def test_strict_flag_does_not_override_an_actually_confirmed_licence(gate):
    # Strict mode removes the environment-based exemption, not a real confirmed licence.
    field_names = [name for name in Settings.model_fields if name.endswith("_commercial_license_confirmed")]
    # Each gate module has exactly one matching confirmation flag on Settings; find it by probing.
    confirmed_open = None
    for field in field_names:
        config = Settings(_env_file=None, envirochem_environment="local", commercial_license_gate_strict=True, **{field: True})
        if gate(config)[0] is True:
            confirmed_open = field
            break
    assert confirmed_open is not None, f"{gate.__module__} never opens even with its own licence flag confirmed under strict mode"
