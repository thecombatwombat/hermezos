"""Configuration management for HermezOS."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import tomllib as _toml  # Python 3.11+

    TOMLDecodeError = _toml.TOMLDecodeError
except ModuleNotFoundError:
    import tomli as _toml  # type: ignore[no-redef]
    from tomli import TOMLDecodeError  # type: ignore


class Config:
    """Configuration manager for HermezOS."""

    def __init__(self, config_path: Path | None = None):
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
                self._config = _toml.load(f)
        except TOMLDecodeError as e:
            # Re-raise TOML parsing errors so CLI can handle them
            raise ValueError(
                f"Invalid TOML configuration in {self.config_path}: {e}"
            ) from e
        except Exception as e:
            # Re-raise other errors so CLI can handle them
            raise ValueError(
                f"Failed to load configuration from {self.config_path}: {e}"
            ) from e

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
        return (
            list(keys) if keys is not None else ["status", "severity", "version", "id"]
        )

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

    # Graph indexing configuration properties
    @property
    def graph_enabled(self) -> bool:
        """Get whether graph indexing is enabled."""
        value = self.get("graph.enabled", False)
        return bool(value) if value is not None else False

    @property
    def graph_driver(self) -> str:
        """Get graph driver type."""
        value = self.get("graph.driver", "null")
        return str(value) if value is not None else "null"

    @property
    def graph_mode(self) -> str:
        """Get graph mode (export_only or live)."""
        value = self.get("graph.mode", "export_only")
        return str(value) if value is not None else "export_only"

    @property
    def graph_url(self) -> str:
        """Get Graphiti server URL."""
        value = self.get("graph.url", "http://localhost:8800")
        return str(value) if value is not None else "http://localhost:8800"

    @property
    def graph_api_key(self) -> str:
        """Get Graphiti API key."""
        value = self.get("graph.api_key", "")
        return str(value) if value is not None else ""

    @property
    def graph_db_path(self) -> str:
        """Get Kuzu database path."""
        value = self.get("graph.db_path", ".hermezos/kuzu")
        return str(value) if value is not None else ".hermezos/kuzu"

    @property
    def graph_export_path(self) -> str:
        """Get Graphiti export directory path."""
        value = self.get("graph.export_path", "graph")
        return str(value) if value is not None else "graph"
