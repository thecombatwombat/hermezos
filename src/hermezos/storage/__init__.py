"""Storage adapters for HermezOS."""

from abc import abstractmethod
from pathlib import Path
from typing import Optional, Protocol

from ..models import RuleCard
from .filesystem import FileSystemStorage


class StorageAdapter(Protocol):
    """Protocol for storage adapters."""

    @abstractmethod
    def load_all_cards(self) -> list[RuleCard]:
        """Load all rule cards from storage, parse YAML, and normalize."""
        ...

    @abstractmethod
    def save_card(self, card: RuleCard) -> None:
        """Save a rule card to storage with atomic write."""
        ...

    @abstractmethod
    def list_paths(self) -> list[Path]:
        """List all YAML file paths in storage."""
        ...


__all__ = ["StorageAdapter", "FileSystemStorage"]
