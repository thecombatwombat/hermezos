"""Configuration management for HermezOS."""

from pathlib import Path
from typing import Any, Union

import tomli


class Config:
    """Configuration manager for HermezOS."""

    def __init__(self, config_path: Union[Path, None] = None):
        """Initialize configuration from TOML file."""
        if config_path is None:
            # Default to hermez.toml in current directory
            config_path = Path.cwd() / "hermez.toml"

        self.config_path = config_path
        self._config: dict[str, Any] = {}

        if config_path.exists():
            self._load_config()

    def _load_config(self) -> None:
        """Load configuration from TOML file."""
        try:
            with open(self.config_path, "rb") as f:
                self._config = tomli.load(f)
        except Exception:
            # Use defaults if loading fails
            self._config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    @property
    def registry_root(self) -> Path:
        """Get registry root path."""
        root_path = self.get("registry.root_path", "registry")
        registry_path = Path(root_path)
        
        # If relative path, resolve relative to config file directory
        if not registry_path.is_absolute():
            registry_path = self.config_path.parent / registry_path
            
        return registry_path

    @property
    def default_limit(self) -> int:
        """Get default pack limit."""
        limit = self.get("packer.default_limit", 50)
        return int(limit) if limit is not None else 50

    @property
    def sort_keys(self) -> list[str]:
        """Get sort keys for rule selection."""
        keys = self.get("packer.sort_keys", ["status", "severity", "version", "id"])
        return list(keys) if keys is not None else ["status", "severity", "version", "id"]

    @property
    def sort_orders(self) -> list[str]:
        """Get sort orders for rule selection."""
        orders = self.get("packer.sort_orders", ["asc", "asc", "desc", "asc"])
        return list(orders) if orders is not None else ["asc", "asc", "desc", "asc"]

    @property
    def allow_deprecated(self) -> bool:
        """Get whether deprecated rules are allowed."""
        value = self.get("validation.allow_deprecated", False)
        return bool(value) if value is not None else False

    @property
    def strict_validation(self) -> bool:
        """Get whether strict validation is enabled."""
        value = self.get("validation.strict", True)
        return bool(value) if value is not None else True
