"""Indexing layer for HermezOS with Graphiti and Kùzu support."""

import logging
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..config import Config
from ..models import PackRequest, RuleCard

logger = logging.getLogger(__name__)


@runtime_checkable
class IndexAdapter(Protocol):
    """Protocol for graph indexing adapters."""

    def candidate_ids(self, request: PackRequest) -> list[str]:
        """Get candidate rule IDs for the given pack request.

        Args:
            request: Pack request with filtering criteria

        Returns:
            List of rule IDs that match the request criteria.
            Empty list means no filtering (evaluate all rules).
        """
        ...

    def upsert_card(self, card: RuleCard) -> None:
        """Insert or update a rule card in the index.

        Args:
            card: Rule card to upsert
        """
        ...

    def delete_card(self, card_id: str) -> None:
        """Delete a rule card from the index.

        Args:
            card_id: ID of the rule card to delete
        """
        ...

    def close(self) -> None:
        """Close the index adapter and clean up resources."""
        ...


def make_index(config: Config) -> IndexAdapter:
    """Factory function to create an IndexAdapter based on configuration.

    Args:
        config: HermezOS configuration

    Returns:
        IndexAdapter instance based on config.graph_driver
    """
    if not config.graph_enabled or config.graph_driver == "null":
        from .null_index import NullIndex

        return NullIndex()

    driver = config.graph_driver.lower()

    try:
        if driver == "graphiti":
            from .graphiti import GraphitiIndex

            return GraphitiIndex(
                mode=config.graph_mode,
                url=config.graph_url,
                api_key=config.graph_api_key,
                export_path=Path(config.graph_export_path),
            )
        elif driver == "kuzu":
            from .kuzu_index import KuzuIndex

            return KuzuIndex(db_path=Path(config.graph_db_path))
        else:
            logger.warning(
                f"Unknown graph driver '{driver}', falling back to null index"
            )
            from .null_index import NullIndex

            return NullIndex()

    except Exception as e:
        logger.warning(
            f"Failed to initialize {driver} index: {e}, falling back to null index"
        )
        from .null_index import NullIndex

        return NullIndex()


__all__ = ["IndexAdapter", "make_index"]
