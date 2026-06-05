"""YAML configuration loader with env var injection and hot-reload."""
import os
import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

_ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


def _inject_env_vars_in_data(data):
    """Recursively inject env vars into string values in parsed YAML data.

    Only processes actual data values (not comments, which YAML parser already handles).
    """
    if isinstance(data, str):
        def replacer(match):
            env_var = match.group(1)
            env_value = os.environ.get(env_var)
            if env_value is None:
                return match.group(0)  # Keep the placeholder as-is if env var not set
            return env_value
        return _ENV_VAR_PATTERN.sub(replacer, data)
    elif isinstance(data, dict):
        return {k: _inject_env_vars_in_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_inject_env_vars_in_data(item) for item in data]
    return data


@dataclass
class ModelConfig:
    """Configuration for a single model."""
    name: str
    type: str  # image_generate, video_generate, image_understand, video_understand
    params: dict = field(default_factory=dict)


@dataclass
class ProviderConfig:
    """Configuration for a single provider."""
    name: str
    api_key: str
    base_url: str
    models: list = field(default_factory=list)  # list of ModelConfig


@dataclass
class AppConfig:
    """Root application configuration."""
    providers: list = field(default_factory=list)  # list of ProviderConfig
    defaults: dict = field(default_factory=dict)   # provider_name/model_name -> type


class Config:
    """Manages YAML config with hot-reload support."""

    def __init__(self, config_path: str = "models.yaml"):
        self._config_path = Path(config_path)
        self._config = None
        self._last_mtime = None
        self._load()

    def _load(self):
        """Load config from YAML file with env var injection."""
        raw = self._config_path.read_text(encoding="utf-8")
        # Parse YAML first so comments are excluded
        data = yaml.safe_load(raw)
        # Only inject env vars into actual data values
        if data is not None:
            data = _inject_env_vars_in_data(data)
        self._config = self._parse_config(data) if data else AppConfig()
        self._last_mtime = self._config_path.stat().st_mtime

    def _parse_config(self, data: dict) -> AppConfig:
        providers = []
        for p in data.get("providers", []):
            models = []
            for m in p.get("models", []):
                models.append(ModelConfig(
                    name=m["name"],
                    type=m["type"],
                    params=m.get("params", {}),
                ))
            providers.append(ProviderConfig(
                name=p["name"],
                api_key=p["api_key"],
                base_url=p["base_url"],
                models=models,
            ))
        return AppConfig(
            providers=providers,
            defaults=data.get("defaults", {}),
        )

    def reload_if_changed(self):
        """Reload config if file has changed on disk."""
        if not self._config_path.exists():
            return
        mtime = self._config_path.stat().st_mtime
        if mtime != self._last_mtime:
            self._load()

    @property
    def config(self) -> AppConfig:
        return self._config

    def get_provider(self, provider_name: str) -> Optional[ProviderConfig]:
        for p in self._config.providers:
            if p.name == provider_name:
                return p
        return None

    def get_models_by_type(self, model_type: str) -> list:
        """Get all models of a given type across all providers."""
        results = []
        for p in self._config.providers:
            for m in p.models:
                if m.type == model_type:
                    results.append((p, m))
        return results

    def resolve_default(self, model_type: str) -> Optional[tuple]:
        """Resolve default model for a type: returns (provider_name, model_name)."""
        key = f"{model_type}"
        default_ref = self._config.defaults.get(key)
        if default_ref and "/" in default_ref:
            parts = default_ref.split("/", 1)
            return parts[0], parts[1]
        return None

    def find_model(self, provider_name: Optional[str], model_name: str, model_type: str):
        """Find a specific model config.

        Args:
            provider_name: provider name or None for default
            model_name: model name to find
            model_type: type of operation

        Returns:
            tuple of (ProviderConfig, ModelConfig) or None
        """
        if provider_name:
            provider = self.get_provider(provider_name)
            if not provider:
                return None
            for m in provider.models:
                if m.name == model_name and m.type == model_type:
                    return provider, m
            return None

        # Find by default
        default_ref = self._config.defaults.get(model_type)
        if default_ref and "/" in default_ref:
            parts = default_ref.split("/", 1)
            provider_name = parts[0]
            model_name = parts[1]
            provider = self.get_provider(provider_name)
            if not provider:
                return None
            for m in provider.models:
                if m.name == model_name and m.type == model_type:
                    return provider, m
        return None
