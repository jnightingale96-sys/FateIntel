"""Typed application errors with safe HTTP mappings."""

from __future__ import annotations

from typing import Any


class EnviroChemError(Exception):
    status_code = 500
    error_code = "envirochem_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ChemicalIdentityError(EnviroChemError):
    status_code = 422
    error_code = "chemical_identity_error"


class ModelInputError(EnviroChemError):
    status_code = 422
    error_code = "model_input_error"


class ExternalModelUnavailableError(EnviroChemError):
    status_code = 503
    error_code = "external_model_unavailable"


class ExternalDataSourceError(EnviroChemError):
    status_code = 502
    error_code = "external_data_source_error"


class ModelExecutionError(EnviroChemError):
    status_code = 502
    error_code = "model_execution_error"


class ConfigurationError(EnviroChemError):
    status_code = 500
    error_code = "configuration_error"


class ReachReviewError(EnviroChemError):
    status_code = 422
    error_code = "reach_review_error"


class ReachSigningUnavailableError(EnviroChemError):
    status_code = 503
    error_code = "reach_signing_unavailable"
