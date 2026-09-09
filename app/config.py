"""Validated, non-secret runtime configuration for EnviroChem.

Settings are read from environment variables and an optional project-root
``.env`` file.  The application does not define placeholder API keys or
secrets that it does not use.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .version import DEFAULT_PORT


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_URL = f"sqlite:///{(PROJECT_ROOT / 'data' / 'envirochem.sqlite').as_posix()}"


def _read_env_file(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, value = line.split("=", 1)
        key = key.strip().upper()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key and value:
            values[key] = value
    return values


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    envirochem_port: int = Field(default=DEFAULT_PORT, ge=1, le=65535)
    envirochem_environment: Literal["local", "test", "staging", "production"] = "local"
    envirochem_debug: bool = False
    log_level: str = "INFO"
    log_format: Literal["text", "json"] = "text"

    database_url: str = DEFAULT_SQLITE_URL

    envirochem_spin_path: Path | None = None
    envirochem_pearl_path: Path | None = None
    envirochem_swash_path: Path | None = None
    envirochem_macro_path: Path | None = None
    envirochem_toxswa_path: Path | None = None
    envirochem_greater_path: Path | None = None
    envirochem_chemsteer_path: Path | None = None
    envirochem_cem_path: Path | None = None
    envirochem_efast_path: Path | None = None
    envirochem_pwc_path: Path | None = None
    # Official external tools are never bundled.  Local process execution is
    # disabled by default and requires an operator-controlled executable path,
    # fixed argument template and output-file contract for each model.
    envirochem_external_execution_enabled: bool = False
    envirochem_external_execution_timeout_seconds: int = Field(default=900, ge=1, le=7200)
    envirochem_pwc_command_args_json: str | None = None
    envirochem_pwc_output_globs_json: str | None = None
    envirochem_chemsteer_command_args_json: str | None = None
    envirochem_chemsteer_output_globs_json: str | None = None
    envirochem_cem_command_args_json: str | None = None
    envirochem_cem_output_globs_json: str | None = None
    envirochem_efast_command_args_json: str | None = None
    envirochem_efast_output_globs_json: str | None = None
    envirochem_native_rdkit: bool = False
    reach_manifest_private_key_path: Path | None = None

    # BioTransformer is an interim transformation-product prediction provider.
    # Its ENVMICRO module contains enviPath/EAWAG-derived data, so remote use is
    # restricted to local/test evaluation unless a commercial licence has been
    # confirmed explicitly by the operator.
    biotransformer_enabled: bool = True
    biotransformer_base_url: str = "https://biotransformer.ca"
    biotransformer_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    biotransformer_poll_interval_seconds: float = Field(default=1.0, ge=0.1, le=10)
    biotransformer_max_wait_seconds: float = Field(default=45.0, gt=0, le=300)
    biotransformer_commercial_license_confirmed: bool = False

    # enviPath is a second transformation-pathway provider: its own rule-based
    # prediction engine, plus curated/reviewed pathway packages (e.g. EAWAG-BBD)
    # searchable by compound. envipath.org states it is "free for academic and
    # non-commercial use only" and requires account registration -- the same
    # shape of restriction as BioTransformer's commercial-license gate above.
    # Credentials are optional (public packages can be searched anonymously)
    # and are read only from the environment/.env file, never from the UI.
    envipath_enabled: bool = True
    envipath_base_url: str = "https://envipath.org"
    # Live-verified 2026-09-08: envipath.org's REST API lives under /api/legacy/
    # and returns a clean 401 {"detail": "Unauthorized"} without a token/session --
    # no anonymous read access. An API token (Authorization: Bearer, generated
    # from the operator's own envipath.org account settings) is the recommended,
    # robust auth path; username/password session login is kept as a fallback
    # for older/self-hosted enviPath instances but is untested against the
    # current site, whose login page now sits behind a CAPTCHA-style challenge.
    envipath_api_token: str | None = None
    envipath_username: str | None = None
    envipath_password: str | None = None
    envipath_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    envipath_commercial_license_confirmed: bool = False

    # MassBank Europe is the analytical-identification feature's live connector:
    # an open REST API returning real, measured MS2 (product-ion) spectra plus
    # chromatography metadata (retention time, column, mobile phase, ionisation
    # mode), searchable by InChIKey. No account/API key is required -- live-
    # verified 2026-09-08 against https://massbank.eu/MassBank-api/records.
    massbank_enabled: bool = True
    massbank_base_url: str = "https://massbank.eu"
    massbank_timeout_seconds: float = Field(default=15.0, gt=0, le=120)

    def __init__(
        self,
        *,
        _env_file: str | Path | None = PROJECT_ROOT / ".env",
        **values,
    ):
        file_values = _read_env_file(Path(_env_file) if _env_file is not None else None)
        resolved: dict[str, object] = {}
        for field_name in type(self).model_fields:
            environment_name = field_name.upper()
            if environment_name in file_values:
                resolved[field_name] = file_values[environment_name]
            environment_value = os.environ.get(environment_name)
            if environment_value not in {None, ""}:
                resolved[field_name] = environment_value
        resolved.update(values)
        super().__init__(**resolved)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalised = value.strip().upper()
        if normalised not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR or CRITICAL")
        return normalised

    @field_validator("biotransformer_base_url")
    @classmethod
    def validate_biotransformer_base_url(cls, value: str) -> str:
        normalised = value.strip().rstrip("/")
        if not normalised.startswith("https://"):
            raise ValueError("BIOTRANSFORMER_BASE_URL must use HTTPS")
        return normalised

    @field_validator("envipath_base_url")
    @classmethod
    def validate_envipath_base_url(cls, value: str) -> str:
        normalised = value.strip().rstrip("/")
        if not normalised.startswith("https://"):
            raise ValueError("ENVIPATH_BASE_URL must use HTTPS")
        return normalised

    @field_validator("massbank_base_url")
    @classmethod
    def validate_massbank_base_url(cls, value: str) -> str:
        normalised = value.strip().rstrip("/")
        if not normalised.startswith("https://"):
            raise ValueError("MASSBANK_BASE_URL must use HTTPS")
        return normalised

    @property
    def database_backend(self) -> str:
        return self.database_url.split(":", 1)[0].lower()

    def external_model_path(self, model_key: str) -> Path | None:
        field_name = f"envirochem_{model_key.casefold()}_path"
        return getattr(self, field_name, None)

    def external_model_command_args_json(self, model_key: str) -> str | None:
        field_name = f"envirochem_{model_key.casefold()}_command_args_json"
        return getattr(self, field_name, None)

    def external_model_output_globs_json(self, model_key: str) -> str | None:
        field_name = f"envirochem_{model_key.casefold()}_output_globs_json"
        return getattr(self, field_name, None)


settings = Settings()
